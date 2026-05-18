#include <stdio.h>  
#include <stdlib.h>  
#include <string.h>  
#include <unistd.h>  
#include <fcntl.h>  
#include <sys/file.h>  // 文件锁支持  

#include "USB2UARTSPIIICDLL.h"  

#define BUFFER_SIZE 8192      // 接收缓冲区大小（需足够容纳一帧数据）  
#define FILE_NAME "received.dat"  
#define TARGET_DATA_COUNT 1024  // 目标数据个数  
#define LINE_BUF_SIZE 128     // 单行缓冲区大小  

FILE *fp = NULL;  
unsigned char globalBuf[BUFFER_SIZE]; // 全局接收缓冲区  
int globalBufLen = 0;                // 缓冲区当前长度  

// 检查缓冲区首行是否为 "Frame=0"  
int isFrameValid(const unsigned char *buf) {  
    char firstLine[LINE_BUF_SIZE];  
    int i = 0;  
    while (i < globalBufLen && buf[i] != '\n' && i < LINE_BUF_SIZE - 1) {  
        firstLine[i] = buf[i];  
        i++;  
    }  
    firstLine[i] = '\0';  
    return (strcmp(firstLine, "Frame=0") == 0);  
}  

// 检查第二行是否有 1024 个以空格分隔的数据  
int isDataValid(const unsigned char *buf, int bufLen) {  
    int lineStart = 0;  
    int dataCount = 0;  

    // 找到第二行起始位置（跳过第一行）  
    while (lineStart < bufLen && buf[lineStart] != '\n') lineStart++;  
    if (lineStart >= bufLen) return 0;  // 无第二行  
    lineStart++;  // 跳过换行符  

    // 统计第二行数据个数  
    int isPrevSpace = 1;  // 初始视为空格以避免开头空格干扰  
    for (int i = lineStart; i < bufLen; i++) {  
        if (buf[i] == '\n' || buf[i] == '\0') break;  // 行结束  
        if (buf[i] == ' ') {  
            if (!isPrevSpace) dataCount++;  // 新空格分隔符  
            isPrevSpace = 1;  
        } else {  
            isPrevSpace = 0;  
        }  
    }  
    // 最后一个数据可能无结尾空格  
    if (!isPrevSpace && buf[bufLen - 1] != ' ') dataCount++;  

    return (dataCount == TARGET_DATA_COUNT);  
}  

// 清空文件并写入缓冲区数据（带文件锁）  
void writeToFile(const unsigned char *buf, int bufLen) {  
    int fd = fileno(fp);  
    if (fd == -1) {  
        perror("获取文件描述符失败");  
        return;  
    }  

    // 获取独占锁  
    if (flock(fd, LOCK_EX) == -1) {  
        perror("文件加锁失败");  
        return;  
    }  

    // 清空文件并写入  
    ftruncate(fd, 0);  
    rewind(fp);  
    if (fwrite(buf, 1, bufLen, fp) != bufLen) {  
        perror("文件写入失败");  
    }  
    fflush(fp);  

    // 释放锁  
    flock(fd, LOCK_UN);  
}  

int main() {  
    unsigned char receiveBuf[BUFFER_SIZE]; // 临时接收缓冲区  
    int ret;  

    // 初始化USB设备  
    ret = OpenUsb(0);  
    if (ret != 0) {  
        printf("Failed to open USB device\n");  
        return -1;  
    }  
    printf("Successfully opened USB device\n");  

    // 配置SPI从机模式  
    ret = ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0);  
    if (ret != 0) {  
        printf("Failed to configure SPI slave mode\n");  
        CloseUsb(0);  
        return -1;  
    }  
    printf("Successfully configured SPI slave mode: Mode 0, MSB\n");  

    // 打开文件（二进制写入模式）  
    fp = fopen(FILE_NAME, "wb");  
    if (fp == NULL) {  
        perror("Failed to open file");  
        CloseUsb(0);  
        return -1;  
    }  

    printf("Start receiving data...\n");  

    while (1) {  
        ret = SPISlaveRcvData(receiveBuf, BUFFER_SIZE - globalBufLen - 1, 0);  
        if (ret < 0) {  
            printf("SPI接收错误: %d\n", ret);  
            break;  
        } else if (ret > 0) {  
            // 将新数据追加到全局缓冲区  
            memcpy(globalBuf + globalBufLen, receiveBuf, ret);  
            globalBufLen += ret;  
            globalBuf[globalBufLen] = '\0';  // 确保字符串终止  

            // 检查帧头是否有效  
            if (!isFrameValid(globalBuf)) {  
                printf("无效帧头，清空缓冲区\n");  
                globalBufLen = 0;  // 清空缓冲区  
                continue;  
            }  

            // 检查数据格式是否有效  
            if (isDataValid(globalBuf, globalBufLen)) {  
                printf("收到有效数据帧，写入文件\n");  
                writeToFile(globalBuf, globalBufLen);  
                globalBufLen = 0;  // 清空缓冲区  
            } else {  
                printf("数据不完整，继续接收...\n");  
                // 如果数据不完整，但缓冲区中的数据过长也要考虑清空缓冲区以避免内存泄漏  
                if (globalBufLen > BUFFER_SIZE / 2) {  
                    printf("缓冲区太长，清空缓冲区\n");  
                    globalBufLen = 0;  // 清空缓冲区  
                }  
            }  
        }  
        usleep(50000);  // 避免忙等待  
    }  

    // 清理资源  
    fclose(fp);  
    CloseUsb(0);  
    return 0;  
}  
