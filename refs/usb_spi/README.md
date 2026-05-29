# refs/usb_spi — USB 转 SPI 适配器文档索引

USB 转 SPI 适配器模块（USB ID `0483:5740`，STM32 方案），用于 RK3568 侧做 SPI slave。

## 目录结构

```
refs/usb_spi/
└── USB转spi/
    ├── USB2UARTPSIIICV3.1.1(20240919)/   驱动库版本 3.1.1（2024-09-19）
    ├── USB2UARTPSIIICV3.1.2(20250106)/   驱动库版本 3.1.2（2025-01-06）
    └── USB2UARTPSIIICV3.1.2(20250203)/   驱动库版本 3.1.2（2025-02-03，最新）
```

## 本项目用法

- RK3568 侧：适配器插 USB 口做 SPI slave（`libUSB2UARTSPIIIC.so` + `USB2UARTSPIIICDLL.h`）
- 哪吒侧：`/dev/spidev1.0`，MODE0，1.125MHz，SPI master（原生引脚，需 root）
- 物理链路已实测逐字节通（2026-05-19）

## 关键调用序列

```c
OpenUsb(0)
ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0)
loop: SPISlaveRcvData(buf, len, 0)
CloseUsb(0)
```

> 详见 `rk3568/legacy/RK3568使用SPI接收数据代码/spi_rev_slavemyloop0411.c`（传输层参考）
> 权威框架：`docs/rk3568_framework.md §3.1`
