#include <stdio.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#define BUF_SIZE 4096  // 每次发送的数据块大小

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

    // 打开 raw.dat 文件
    FILE *file = fopen("raw.dat", "rb");
    if (!file) {
        printf("Failed to open raw.dat");
        close(fd);
        return -1;
    }

    // 读取文件内容并发送
    uint8_t tx_buf[BUF_SIZE];  // 发送缓冲区
    uint8_t rx_buf[BUF_SIZE];  // 接收缓冲区
    size_t bytes_read;

    while ((bytes_read = fread(tx_buf, 1, BUF_SIZE, file)) > 0) {
        // 设置SPI传输结构体
        struct spi_ioc_transfer tr = {
            .tx_buf = (unsigned long)tx_buf,  // 发送数据
            .rx_buf = (unsigned long)rx_buf,  // 接收数据
            .len = bytes_read,                // 发送数据长度
            .delay_usecs = 0,                 // 延时
            .speed_hz = speed,                // 速度
            .bits_per_word = bits,            // 数据位宽
        };

        // 执行SPI传输
        int ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
        if (ret < 0) {
            printf("Failed to send SPI message");
        } else {
            printf("Sent %zu bytes successfully\n", bytes_read);  // 打印发送成功信息
        }

        // 打印接收到的数据（调试用）
        printf("Received data (first 16 bytes): ");
        for (size_t i = 0; i < 16 && i < bytes_read; i++) {
            printf("%02X ", rx_buf[i]);
        }
        printf("\n");

        // 清空接收缓冲区
        memset(rx_buf, 0, BUF_SIZE);

        // 延时1秒
        sleep(1);
    }

    // 关闭文件和SPI设备
    fclose(file);
    close(fd);

    printf("File sent successfully.\n");
    return 0;
}