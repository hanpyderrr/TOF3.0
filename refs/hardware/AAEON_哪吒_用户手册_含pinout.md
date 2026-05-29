# AAEON_哪吒_用户手册_含pinout

> AAEON「哪吒」嵌入式开发套件用户手册，含完整 40-pin HAT GPIO 引脚定义。

## 关键信息

### 硬件规格

| 项目 | 详情 |
|------|------|
| 处理器 | Intel N97 / Alder Lake-N，x86_64 |
| 板型 | 仿树莓派，85 × 56 mm |
| 操作系统 | Ubuntu（预装） |
| 连接器 | CN1~CN11，共 11 个 |

### 主要连接器

| 连接器 | 功能 |
|--------|------|
| **CN3** | **40-pin HAT GPIO**（树莓派兼容排针） |
| CN7 | 10-pin USB/UART wafer |
| CN9 | Front Panel |
| CN10 | DC 电源 wafer |
| CN11 | 风扇 |

### CN3 HAT GPIO 关键引脚

| 引脚 | 功能 | 说明 |
|------|------|------|
| 1 | 3.3V 电源 | |
| 2 | 5V 电源 | |
| 4 | 5V 电源 | |
| 6 | GND | |
| **8** | **UART_TX / GPIO16** | 激光器串口 TX，3.3V TTL |
| **9** | **GND** | |
| **10** | **UART_RX / GPIO17** | 激光器串口 RX，3.3V TTL |

- **HAT 所有 GPIO 电平：3.3V TTL**（不能直接对接 5V 设备信号线）
- 5V 电源引脚（pin 2/4）可用于给电平转换板的 VCCB 供电

### 本项目用途

- CN3 pin 8/10：哪吒 UART，接激光器 P4（经分压电阻降压保护）
- CN3 pin 2 或 4：5V 电源，可给电平转换板 VCCB 端供电（如需用 TXS0108E）
