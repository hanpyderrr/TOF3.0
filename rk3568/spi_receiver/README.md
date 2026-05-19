# spi_receiver — SPI slave 收实时深度帧（本阶段核心）

实施计划见 [`docs/realtime_display_plan.md`](../../docs/realtime_display_plan.md)（权威，含已锁决策）；
背景设计见 [`docs/rk3568_framework.md`](../../docs/rk3568_framework.md) §3.1。

## 职责

USB转SPI 适配器做 SPI slave，收哪吒（`/dev/spidev1.0` master, MODE0, 1.125MHz）
推来的**裸 TofFrame**（2070B），在无边界字节流中按 magic 同步、校验后**覆写
`received.dat`（二进制定长 2070B，flock）**，由同侧 Qt 显示程序读出渲染（**文件桥**）。

## 帧格式（裸帧，本阶段决策）

SPI 上直接是 `TofFrame` 2070B，自带 magic `0x50464F54`（小端字节 `54 4F 46 50`）
+ crc16-Modbus，**无外层信封**（无 `0xABCD/CMD/CRC32`、无 ACK、不补传，丢帧只丢一画面）。
外层信封/文件队列（CMD 0x01–0x05）属**暂缓的 5G 批量上传阶段**，本模块不实现。

## 传输层（沿用旧版已验证物理链路，勿改）

- 库：`deps/aarch64/libUSB2UARTSPIIIC.so`（板上 `/lib/` 已存在同库）+ `deps/USB2UARTSPIIICDLL.h`
  > ⚠️ 仓库 `.gitignore` 全局忽略 `*.so`，**两个 `.so` 不入 git**（仅头文件入库）。
  > 构建前自备：板上 `/lib/libUSB2UARTSPIIIC.so`（aarch64），或 `单光子项目` 同库（aarch64/x86_64）→ 放 `deps/{aarch64,x86_64}/`
- 调用：`OpenUsb(0)` → `ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0)` → 循环 `SPISlaveRcvData`
- 参考：`../legacy/RK3568使用SPI接收数据代码/spi_rev_slavemyloop0411.c`（仅传输层借鉴；旧版校验文本帧，不复用）
- 接收异常仅记日志并 `CloseUsb`+重连，不退出（哪吒侧数据继续本地积累）

## 构建（板上无 gcc，用 SDK 交叉编译）

```bash
make                 # 默认 aarch64（板子），用 ~/rk3568_linux_sdk 工具链
make ARCH=x86_64     # 本机联调用（需 LD_LIBRARY_PATH=deps/x86_64 运行）
make clean
```

产物经串口 base64 传板上 `/myApp/tof3/spi_receiver/`；板上 `/lib/libUSB2UARTSPIIIC.so` 已就位。

## 运行

```bash
./spi_receiver [received_dat_path]    # 默认 /tmp/received.dat（板上 tmpfs，免 eMMC 磨损）
```

设备/路径不硬编码。下游 Qt 显示见 `rk3568/qt_display/`（待实现），上游见 `nezha/spi_syncer/`。

## 状态

✅ `deps/USB2UARTSPIIICDLL.h` 入库（`.so` 因 `*.so` 策略不入库，构建前自备，见上）；
`spi_receiver.c` 已实现，aarch64 交叉 + x86_64 本机编译均通过（-Wall -Wextra 无警告）。
✅ 板上联调：数据链路端到端实测通过（received.dat 2070B/TOFP，seq 持续递增）。
详见 `docs/realtime_display_plan.md` §9 / §9.6。
