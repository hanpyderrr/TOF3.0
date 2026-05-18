// SPDX-License-Identifier: GPL-2.0-only
/*
 * SPI send utility (using spidev driver)
 *
 * This program sends data from a file (raw.dat) over SPI.
 */

#include <stdint.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <sys/stat.h>

#define DEVICE "/dev/spidev1.1"
#define SPEED 500000  // SPI speed in Hz
#define BITS_PER_WORD 8

static void pabort(const char *s) {
    perror(s);
    abort();
}

static void send_file(int fd, const char *filename) {
    struct stat sb;
    uint8_t *tx;
    ssize_t bytes;

    if (stat(filename, &sb) == -1)
        pabort("can't stat input file");

    int tx_fd = open(filename, O_RDONLY);
    if (tx_fd < 0)
        pabort("can't open input file");

    tx = malloc(sb.st_size);
    if (!tx)
        pabort("can't allocate tx buffer");

    bytes = read(tx_fd, tx, sb.st_size);
    if (bytes != sb.st_size)
        pabort("failed to read input file");

    struct spi_ioc_transfer tr = {
        .tx_buf = (unsigned long)tx,
        .len = sb.st_size,
        .speed_hz = SPEED,
        .bits_per_word = BITS_PER_WORD,
    };

    if (ioctl(fd, SPI_IOC_MESSAGE(1), &tr) < 1)
        pabort("can't send spi message");

    free(tx);
    close(tx_fd);
}

int main() {
    int fd = open(DEVICE, O_RDWR);
    if (fd < 0)
        pabort("can't open device");

    // Set SPI mode
    uint8_t mode = SPI_MODE_0;
    if (ioctl(fd, SPI_IOC_WR_MODE, &mode) == -1)
        pabort("can't set spi mode");

    // Set bits per word
    if (ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &BITS_PER_WORD) == -1)
        pabort("can't set bits per word");

    // Set max speed
    if (ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &SPEED) == -1)
        pabort("can't set max speed");

    printf("Sending data from %s...\n", "raw.dat");
    send_file(fd, "raw.dat");

    close(fd);
    return 0;
}