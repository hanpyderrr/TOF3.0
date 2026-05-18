#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "USB2UARTSPIIICDLL.h"

#define BUFFER_SIZE 1024    // 接收缓冲区大小
#define FILE_NAME "received.dat"
FILE *fp = NULL;


int main() {
    unsigned char receiveBuf[BUFFER_SIZE]; // 接收缓冲区
    int ret;


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

    printf("Start receiving data... (Press Ctrl+C to stop)\n");

    // 打开文件（写入二进制模式，会截断0）ab是追加二进制
    fp = fopen(FILE_NAME, "wb");
    if (fp == NULL) {
        perror("Failed to open file");
        return -1;
    }

    // 主接收循环
    while (1) {
        // 接收数据块
        ret = SPISlaveRcvData(receiveBuf, BUFFER_SIZE, 0);
        if (ret < 0) {
            printf("SPI接收错误: %d\n", ret);
            break;
        } else if (ret > 0) {

            // 写入文件
            if (fwrite(receiveBuf, 1, ret, fp) != ret) {
                perror("文件写入失败");
                break;
            }
            fflush(fp);  // 刷新缓冲区到磁盘

            // 打印调试信息
            printf("Received %d bytes | Total saved: %ld bytes\n",
                   ret, ftell(fp));
        }
        sleep(1);  // 短暂延时避免忙等待
    }

    // 清理资源

    fclose(fp);
    CloseUsb(0);

    return 0;
}