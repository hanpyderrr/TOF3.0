#include <stdio.h>
#include "USB2UARTSPIIICDLL.h" // 假设这是你的库文件

int main() {
    unsigned char receiveBuf[256]; // 接收缓冲区
    OpenUsb(0); // 打开USB设备

    // 设置SPI从机参数
    ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0);

    // 预装数据（可选，具体看应用场景）
    // SPISlavePreloadData(preloadBuf, preloadLen, 0);

    while (1) {
        // 接收数据
        int bytesRead = SPISlaveRcvData(receiveBuf, sizeof(receiveBuf), 0);
        if (bytesRead < 0) {
            printf("Error receiving data: %d\n", bytesRead);
            continue; // 错误处理，继续接收
        }
        
        // 处理接收到的数据
        printf("Received %d bytes: ", bytesRead);
        for (int i = 0; i < bytesRead; i++) {
            printf("%02X ", receiveBuf[i]);
        }
        printf("\n");
    }

    CloseUsb(0); // 关闭USB设备
    return 0;
}