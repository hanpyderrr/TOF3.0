#include <stdio.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>

#define FILE_NAME "raw.dat"
#define MAX_BLOCK_SIZE 1024  // 单次传输最大字节数

// 检查文件是否被修改
int is_file_modified(const char *filename, time_t *last_mod_time) {
    struct stat file_stat;
    if (stat(filename, &file_stat)) {
        perror("Failed to get file status");
        return -1;
    }
    if (file_stat.st_mtime > *last_mod_time) {
        *last_mod_time = file_stat.st_mtime;
        return 1;  // 文件已修改
    }
    return 0;  // 文件未修改
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
        // 检查文件是否更新
        if (is_file_modified(FILE_NAME, &last_mod_time) == 1) {
            fp = fopen(FILE_NAME, "rb");
            if (!fp) {
                perror("Failed to open file");
                continue;
            }

            // 读取文件内容
            size_t bytes_read = fread(tx_buf, 1, MAX_BLOCK_SIZE, fp);
            fclose(fp);

            if (bytes_read > 0) {
                // 发送数据块
                struct spi_ioc_transfer tr = {
                    .tx_buf = (unsigned long)tx_buf,
                    .rx_buf = 0,
                    .len = bytes_read,
                    .delay_usecs = 0,
                    .speed_hz = speed,
                    .bits_per_word = bits,
                };
                int ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
                if (ret < 0) {
                    perror("SPI发送失败");
                } else {
                    printf("[更新] 已发送 %zu 字节\n", bytes_read);
                }
            }
        }

        //usleep(100000);  // 100ms 检查一次更新
		sleep(1);
    }

    close(fd);
    return 0;
}