#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>

int main() {
    int fd = open("/dev/spidev0.0", O_RDWR);
    if (fd < 0) {
        perror("无法打开设备");
        return -1;
    }

    // 查询字节序（0=MSB，1=LSB）
    uint8_t lsb_first;
    if (ioctl(fd, SPI_IOC_RD_LSB_FIRST, &lsb_first) < 0) {
        perror("无法查询字节序");
        close(fd);
        return -1;
    }

    printf("当前字节序：%s\n", lsb_first ? "LSB" : "MSB");
    close(fd);
    return 0;
}