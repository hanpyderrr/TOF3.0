#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "USB2UARTSPIIICDLL.h"

#define BUFFER_SIZE 1024
#define FILE_NAME "received.dat"
FILE *fp = NULL;
int main() {
    unsigned char receiveBuf[BUFFER_SIZE];
    int ret;
    
    int is_new_file = 1;  // 标记是否为新文件开始

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

    printf("Start receiving data...\n");

    while (1) {
        ret = SPISlaveRcvData(receiveBuf, BUFFER_SIZE, 0);
        if (ret < 0) {
            printf("SPI接收错误: %d\n", ret);
            break;
        } else if (ret > 0) {
            // 如果是新文件开始，以覆盖模式打开文件
            if (is_new_file) {
                fp = fopen(FILE_NAME, "wb");
                if (!fp) {
                    perror("文件打开失败");
                    break;
                }
                is_new_file = 0;  // 标记文件已开始写入
            }

            // 写入当前数据块
            size_t written = fwrite(receiveBuf, 1, ret, fp);
            if (written != ret) {
                perror("文件写入失败");
                break;
            }
            fflush(fp);  // 刷新缓冲区到磁盘
            
            printf("已接收 %d 字节 | 累计写入: %ld 字节\n", 
                  ret, ftell(fp));
        }

        // 检测到传输间隔（根据实际调整延时）
        //usleep(1000);  // 1ms短暂延时
		sleep(1);
        // 如果检测到发送端停止传输，则关闭文件并重置标记
        // （此处需根据实际协议添加更精确的传输结束检测）
        if (ret == 0) {
            fclose(fp);
            fp = NULL;
            is_new_file = 1;
            printf("检测到传输结束，等待新文件...\n");
        }
    }

    // 清理资源
    if (fp) fclose(fp);
    CloseUsb(0);
    return 0;
}