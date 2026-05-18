/*
 * sim_pf32.cpp — PF32 TCSPC 数据模拟器（哪吒端）
 *
 * 数据流（与真实 PF32 路径完全相同）：
 *   模拟场景 → 合成直方图[1024像素×1024bins] → pd_bin_to_depth() → TofFrame 二进制
 *
 * 模拟场景：背景墙（~7000mm）+ 前景球体（~2800mm，左右正弦移动）+ 5% 无效像素
 *
 * 直方图模型（单像素）：
 *   - 暗计数本底：均匀随机 0~4 counts/bin（模拟 SPAD 暗计数 + 环境光）
 *   - 信号峰：以目标 bin 为中心的高斯，sigma ≈ 2 bins（IRF ~150ps FWHM）
 *   - 峰高：~120 counts（典型 0.5s 积累，中等反射率目标）
 *   - 5% 像素：只有暗计数，无信号（occlusion / 死像素）
 *
 * 验证：
 *   ./sim_pf32 &
 *   sleep 1 && python3 verify_depth.py /tmp/depth.dat
 *   kill %1
 */
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <csignal>
#include <unistd.h>
#include <fcntl.h>
#include <sys/file.h>
#include "depth_proto.h"
#include "peak_detect.h"

/* ── 全局信号标志 ────────────────────────────────────────── */
static volatile bool g_run = true;
static void sigHandler(int) { g_run = false; }

/* ── 直方图生成参数 ──────────────────────────────────────── */
static const float  kSigmaBins   = 2.0f;   /* IRF 高斯宽度（bins）*/
static const int    kPeakHeight  = 120;    /* 信号峰高（counts）*/
static const int    kDarkMax     = 4;      /* 暗计数上限（counts/bin）*/
static const float  kInvalidRate = 0.05f;  /* 无效像素概率 */

/* ── 场景参数 ────────────────────────────────────────────── */
static const float kBgDistMm    = 7000.f;  /* 背景墙基础距离 */
static const float kBgWaveMm    = 120.f;   /* 背景起伏幅度 */
static const float kSphDistMm   = 2800.f;  /* 球心距离 */
static const float kSphRadius   = 0.45f;   /* 球体半径（归一化坐标）*/
static const float kSphSwing    = 0.35f;   /* 左右摆动幅度（归一化）*/
static const float kNoiseMm     = 50.f;    /* 真实距离扰动（mm 峰峰）*/

/* ── 单像素真实距离计算（场景模型）────────────────────────
 *
 * 输入：nx, ny  归一化坐标 [-1, 1]
 *       t       仿真时间（秒）
 * 返回：真实距离（mm），0 表示强制无效
 */
static float sceneDepth(float nx, float ny, double t)
{
    /* 背景墙 */
    float d = kBgDistMm
            + sinf(nx * 3.0f + (float)(t * 0.3)) * kBgWaveMm
            + cosf(ny * 2.5f - (float)(t * 0.2)) * kBgWaveMm * 0.75f;

    /* 前景球体 */
    float bx = (float)(sin(t * 0.4) * kSphSwing);
    float r2 = (nx - bx) * (nx - bx) + ny * ny;
    if (r2 < kSphRadius * kSphRadius) {
        float dz = sqrtf(kSphRadius * kSphRadius - r2);
        d = kSphDistMm - dz * 1200.f;
    }

    /* 距离扰动（模拟测量噪声，在直方图噪声之外的宏观误差） */
    d += ((float)rand() / RAND_MAX - 0.5f) * kNoiseMm;

    if (d < 100.f)    return 100.f;
    if (d > TOF_MAX_MM) return (float)TOF_MAX_MM;
    return d;
}

/* ── 单像素合成直方图 ────────────────────────────────────
 *
 * 输入：true_dist_mm  目标真实距离（mm），0 = 强制无效
 *       hist[bins]    输出直方图缓冲区（调用前无需清零）
 */
