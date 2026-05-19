/*
 * spi_syncer.c — 哪吒侧实时深度帧 SPI 推送（裸 TofFrame，本阶段 P-RT）
 *
 * 数据流：sim_pf32/ExampleTOF 写 TOF_DEPTH_FILE(2070B TofFrame, flock LOCK_EX)
 *         本程序按 seq 去重读出一帧 → /dev/spidev1.0 SPI master 整帧发送
 *         → USB转SPI 适配器 → RK3568 spi_receiver。
 *
 * 与旧 单光子项目/TOF/哪吒端/spisendTOF.c 的唯一区别：去重逻辑由 mtime（秒级粒度，
 * 2fps 会漏发/重发）改为 TofFrame.seq 比对，与哪吒 Qt onTimer 去重一致。
 *
 * SPI 参数与已验证物理链路一致：MODE0 / 8bit / 1.125MHz，整帧单次 SPI_IOC_MESSAGE。
 * 需 root（/dev/spidev1.0 仅 root 可写）。传输失败仅记日志，不退出（不阻塞采集）。
 *
 * 构建（哪吒，x86_64）：  gcc -O2 -Wall -o spi_syncer spi_syncer.c
 * 运行：  sudo ./spi_syncer [depth_file] [spidev]
 *         默认 depth_file=TOF_DEPTH_FILE(/tmp/depth.dat)  spidev=/dev/spidev1.0
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>

#include "../acquisition/depth_proto.h"

#define DEFAULT_SPIDEV "/dev/spidev1.0"
#define POLL_USEC      20000   /* 20ms 轮询；sim 500ms/帧，余量大，延迟低 */

static volatile sig_atomic_t g_run = 1;
static void on_sig(int s) { (void)s; g_run = 0; }

static int spi_open(const char *dev)
{
    int fd = open(dev, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "spi_syncer: open %s failed: %s%s\n", dev, strerror(errno),
                errno == EACCES ? " (需 root: sudo ./spi_syncer)" : "");
        return -1;
    }
    uint8_t  mode = SPI_MODE_0, bits = 8;
    uint32_t speed = 1125000;
    if (ioctl(fd, SPI_IOC_WR_MODE, &mode) < 0 ||
        ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0 ||
        ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed) < 0) {
        perror("spi_syncer: SPI config");
        close(fd);
        return -1;
    }
    return fd;
}

/* 读一帧并校验；返回 0=成功(frame 已填), <0=本轮无有效新帧 */
static int read_frame(const char *path, TofFrame *frame)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0)
        return -1;
    if (flock(fd, LOCK_SH) != 0) {       /* 与 sim_pf32 写端 LOCK_EX 互斥 */
        close(fd);
        return -1;
    }
    ssize_t n = read(fd, frame, TOF_FRAME_SIZE);
    flock(fd, LOCK_UN);
    close(fd);
    if (n != TOF_FRAME_SIZE)
        return -1;
    return tof_frame_verify(frame) == 0 ? 0 : -1;
}

int main(int argc, char **argv)
{
    const char *depth_file = (argc > 1) ? argv[1] : TOF_DEPTH_FILE;
    const char *spidev     = (argc > 2) ? argv[2] : DEFAULT_SPIDEV;

    signal(SIGINT,  on_sig);
    signal(SIGTERM, on_sig);

    int spi_fd = spi_open(spidev);
    if (spi_fd < 0)
        return 1;

    printf("spi_syncer: started  depth=%s  spi=%s  frame=%dB\n",
           depth_file, spidev, TOF_FRAME_SIZE);

    TofFrame frame;
    uint32_t last_seq = 0;
    int      have_last = 0;
    uint32_t speed = 1125000;
    uint8_t  bits = 8;
    unsigned long sent = 0, dropped = 0;

    while (g_run) {
        if (read_frame(depth_file, &frame) != 0) {
            usleep(POLL_USEC);
            continue;
        }
        if (have_last && frame.seq == last_seq) {   /* 无新帧 */
            usleep(POLL_USEC);
            continue;
        }

        struct spi_ioc_transfer tr;
        memset(&tr, 0, sizeof(tr));
        tr.tx_buf        = (unsigned long)&frame;
        tr.rx_buf        = 0;
        tr.len           = TOF_FRAME_SIZE;
        tr.speed_hz      = speed;
        tr.bits_per_word = bits;

        if (ioctl(spi_fd, SPI_IOC_MESSAGE(1), &tr) < 0) {
            /* 传输失败不退出：哪吒侧数据继续本地积累，下帧重试 */
            fprintf(stderr, "spi_syncer: SPI send seq=%u failed: %s\n",
                    frame.seq, strerror(errno));
            ++dropped;
            usleep(POLL_USEC);
            continue;
        }

        last_seq  = frame.seq;
        have_last = 1;
        if ((++sent % 50) == 0)
            printf("spi_syncer: sent=%lu dropped=%lu last_seq=%u\n",
                   sent, dropped, last_seq);
        usleep(POLL_USEC);
    }

    close(spi_fd);
    printf("spi_syncer: stopped  sent=%lu dropped=%lu\n", sent, dropped);
    return 0;
}
