# spi_receiver — SPI slave 收实时深度帧（本阶段核心）

完整设计见 [`docs/rk3568_framework.md`](../../docs/rk3568_framework.md) §3.1。

## 职责

USB转SPI 适配器做 SPI slave，收哪吒（`/dev/spidev1.0` master, MODE0, 1.125MHz）
推来的**实时二进制深度帧**，按 MAGIC 同步 + CRC32 校验 → 解析 TofFrame
→ 低延迟交 Qt 渲染到 MIPI 屏 → **即弃**（RK3568 不落盘，无文件重组、无 ACK）。

## 传输层（沿用旧版已验证物理链路，勿改）

- 库：`libUSB2UARTSPIIIC.so`（aarch64）+ `deps/USB2UARTSPIIICDLL.h`
- 调用：`OpenUsb(0)` → `ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0)` → 循环 `SPISlaveRcvData(buf, len, 0)`
- 参考实现：`../legacy/RK3568使用SPI接收数据代码/spi_rev_slavemyloop0411.c`（仅传输层借鉴）
- 物理链路今日已实测逐字节通，见 `docs/spi硬件接口.md`

## 与旧版的关键区别

旧版 0411.c 校验**文本帧**（`Frame=0` + 1024 空格整数），**不复用**。本阶段为实时二进制深度帧：

```
[MAGIC:2B 0xABCD][CMD:1B=0x10 DEPTH_FRAME][SEQ:4B LE][LEN:4B LE][PAYLOAD: TofFrame 2070B][CRC32:4B]
```

实时流：丢帧只影响一帧画面，不补传、不 ACK。
文件队列协议（CMD 0x01–0x05）属**暂缓的 5G 批量上传阶段**，本模块本阶段不实现。

## 构建

板上无 gcc → 在 x86 SDK 机交叉编译：

```
aarch64-linux-gnu-gcc -O2 -o spi_receiver spi_receiver.c -Ideps -Ldeps -lUSB2UARTSPIIIC
```

产物 + aarch64 `libUSB2UARTSPIIIC.so` 经串口 base64 传板上 `/myApp/tof3/spi_receiver/`，库放 `/lib/`。
x86_64 .so 仅供开发机本地联调。

## 与 Qt 显示的进程模型

可合一进程（接收线程 + Qt 主线程经队列交帧）或拆两进程（共享内存/本地 socket）——开放项 O6，实现时定。

## 缺口

- `deps/`：`USB2UARTSPIIICDLL.h` + aarch64/x86_64 `libUSB2UARTSPIIIC.so` 待补
  （源：`单光子项目/RK3568相关代码/RK3568使用SPI接收数据代码/`；板上 `/lib/libUSB2UARTSPIIIC.so` 已存在可取）
- `spi_receiver.c` 待实现（传输层照搬 0411.c，应用层重写为二进制深度帧解析）
