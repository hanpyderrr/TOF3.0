/*
 * ExampleTOF.cpp — 真实 PF32 TCSPC 采集（哪吒端，P7）
 *
 * 数据流（与 sim_pf32.cpp 等价路径，共享 pd_bin_to_depth）：
 *   PF32 USB → getHistogram_short() → histogram[32×32×1024 uint16]
 *     ├─ pd_bin_to_depth → TofFrame(2070B) → /tmp/depth.dat（实时，给 qt_app）
 *     └─ 28B header + 2MB payload → ~/tof-data/raw_tcspc/<session>/seq_NNNNNN.tch（本地全量存档）
 *
 * 配置：TCSPC_sys_master 模式（PF32 出 TRIG 触发激光，反向 start-stop）；
 * 距离换算与模拟器一致：dist_mm = (1023 - peak_bin) × 55ps × c/2 ≈ (1023 - bin) × 8.25mm。
 *
 * 环境变量（可选，与 sim_pf32 一样保持零参数也能跑）：
 *   TOF_DATA_DIR        默认 ~/tof-data
 *   TOF_RAW_ENABLE      默认 1（设 0 关闭 .tch 落盘，仅出深度）
 *   TOF_INTEGRATION_S   默认 0.5（每帧积累秒数；典型 2fps）
 *   TOF_FIRMWARE        默认空（PF32_construct() 自动加载默认 PF32_USB3/USBC.bit）
 *   TOF_MAX_FRAMES      默认 0（0=无限循环，>0 抓 N 帧后退出，便于联调）
 *   TOF_MIN_FREE_MB     默认 500（剩余空间低于此值时停写 raw，仅出深度）
 *
 * 编译：cmake 已在 nezha/acquisition/CMakeLists.txt 挂 if(EXISTS) 钩子，
 *       哪吒上 `cd ~/TOF3.0/nezha/acquisition && cmake . && make ExampleTOF`
 *
 * 验证：./ExampleTOF & sleep 2 && python3 verify_depth.py /tmp/depth.dat ; kill %1
 *       ls -t ~/tof-data/raw_tcspc/  # 最新 session 目录里有 seq_NNNNNN.tch
 */
#include "PF32_API.h"
#include "PF_types.h"

#include "depth_proto.h"
#include "peak_detect.h"

#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <csignal>
#include <ctime>
#include <string>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/file.h>
#include <sys/time.h>
#include <fcntl.h>
#include <unistd.h>

/* ── 全局信号 ─────────────────────────────────────────────── */
static volatile bool g_run = true;
static void sigHandler(int) { g_run = false; }

/* ── 运行参数（环境变量驱动） ─────────────────────────────── */
struct Opts {
    std::string dataDir;
    std::string depthFile;
    std::string firmware;
    double      integrationSec;
    bool        writeRaw;
    int         maxFrames;
    long        minFreeMB;
};

static std::string envOr(const char *key, const std::string &def)
{
    const char *v = getenv(key);
    return (v && *v) ? std::string(v) : def;
}

static int envOrInt(const char *key, int def)
{
    const char *v = getenv(key);
    return (v && *v) ? atoi(v) : def;
}

static double envOrDouble(const char *key, double def)
{
    const char *v = getenv(key);
    return (v && *v) ? atof(v) : def;
}

static Opts loadOpts()
{
    Opts o;
    std::string home = envOr("HOME", "/root");
    o.dataDir        = envOr("TOF_DATA_DIR",       home + "/tof-data");
    o.depthFile      = envOr("TOF_DEPTH_FILE",     TOF_DEPTH_FILE);
    o.firmware       = envOr("TOF_FIRMWARE",       "");
    o.integrationSec = envOrDouble("TOF_INTEGRATION_S", 0.5);
    o.writeRaw       = envOrInt("TOF_RAW_ENABLE",  1) != 0;
    o.maxFrames      = envOrInt("TOF_MAX_FRAMES",  0);
    o.minFreeMB      = envOrInt("TOF_MIN_FREE_MB", 500);
    return o;
}

/* ── 文件系统工具 ─────────────────────────────────────────── */
static int ensureDir(const std::string &path)
{
    if (path.empty()) return 0;
    struct stat st;
    if (stat(path.c_str(), &st) == 0) return S_ISDIR(st.st_mode) ? 0 : -1;
    /* 递归创建父目录 */
    size_t slash = path.find_last_of('/');
    if (slash != std::string::npos && slash > 0)
        ensureDir(path.substr(0, slash));
    return mkdir(path.c_str(), 0755);
}

static long freeMB(const std::string &path)
{
    struct statvfs s;
    if (statvfs(path.c_str(), &s) != 0) return -1;
    return (long)((s.f_bavail * (uint64_t)s.f_frsize) >> 20);
}

