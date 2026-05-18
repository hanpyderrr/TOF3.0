#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "USB2UARTSPIIICDLL.h"

#define BUFFER_SIZE 1024
#define FILE_NAME "received.dat"

int main() {
    unsigned char receiveBuf[BUFFER_SIZE];
    int ret;
    FILE *fp = NULL;

    // 初始化USB设备
    ret = OpenUsb(0);
    if (ret != 0) {
        printf("Failed to open USB device\n");
        fclose(fp);
        return -1;
    } else {
        printf("Successfully opened USB device\n");
    }

    // 配置SPI从机模式：高位在前，模式0
    ret = ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0);
    if (ret != 0) {
        printf("Failed to configure SPI slave mode\n");
        CloseUsb(0);
        fclose(fp);
        return -1;
    } else {
        printf("Successfully configured SPI slave mode: Mode 0, MSB\n");
    }

    // 打开文件并保持句柄
    fp = fopen(FILE_NAME, "wb");
    if (fp == NULL) {
        perror("Failed to open file");
        CloseUsb(0);
        return -1;
    }

    printf("Start receiving data...\n");

    while (1) {
        // 接收数据块
        ret = SPISlaveRcvData(receiveBuf, BUFFER_SIZE, 0);
        if (ret < 0) {
            printf("SPI接收错误: %d\n", ret);
            break;
        } else if (ret > 0) {
            // 重置文件指针到开头并清空旧内容
            fseek(fp, 0, SEEK_SET);
            if (ftruncate(fileno(fp), 0) != 0) {
                perror("Failed to truncate file");
                break;
            }

            // 写入新数据并刷新缓冲区
            if (fwrite(receiveBuf, 1, ret, fp) != ret) {
                perror("文件写入失败");
                break;
            }
            fflush(fp);  // 强制刷新到磁盘

            printf("已更新 %d 字节\n", ret);
        }
        //usleep(1000);  // 短暂延时
        sleep(1);
    }

    // 清理资源
    fclose(fp);
    CloseUsb(0);
    return 0;
}