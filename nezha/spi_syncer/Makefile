# 哪吒侧实时深度帧 SPI 推送（x86_64，本机/哪吒原生编译）
CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra
TARGET   = spi_syncer

$(TARGET): spi_syncer.c ../acquisition/depth_proto.h
	$(CC) $(CFLAGS) -o $@ spi_syncer.c

clean:
	rm -f $(TARGET)

.PHONY: clean