static uint64_t nowMs()
{
    struct timeval tv;
    gettimeofday(&tv, nullptr);
    return (uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
}

static std::string sessionDir(const std::string &root)
{
    char ts[32];
    time_t t = time(nullptr);
    struct tm tm; localtime_r(&t, &tm);
    strftime(ts, sizeof(ts), "%Y%m%d_%H%M%S", &tm);
    return root + "/" + ts + "_pid" + std::to_string((long)getpid());
}

/* ── 写 /tmp/depth.dat（flock 原子，与 sim_pf32 一致）────── */
static int writeDepthFile(const char *path, const TofFrame *f)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("ExampleTOF: open depth"); return -1; }
    flock(fd, LOCK_EX);
    ssize_t n = write(fd, f, TOF_FRAME_SIZE);
    flock(fd, LOCK_UN);
    close(fd);
    return (n == TOF_FRAME_SIZE) ? 0 : -1;
}

/* ── 写 .tch 全量原始直方图 ──────────────────────────────────
 *
 * 格式（ARCHITECTURE.md §六）：
 *   magic         8B   "TCHIST1\0"
 *   seq           4B   LE
 *   width         2B   LE  (32)
 *   height        2B   LE  (32)
 *   bins          2B   LE  (1024)
 *   sampleBytes   2B   LE  (2)
 *   payloadBytes  8B   LE  (2097152)
 *   payload       uint16[32×32×1024]
 * 合计 28B 头 + 2 MB 数据。
 */
static int writeRawTch(const std::string &dir, uint32_t seq, const uint16_t *hist)
{
    char name[512];
    snprintf(name, sizeof(name), "%s/seq_%06u.tch", dir.c_str(), seq);

    int fd = open(name, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("ExampleTOF: open .tch"); return -1; }

    uint8_t hdr[28] = {0};
    memcpy(hdr + 0, "TCHIST1\0", 8);
    uint32_t s32  = seq;                 memcpy(hdr + 8,  &s32,  4);
    uint16_t w16  = TOF_SENSOR_W;        memcpy(hdr + 12, &w16,  2);
    uint16_t h16  = TOF_SENSOR_H;        memcpy(hdr + 14, &h16,  2);
    uint16_t b16  = PD_TDC_BINS;         memcpy(hdr + 16, &b16,  2);
    uint16_t sb16 = 2;                   memcpy(hdr + 18, &sb16, 2);
    uint64_t pb64 = (uint64_t)TOF_SENSOR_W * TOF_SENSOR_H * PD_TDC_BINS * 2;
    memcpy(hdr + 20, &pb64, 8);

    if (write(fd, hdr, sizeof(hdr)) != (ssize_t)sizeof(hdr)) {
        perror("ExampleTOF: write .tch hdr"); close(fd); return -1;
    }
    ssize_t n = write(fd, hist, (size_t)pb64);
    close(fd);
    if (n != (ssize_t)pb64) {
        fprintf(stderr, "ExampleTOF: short write .tch (%zd/%lu)\n",
                n, (unsigned long)pb64);
        return -1;
    }
    return 0;
}

