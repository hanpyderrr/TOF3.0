#include <stdio.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <arpa/inet.h>  // 用于htonl/ntohl

#define FILE_NAME "raw.dat"
#define MAX_BLOCK_SIZE 1024

int is_file_modified(const char *filename, time_t *last_mod_time) {
    struct stat file_stat;
    if (stat(filename, &file_stat) {
        perror("Failed to get file status");
        return -1;
    }
    if (file_stat.st_mtime > *last_mod_time) {
        *last_mod_time = file_stat.st_mtime;
        return 1;
    }
    return 0;
}

int main() {
    int fd = open("/dev/spidev1.0", O_RDWR);
    if (fd < 0) {
        perror("Failed to open SPI device");
        return -1;
    }

    // 配置SPI参数
    uint8_t mode = SPI_MODE_0;
    uint8_t bits = 8;
    uint32_t speed = 1125000;

    if (ioctl(fd, SPI_IOC_WR_MODE, &mode) < 0) {
        perror("Failed to set SPI mode");
        close(fd);
        return -1;
    }
    if (ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0) {
        perror("Failed to set bits per word");
        close(fd);
        return -1;
    }
    if (ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed) < 0) {
        perror("Failed to set SPI speed");
        close(fd);
        return -1;
    }

    time_t last_mod_time = 0;
    uint8_t tx_buf[MAX_BLOCK_SIZE];
    FILE *fp;

    while (1) {
        if (is_file_modified(FILE_NAME, &last_mod_time) == 1) {
            fp = fopen(FILE_NAME, "rb");
            if (!fp) {
                perror("Failed to open file");
                continue;
            }

            // 获取文件大小并发送头部
            fseek(fp, 0, SEEK_END);
            long file_size = ftell(fp);
            fseek(fp, 0, SEEK_SET);
            uint32_t file_size_network = htonl(file_size);

            struct spi_ioc_transfer tr_header = {
                    .tx_buf = (unsigned long)&file_size_network,
                    .rx_buf = 0,
                    .len = sizeof(file_size_network),
                    .delay_usecs = 0,
                    .speed_hz = speed,
                    .bits_per_word = bits,
            };
            ioctl(fd, SPI_IOC_MESSAGE(1), &tr_header);

            // 分块发送文件内容
            long total_sent = 0;
            while (total_sent < file_size) {
                size_t block_size = (file_size - total_sent > MAX_BLOCK_SIZE) ?
                                    MAX_BLOCK_SIZE : file_size - total_sent;
                size_t bytes_read = fread(tx_buf, 1, block_size, fp);

                struct spi_ioc_transfer tr_data = {
                        .tx_buf = (unsigned long)tx_buf,
                        .rx_buf = 0,
                        .len = bytes_read,
                        .delay_usecs = 0,
                        .speed_hz = speed,
                        .bits_per_word = bits,
                };
                ioctl(fd, SPI_IOC_MESSAGE(1), &tr_data);
                total_sent += bytes_read;
            }

            fclose(fp);
            printf("[Sent] File size: %ld bytes\n", file_size);
        }
        usleep(100000);  // 100ms检查一次
    }

    close(fd);
    return 0;
}