# spi_receiver 交叉/本机编译
# 默认 aarch64（部署到 RK3568），用系统 aarch64-linux-gnu-gcc（apt 安装）。
# 本机联调： make ARCH=x86_64   （运行需 LD_LIBRARY_PATH=deps/x86_64）

ARCH    ?= aarch64
CFLAGS  ?= -O2 -Wall -Wextra
TARGET   = spi_receiver

ifeq ($(ARCH),aarch64)
  CC     = aarch64-linux-gnu-gcc
  LIBDIR = deps/aarch64
else
  CC     = gcc
  LIBDIR = deps/x86_64
endif

$(TARGET): spi_receiver.c deps/USB2UARTSPIIICDLL.h
	$(CC) $(CFLAGS) -o $@ spi_receiver.c -Ideps -L$(LIBDIR) -lUSB2UARTSPIIIC

clean:
	rm -f $(TARGET)

.PHONY: clean
