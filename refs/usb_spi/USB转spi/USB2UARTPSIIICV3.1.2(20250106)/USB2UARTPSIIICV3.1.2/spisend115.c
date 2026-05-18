#include <stdio.h>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>


int main() {
    int fd = open("/dev/spidev1.0", O_RDWR);
    if (fd < 0) {
        perror("Failed to open SPI device");
        return -1;
    }

    uint8_t mode = SPI_MODE_0;
    uint8_t bits = 8;
    uint32_t speed = 1125000;

    ioctl(fd, SPI_IOC_WR_MODE, &mode);
    ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &bits);
    ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);

    
    uint8_t rxbuf[4096];          // 接受数据
    memset(rxbuf, 0, 4096);
    int index = 0;

    while(1){
        uint8_t tx[] = {0x01};  // 发送数据1表示接受数据
        struct spi_ioc_transfer tr = {
        .tx_buf = (unsigned long)tx,
        .rx_buf = (unsigned long)rxbuf[index],
        .len = sizeof(rxbuf),
        };
        ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
        printf("Received: 0x%02X\n", rxbuf[index]);
        if(rxbuf[index] == '\n' || index >=4095){
            rxbuf[index] = '\0';//终止字符串
            printf("Received: %s\n", rxbuf);

            memset(rxbuf,0,4096);//重置缓冲区
            index = 0;
        }else{
            index++;//下一个字符
        }
        sleep(1);//

    }
 
    close(fd);
    return 0;
}