static void simPixelHistogram(float true_dist_mm, uint16_t hist[PD_TDC_BINS])
{
    /* 暗计数本底 */
    for (int b = 0; b < PD_TDC_BINS; ++b)
        hist[b] = (uint16_t)(rand() % (kDarkMax + 1));

    if (true_dist_mm <= 0.f) return;   /* 无效像素：只有暗计数 */

    /* 目标 bin（反向 start-stop）*/
    float peak_f = 1023.0f - true_dist_mm / PD_BIN_MM;
    int   peak_b = (int)(peak_f + 0.5f);
    if (peak_b < 0)            peak_b = 0;
    if (peak_b >= PD_TDC_BINS) peak_b = PD_TDC_BINS - 1;

    /* 高斯信号峰（±4sigma 范围内）*/
    int bMin = peak_b - (int)(kSigmaBins * 4.f);
    int bMax = peak_b + (int)(kSigmaBins * 4.f);
    if (bMin < 0)            bMin = 0;
    if (bMax >= PD_TDC_BINS) bMax = PD_TDC_BINS - 1;

    for (int b = bMin; b <= bMax; ++b) {
        float delta  = (float)(b - peak_b) / kSigmaBins;
        int   signal = (int)(kPeakHeight * expf(-0.5f * delta * delta));
        hist[b] = (uint16_t)(hist[b] + signal);
    }
}

/* ── 帧写入（flock 原子写）──────────────────────────────── */
static int writeFrame(const char *path, const TofFrame *frame)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("sim_pf32: open"); return -1; }
    flock(fd, LOCK_EX);
    ssize_t n = write(fd, frame, TOF_FRAME_SIZE);
    flock(fd, LOCK_UN);
    close(fd);
    return (n == TOF_FRAME_SIZE) ? 0 : -1;
}

/* ── 主循环 ──────────────────────────────────────────────── */
int main(void)
{
    signal(SIGINT,  sigHandler);
    signal(SIGTERM, sigHandler);

    /* 分配直方图缓冲区：1024 像素 × 1024 bins */
    uint16_t *histogram = (uint16_t *)malloc(PD_TDC_BINS * TOF_PIXELS * sizeof(uint16_t));
    if (!histogram) { perror("malloc"); return 1; }

    TofFrame frame;
    uint32_t seq = 0;
    double   t   = 0.0;

    printf("sim_pf32: started  output=%s\n", TOF_DEPTH_FILE);
    printf("sim_pf32: histogram model: dark=%d, peak=%d counts, sigma=%.1f bins\n",
           kDarkMax, kPeakHeight, kSigmaBins);

    while (g_run) {
        /* Step 1：每像素生成合成直方图 */
        for (int row = 0; row < TOF_SENSOR_H; ++row) {
            for (int col = 0; col < TOF_SENSOR_W; ++col) {
                int   idx = row * TOF_SENSOR_W + col;
                float nx  = (float)col / (TOF_SENSOR_W - 1) * 2.f - 1.f;
                float ny  = (float)row / (TOF_SENSOR_H - 1) * 2.f - 1.f;

                /* 5% 概率无效像素 */
                bool invalid = ((float)rand() / RAND_MAX) < kInvalidRate;
                float dist   = invalid ? 0.f : sceneDepth(nx, ny, t);

                simPixelHistogram(dist, histogram + idx * PD_TDC_BINS);
            }
        }

        /* Step 2：峰值检测（与 ExampleTOF 真实路径相同函数）*/
        memset(&frame, 0, sizeof(frame));
        frame.seq = seq;
        uint16_t valid = 0;
        for (int p = 0; p < TOF_PIXELS; ++p) {
            frame.depths[p] = pd_bin_to_depth(histogram + p * PD_TDC_BINS, PD_TDC_BINS);
            if (frame.depths[p]) ++valid;
        }
        frame.validCount = valid;

        /* Step 3：封帧（填 magic + CRC）并写文件 */
        tof_frame_seal(&frame);
        if (writeFrame(TOF_DEPTH_FILE, &frame) == 0) {
            /* 打印球心处像素的距离，方便肉眼验证 */
            int   centerIdx   = (TOF_SENSOR_H / 2) * TOF_SENSOR_W + TOF_SENSOR_W / 2;
            float bx          = (float)(sin(t * 0.4) * kSphSwing);
            printf("sim_pf32: frame=%u  valid=%u/1024  center=%umm  ball_x=%.2f\n",
                   seq, valid, frame.depths[centerIdx], bx);
        }

        ++seq;
        t += 0.5;
        usleep(500000);
    }

    free(histogram);
    printf("sim_pf32: stopped after %u frames\n", seq);
    return 0;
}
