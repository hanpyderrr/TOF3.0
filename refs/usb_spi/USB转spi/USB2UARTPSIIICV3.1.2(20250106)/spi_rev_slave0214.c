#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "USB2UARTSPIIICDLL.h"

// 假设这些函数已经在库中定义
extern int OpenUsb(unsigned int UsbIndex);
extern int ConfigSPIParamSlave(unsigned int fistBit, unsigned int subMode, unsigned int UsbIndex);
extern int SPISlaveRevData(unsigned char *rcvBuf, unsigned int len, unsigned int UsbIndex);
extern int CloseUsb(unsigned int UsbIndex);

int main() {
    unsigned char receiveBuf[1024]; // 接收缓冲区
    int ret;

    // 打开USB转SPI转接模块
    ret = OpenUsb(0);
    if (ret != 0) {
        printf("Failed to open USB device\n");
        return -1;
    }else{
		printf("successed to open USB device\n");
	}

    // 配置SPI从机模式：高位在前，模式0
    ret = ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0);
    if (ret != 0) {
        printf("Failed to configure SPI slave mode\n");
        CloseUsb(0);
        return -1;
    }else{
		printf("successed toconfigure SPI slave mode :0 and MSB\n"");
	}

    // 从SPI从机接收数据
    ret = SPISlaveRevData(receiveBuf, sizeof(receiveBuf), 0);
    if (ret < 0) {
        printf("Failed to receive data from SPI slave\n");
    } else {
        printf("Received %d bytes: ", ret);
        for (int i = 0; i < ret; i++) {
            printf("%02x ", receiveBuf[i]);
        }
        printf("\n");
    }

    // 关闭USB转SPI转接模块
    CloseUsb(0);

    return 0;
}