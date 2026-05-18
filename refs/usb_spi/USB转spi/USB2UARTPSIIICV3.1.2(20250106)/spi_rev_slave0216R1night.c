#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "USB2UARTSPIIICDLL.h"

#define BUFFER_SIZE 1024
#define FILE_NAME "received.dat"
#define HEADER_SIZE 4  // 文件大小头长度

int main() {
    unsigned char receiveBuf[BUFFER_SIZE];
    unsigned char *file_buffer = NULL;
    uint32_t expected_size = 0;
    uint32_t received_size = 0;
    int is_receiving = 0;
    int ret;

    // 初始化USB设备
    ret = OpenUsb(0);
    if (ret != 0) {
        printf("Failed to open USB device\n");
        return -1;
    } else {
        printf("Successfully opened USB device\n");
    }

    // 配置SPI从机模式：高位在前，模式0
    ret = ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0);
    if (ret != 0) {
        printf("Failed to configure SPI slave mode\n");
        CloseUsb(0);
        return -1;
    } else {
        printf("Successfully configured SPI slave mode: Mode 0, MSB\n");
    }


    while (1) {
        ret = SPISlaveRevData(receiveBuf, BUFFER_SIZE, 0);
        if (ret < 0) {
            printf("SPI接收错误: %d\n", ret);
            break;
        } else if (ret > 0) {
            if (!is_receiving) {
                // 解析文件大小头
                if (ret < HEADER_SIZE) {
                    printf("错误：首包数据不足头部长度\n");
                    continue;
                }
                expected_size = ntohl(*(uint32_t*)receiveBuf);
                received_size = 0;
                file_buffer = malloc(expected_size);
                if (!file_buffer) {
                    perror("内存分配失败");
                    break;
                }
                is_receiving = 1;

                // 复制首包中的数据部分
                size_t data_bytes = ret - HEADER_SIZE;
                if (data_bytes > 0) {
                    memcpy(file_buffer, receiveBuf + HEADER_SIZE, data_bytes);
                    received_size += data_bytes;
                }
            } else {
                // 累积后续数据块
                memcpy(file_buffer + received_size, receiveBuf, ret);
                received_size += ret;
            }

            // 检查是否接收完成
            if (received_size >= expected_size) {
                FILE *fp = fopen(FILE_NAME, "wb");
                if (fp) {
                    fwrite(file_buffer, 1, expected_size, fp);
                    fclose(fp);
                    printf("已接收完整文件: %u 字节\n", expected_size);
                } else {
                    perror("文件写入失败");
                }
                free(file_buffer);
                file_buffer = NULL;
                is_receiving = 0;
            }
        }
        usleep(1000);
    }

    if (file_buffer) free(file_buffer);
    CloseUsb(0);
    return 0;
}