#include <stdio.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

int main() {
    int fd = open("/dev/spidev1.0", O_RDWR);
    if (fd < 0) {
        printf("Failed to open SPI device");
        return -1;
    }

    // 配置SPI模式、数据位宽和速度
    uint8_t mode = SPI_MODE_0;
    uint8_t bits = 8;
    uint32_t speed = 1125000;

    ioctl(fd, SPI_IOC_WR_MODE, &mode);
    ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &bits);
    ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);

    // 发送数据缓冲区
    uint8_t tx[] = "Frame=123";
    // 接收数据缓冲区
    uint8_t rxbuf[4096];
    memset(rxbuf, 0, sizeof(rxbuf));

    while (1) {
        // 设置SPI传输结构体
        struct spi_ioc_transfer tr = {
            .tx_buf = (unsigned long)tx,       // 发送数据
            .rx_buf = (unsigned long)rxbuf,     // 接收数据
            .len = sizeof(tx) - 1,             // 发送数据长度（不包括字符串结束符）
            .delay_usecs = 0,                   // 延时
            .speed_hz = speed,                  // 速度
            .bits_per_word = bits,              // 数据位宽
        };

        // 执行SPI传输
        int ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
        if (ret < 0) {
            perror("Failed to send SPI message");
        } else {
            printf("Send successfully: %s\n", tx);  // 打印发送成功信息
        }

        // 打印接收到的数据
        printf("Received: %s\n", rxbuf);

        // 清空接收缓冲区
        memset(rxbuf, 0, sizeof(rxbuf));

        // 延时1秒
        sleep(1);
    }

    close(fd);
    return 0;
}