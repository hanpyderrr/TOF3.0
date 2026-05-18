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

    // 打开 raw.dat 文件（二进制模式）
    FILE *fp = fopen(FILE_NAME, "rb");
    if (!fp) {
        perror("Failed to open file");
        close(fd);
        return -1;
    }


    // 分批次发送
    uint8_t tx_buf[MAX_BLOCK_SIZE];
    long total_sent = 0;
    int block_num = 1;

    time_t last_mod_time = 0;
    //FILE *fp = NULL;

    while (1) {
        // 检查文件是否更新
        if (is_file_modified(FILE_NAME, &last_mod_time) == 1) {
            // 获取文件大小
            fseek(fp, 0, SEEK_END);
            long file_size = ftell(fp);
            fseek(fp, 0, SEEK_SET);
            printf("文件总大小: %ld 字节\n", file_size);

            while (total_sent < file_size) {
                // 计算本次发送的字节数
                long remaining = file_size - total_sent;
                size_t block_size = (remaining > MAX_BLOCK_SIZE) ? MAX_BLOCK_SIZE : remaining;

                // 读取数据块
                size_t bytes_read = fread(tx_buf, 1, block_size, fp);
                if (bytes_read <= 0) {
                    perror("文件读取失败");
                    break;
                }

                // 发送数据块
                struct spi_ioc_transfer tr = {
                        .tx_buf = (unsigned long) tx_buf,
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
                    printf("[批次 %d] 已发送 %zu 字节\n", block_num, bytes_read);
                    total_sent += bytes_read;
                    block_num++;
                }

                sleep(1);  // 50ms 延时，确保从机处理完成
                
            }
            total_sent =0;
			sleep(1);
        }else if (is_file_modified(FILE_NAME, &last_mod_time) == 0) {
				printf("file not change\n");
			}

        
    }
	fclose(fp);
    close(fd);
    
    return 0;
}