#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <string.h>

#define SPI_DEVICE "/dev/spidev1.0"  // SPI设备节点，根据实际情况修改
#define DATA_FILE "data.dat"         // 数据保存的文件路径

// SPI模式
int SPI_MODE = SPI_MODE_0;

// SPI速度
int SPI_SPEED = 500000;  // 500 kHz

// SPI字长
int SPI_BITS_PER_WORD = 8;

// SPI延迟
int SPI_DELAY = 0;

int spi_fd;

// 初始化SPI
int spi_init() {
    int ret;

    // 打开SPI设备
    spi_fd = open(SPI_DEVICE, O_RDWR);
    if (spi_fd < 0) {
        perror("无法打开SPI设备");
        return -1;
    }

    // 设置SPI模式
    ret = ioctl(spi_fd, SPI_IOC_WR_MODE, &SPI_MODE);
    if (ret == -1) {
        perror("无法设置SPI模式");
        return -1;
    }

    // 设置SPI字长
    ret = ioctl(spi_fd, SPI_IOC_WR_BITS_PER_WORD, &SPI_BITS_PER_WORD);
    if (ret == -1) {
        perror("无法设置SPI字长");
        return -1;
    }

    // 设置SPI速度
    ret = ioctl(spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, &SPI_SPEED);
    if (ret == -1) {
        perror("无法设置SPI速度");
        return -1;
    }

    return 0;
}

// SPI发送和接收数据
int spi_transfer(unsigned char *tx_buf, unsigned char *rx_buf, int len) {
    struct spi_ioc_transfer tr = {
        .tx_buf = (unsigned long)tx_buf,
        .rx_buf = (unsigned long)rx_buf,
        .len = len,
        .delay_usecs = SPI_DELAY,
        .speed_hz = SPI_SPEED,
        .bits_per_word = SPI_BITS_PER_WORD,
    };

    int ret = ioctl(spi_fd, SPI_IOC_MESSAGE(1), &tr);
    if (ret < 1) {
        perror("SPI传输失败");
        return -1;
    }

    return 0;
}

// 关闭SPI
void spi_close() {
    close(spi_fd);
}

// 将数据转换为十六进制字符串
void data_to_hex_string(unsigned char *data, int len, char *hex_str) {
    for (int i = 0; i < len; i++) {
        sprintf(hex_str + i * 3, "%02X ", data[i]);  // 每个字节转换为2位十六进制，加一个空格
    }
    hex_str[len * 3 - 1] = '\0';  // 去掉最后一个空格，添加字符串结束符
}

// 保存数据到文件（十六进制格式）
void save_data_to_file(const char *filename, unsigned char *data, int len) {
    FILE *file = fopen(filename, "w");  // 以写入模式打开文件（清空文件）
    if (file == NULL) {
        perror("无法打开文件");
        return;
    }

    // 将数据转换为十六进制字符串
    char hex_str[128];  // 假设数据长度不超过128字节
    data_to_hex_string(data, len, hex_str);

    // 写入文件
    fprintf(file, "%s\n", hex_str);
    fclose(file);
}

int main() {
    unsigned char tx_buf[32] = {0x01, 0x02, 0x03, 0x04};  // 要发送的数据
    unsigned char rx_buf[32] = {0};  // 接收数据的缓冲区

    // 初始化SPI
    if (spi_init() < 0) {
        return -1;
    }

    printf("开发板作为SPI主机，开始通信...\n");

    // 持续发送和接收数据
    while (1) {
        // 清空接收缓冲区
        memset(rx_buf, 0, sizeof(rx_buf));

        // 发起SPI传输
        if (spi_transfer(tx_buf, rx_buf, sizeof(rx_buf)) < 0) {
            fprintf(stderr, "SPI传输失败，继续尝试...\n");
            continue;
        }

        // 打印接收到的数据
        printf("接收到的数据: ");
        for (int i = 0; i < sizeof(rx_buf); i++) {
            printf("%02X ", rx_buf[i]);
        }
        printf("\n");

        // 保存数据到文件（十六进制格式）
        save_data_to_file(DATA_FILE, rx_buf, sizeof(rx_buf));

        // 等待10秒
        sleep(10);
    }

    // 关闭SPI（实际上不会执行到这里）
    spi_close();

    return 0;
}