/* ── 主程序 ────────────────────────────────────────────────── */
int main(int /*argc*/, char ** /*argv*/)
{
    signal(SIGINT,  sigHandler);
    signal(SIGTERM, sigHandler);

    Opts opts = loadOpts();

    /* 1. 准备 raw_tcspc session 目录 */
    std::string rawSession;
    if (opts.writeRaw) {
        std::string rawRoot = opts.dataDir + "/raw_tcspc";
        if (ensureDir(opts.dataDir) != 0 && errno != EEXIST) {
            perror("ExampleTOF: mkdir data-dir");
        }
        if (ensureDir(rawRoot) != 0 && errno != EEXIST) {
            perror("ExampleTOF: mkdir raw_tcspc");
        }
        rawSession = sessionDir(rawRoot);
        if (ensureDir(rawSession) != 0) {
            perror("ExampleTOF: mkdir session"); return 1;
        }
        fprintf(stderr, "ExampleTOF: raw session = %s (free=%ldMB)\n",
                rawSession.c_str(), freeMB(opts.dataDir));
    } else {
        fprintf(stderr, "ExampleTOF: raw write disabled (TOF_RAW_ENABLE=0)\n");
    }

    /* 2. 构造 PF32（带或不带 firmware 文件路径） */
    setLogStreamLevel(LOGLEVEL_WARNING);   /* WARN 及以上写 stderr，便于排查 */

    PF32_HANDLE pf32 = opts.firmware.empty()
        ? PF32_construct()
        : PF32_constructWithCustomFirmware(opts.firmware.c_str());
    if (!pf32) {
        fprintf(stderr, "ExampleTOF: PF32_construct returned null\n");
        return 2;
    }

    /* 1.5.21 SDK 的 link status 在 construct 后通常是 0/1，主流程不卡这里；
     * 设备真未就绪时下方 getHistogram_short 会返回 false 反馈。 */
    PF32_conn_status st = getLinkStatus(pf32);
    fprintf(stderr, "ExampleTOF: link status=%d (ready=2, 0/1 也属正常瞬态)\n", (int)st);

    /* 3. 配置 TCSPC sys_master 完整序列（1.5.21 SDK）：
     *   - setDataSource(sensor_data)：用真实 SPAD 数据而非内部 test pattern
     *   - setSPADEnable(true)：使 SPAD 阵列工作
     *   - setMode(TCSPC_sys_master)：PF32 自己出 TRIG 驱动激光
     *   - setEXTSTOPEnable(true)：启用 PF32 内部 EXTSTOP 作为 TCSPC stop（sys_master 必需）
     *   - setExposure_us：sample 用 100us，对应 ~10kHz 帧率；本项目用 200us 留余量
     *   - bins 数走默认（最大 1024，1.5.21 SDK 不暴露 setNoOfBinsInHistogram）
     */
    setDataSource(pf32, sensor_data);
    setSPADEnable(pf32, true);
    setMode(pf32, TCSPC_sys_master);
    setEXTSTOPEnable(pf32, true);
    setExposure_us(pf32, 200.0);

    unsigned int width  = getWidth(pf32);
    unsigned int height = getHeight(pf32);
    unsigned int bins   = getNoOfTDCCodes(pf32);
    char serial[MAX_SERIAL_NUMBER_LENGTH + 1] = {0};
    char model[MAX_MODEL_NUMBER_LENGTH + 1]   = {0};
    getSerialNumber(pf32, serial);
    getModelNumber(pf32, model);
    fprintf(stderr, "ExampleTOF: %s/%s sensor=%ux%u bins=%u sync=%dHz\n",
            model, serial, width, height, bins, getSync_Hz(pf32));

    if (width != TOF_SENSOR_W || height != TOF_SENSOR_H || bins != PD_TDC_BINS) {
        fprintf(stderr, "ExampleTOF: geometry mismatch (need 32x32x1024), abort\n");
        PF32_destruct(pf32); return 4;
    }

    /* 4. 分配直方图缓冲（32×32×1024×2 = 2 MB） */
    size_t npix = (size_t)width * height;
    size_t nsamp = npix * bins;
    uint16_t *hist = (uint16_t *)calloc(nsamp, sizeof(uint16_t));
    if (!hist) { perror("ExampleTOF: calloc hist"); PF32_destruct(pf32); return 5; }

    /* 5. 主循环：getHistogram_short → 同时写 .tch 和 /tmp/depth.dat */
    TofFrame frame;
    uint32_t seq = 0;
    int      diskCheckEvery = 100;
    bool     rawActive = opts.writeRaw;

    fprintf(stderr, "ExampleTOF: started integration=%.2fs raw=%s\n",
            opts.integrationSec, rawActive ? "on" : "off");

    bool firstFrame = true;
    while (g_run) {
        uint64_t t0 = nowMs();
        bool ok = getHistogram_short(pf32, hist, opts.integrationSec);
        if (!ok) {
            fprintf(stderr, "ExampleTOF: getHistogram_short failed at seq=%u\n", seq);
            usleep(100000);
            continue;
        }
        uint64_t tHist = nowMs();

        if (firstFrame) {
            fprintf(stderr, "ExampleTOF: first frame ok — sync=%dHz duty=%.3f exposure_us=%.1f\n",
                    getSync_Hz(pf32), getSyncDutyRatio(pf32), getExposure_us(pf32));
            firstFrame = false;
        }

        /* raw .tch 全量存档 */
        if (rawActive) writeRawTch(rawSession, seq, hist);

        /* 峰值检测 → TofFrame（与 sim_pf32 共用 pd_bin_to_depth） */
        memset(&frame, 0, sizeof(frame));
        frame.seq = seq;
        uint16_t valid = 0;
        for (size_t p = 0; p < npix; ++p) {
            uint16_t d = pd_bin_to_depth(hist + p * bins, bins);
            frame.depths[p] = d;
            if (d) ++valid;
        }
        frame.validCount = valid;
        tof_frame_seal(&frame);
        writeDepthFile(opts.depthFile.c_str(), &frame);

        uint64_t tDone = nowMs();
        int center = (int)((height / 2) * width + width / 2);
        fprintf(stderr,
                "ExampleTOF: seq=%u valid=%u/1024 center=%umm "
                "hist=%lums proc=%lums%s\n",
                seq, valid, frame.depths[center],
                (unsigned long)(tHist - t0),
                (unsigned long)(tDone - tHist),
                rawActive ? "" : " [raw-off]");

        /* 磁盘空间监护：低于阈值就停写 raw，深度流不停 */
        if (rawActive && (seq % diskCheckEvery == 0)) {
            long mb = freeMB(opts.dataDir);
            if (mb >= 0 && mb < opts.minFreeMB) {
                fprintf(stderr,
                        "ExampleTOF: free=%ldMB < %ldMB threshold, "
                        "stop writing raw (depth stream continues)\n",
                        mb, opts.minFreeMB);
                rawActive = false;
            }
        }

        ++seq;
        if (opts.maxFrames > 0 && (int)seq >= opts.maxFrames) {
            fprintf(stderr, "ExampleTOF: reached TOF_MAX_FRAMES=%d\n", opts.maxFrames);
            break;
        }
    }

    free(hist);
    PF32_destruct(pf32);
    fprintf(stderr, "ExampleTOF: stopped after %u frames\n", seq);
    return 0;
}
