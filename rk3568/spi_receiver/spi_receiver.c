/*
 * spi_receiver.c — RK3568 侧 SPI slave 收实时深度帧（裸 TofFrame，本阶段 P-RT）
 *
 * 传输层照搬已验证物理链路 spi_rev_slavemyloop0411.c：
 *   OpenUsb → ConfigSPIParamSlave(MSB,Mode0) → 循环 SPISlaveRcvData
 * 应用层换成二进制：SPI 是无边界字节流，按 TofFrame magic("TOFP")在流中同步，
 * 凑满 2070B 并通过 magic/version/尺寸/crc16-Modbus 校验后，flock 覆写 received.dat
 * （二进制 2070B），交 Qt 显示程序消费。无外层信封、无 ACK、不补传（丢帧只丢一画面）。
 *
 * 接收异常仅记日志并重连，不退出（哪吒侧数据继续本地积累）。
 *
 * 构建（RK3568 aarch64，用 SDK，板上无 gcc）：
 *   SDK=~/rk3568_linux_sdk/buildroot/output/rockchip_rk3568
 *   $SDK/host/bin/aarch64-buildroot-linux-gnu-gcc -O2 -Wall -o spi_receiver \
 *       spi_receiver.c -Ideps -Ldeps/aarch64 -lUSB2UARTSPIIIC
 * 运行：  ./spi_receiver [received_dat_path]   (默认 /tmp/received.dat，板上 tmpfs)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <sys/file.h>

#include "USB2UARTSPIIICDLL.h"

#define FRAME_SIZE   2070
#define HDR_VERSION  1
#define HDR_SIZE     16
#define DIM_WH       32
/* magic 0x50464F54 小端落字节序 = 'T''O''F''P' */
static const uint8_t MAGIC[4] = { 0x54, 0x4F, 0x46, 0x50 };

#define RCV_CHUNK    8192
#define ACC_CAP      (FRAME_SIZE * 4)   /* 累积缓冲：容多帧 + 错位重同步 */
#define USB_INDEX    0

static volatile sig_atomic_t g_run = 1;
static void on_sig(int s) { (void)s; g_run = 0; }

/* crc16-Modbus，与 depth_proto.h / tof_frame_parser_core.h 同多项式 */
static uint16_t crc16_modbus(const uint8_t *d, int len)
{
    uint16_t crc = 0xFFFF;
    for (int i = 0; i < len; ++i) {
        crc ^= d[i];
        for (int b = 0; b < 8; ++b)
            crc = (crc & 1u) ? (uint16_t)((crc >> 1) ^ 0xA001u)
                             : (uint16_t)(crc >> 1);
    }
    return crc;
}

/* 校验从 p 起的 2070B 是否为合法 TofFrame（magic/版本/头长/尺寸/crc16）。
 * 不查 validCount/深度范围——Qt 侧 depthParser 会做完整校验，这里只做完整性门控。*/
static int frame_ok(const uint8_t *p)
{
    if (memcmp(p, MAGIC, 4) != 0) return 0;
    if (p[4] != HDR_VERSION || p[5] != HDR_SIZE) return 0;
    if ((p[12] | (p[13] << 8)) != DIM_WH) return 0;   /* width  LE */
    if ((p[14] | (p[15] << 8)) != DIM_WH) return 0;   /* height LE */
    uint16_t want = (uint16_t)(p[FRAME_SIZE - 2] | (p[FRAME_SIZE - 1] << 8));
    uint16_t got  = crc16_modbus(p + 4, FRAME_SIZE - 6);
    return got == want;
}

/* 覆写 received.dat：flock 独占（与 Qt depthParser LOCK_SH 互斥），定长 2070B */
static void write_frame(const char *path, const uint8_t *frame)
{
    int fd = open(path, O_WRONLY | O_CREAT, 0644);
    if (fd < 0) { perror("spi_receiver: open received.dat"); return; }
    if (flock(fd, LOCK_EX) != 0) { perror("spi_receiver: flock"); close(fd); return; }
    if (ftruncate(fd, 0) != 0 || lseek(fd, 0, SEEK_SET) != 0 ||
        write(fd, frame, FRAME_SIZE) != FRAME_SIZE)
        perror("spi_receiver: write received.dat");
    fsync(fd);
    flock(fd, LOCK_UN);
    close(fd);
}

static int spi_open(void)
{
    int ret = OpenUsb(USB_INDEX);
    if (ret != 0) { fprintf(stderr, "spi_receiver: OpenUsb=%d\n", ret); return -1; }
    ret = ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, USB_INDEX);
    if (ret != 0) {
        fprintf(stderr, "spi_receiver: ConfigSPIParamSlave=%d\n", ret);
        CloseUsb(USB_INDEX);
        return -1;
    }
    printf("spi_receiver: SPI slave ready (MSB, Mode0)\n");
    return 0;
}

int main(int argc, char **argv)
{
    const char *out_path = (argc > 1) ? argv[1] : "/tmp/received.dat";

    signal(SIGINT,  on_sig);
    signal(SIGTERM, on_sig);
    signal(SIGHUP,  SIG_IGN);   /* 服务进程：脱离控制台 HUP（生产由 init 启动无 tty）*/

    while (g_run && spi_open() != 0) {
        fprintf(stderr, "spi_receiver: open failed, retry in 2s\n");
        sleep(2);
    }
    printf("spi_receiver: out=%s frame=%dB, receiving...\n", out_path, FRAME_SIZE);

    uint8_t  rcv[RCV_CHUNK];
    uint8_t  acc[ACC_CAP];
    int      acc_len = 0;
    unsigned long frames = 0, bad = 0;

    while (g_run) {
        int ret = SPISlaveRcvData(rcv, sizeof(rcv), USB_INDEX);
        if (ret < 0) {
            fprintf(stderr, "spi_receiver: SPISlaveRcvData=%d, reconnect\n", ret);
            CloseUsb(USB_INDEX);
            acc_len = 0;
            while (g_run && spi_open() != 0) sleep(2);
            continue;
        }
        if (ret == 0) { usleep(2000); continue; }

        /* 追加到累积缓冲；溢出则只保留尾部（可能含半个 magic）*/
        if (acc_len + ret > ACC_CAP) {
            int keep = FRAME_SIZE - 1;
            if (acc_len > keep) {
                memmove(acc, acc + acc_len - keep, keep);
                acc_len = keep;
            }
            if (acc_len + ret > ACC_CAP) acc_len = 0;   /* 极端：丢弃重来 */
        }
        memcpy(acc + acc_len, rcv, ret);
        acc_len += ret;

        /* 在流中按 magic 同步，逐帧取出 */
        int i = 0;
        while (acc_len - i >= FRAME_SIZE) {
            if (memcmp(acc + i, MAGIC, 4) != 0) { ++i; continue; }   /* 找 magic */
            if (frame_ok(acc + i)) {
                write_frame(out_path, acc + i);
                if ((++frames % 50) == 0)
                    printf("spi_receiver: frames=%lu bad=%lu\n", frames, bad);
                i += FRAME_SIZE;                 /* 整帧消费 */
            } else {
                ++bad;
                ++i;                             /* 假 magic / 损坏，跳 1 字节重扫 */
            }
        }
        /* 保留未消费尾部（含可能跨包的帧头）*/
        if (i > 0) {
            memmove(acc, acc + i, acc_len - i);
            acc_len -= i;
        }
    }

    CloseUsb(USB_INDEX);
    printf("spi_receiver: stopped  frames=%lu bad=%lu\n", frames, bad);
    return 0;
}
