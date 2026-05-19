# 哪吒 → RK3568 SPI 硬件接口（沿用单光子旧版已验证链路）

> 更新：2026-05-19
> 来源：旧项目 `/home/ding/workspace/单光子项目`（同一台哪吒，hostname `ding-UP-ADLN01`）
> 旧代码、旧测试数据在两台机器上**原样保留**，本链路在单光子项目中已实测跑通。

---

## 一、物理链路

```
哪吒 NUC                                    RK3568 (ATK-DLRK3568)
┌──────────────┐                           ┌──────────────────────┐
│ 原生 SPI 引脚 │                           │                      │
│ /dev/spidev1.0│  SPI 4 线                 │  USB 口              │
│  (SPI master) │──MOSI/MISO/SCLK/CS──┐     │   ▲                  │
└──────────────┘                      │     │   │ USB              │
                              ┌───────▼─────┴───┴──────┐          │
                              │  USB 转 SPI 适配器模块   │          │
                              │  (STM32, USB ID 0483:5740│          │
                              │   做 SPI slave)          │          │
                              └──────────────────────────┘          │
                                                  RK3568 经 USB 识别 │
                                                  libUSB2UARTSPIIIC  │
                                                  做 SPI slave 收数   │
                              └──────────────────────────────────────┘
```

- **哪吒侧**：用主板**原生 SPI 引脚**，内核 `/dev/spidev1.0` 作 **SPI master**。哪吒上无 USB 转 SPI 适配器（已确认 `lsusb` 无 `0483`）。
- **适配器模块**：哪吒 SPI 引脚（MOSI/MISO/SCLK/CS）接到 USB-SPI 适配器的 SPI 排针；适配器 USB 端插 RK3568 USB 口。该模块是 STM32 方案，USB ID **`0483:5740`**。
- **RK3568 侧**：不使用 RK3568 原生 SPI（设备树被占/disabled），而是通过 USB 识别适配器，用厂商库 `libUSB2UARTSPIIIC.so` 把适配器配成 **SPI slave** 收数。
- 适配器资料：`单光子项目/参考文档/USB转SPI模块资料/USB转spi.zip`。

> 验证状态：`lsusb` 在 RK3568 上可见 `0483:5740`（适配器 USB 端已连），在哪吒上无（哪吒走原生引脚）。SPI 引脚↔适配器排针的物理接线只能靠实跑数据确认。

---

## 二、SPI 参数（两侧必须一致）

| 参数 | 值 | 出处 |
|------|-----|------|
| 设备（哪吒） | `/dev/spidev1.0`（root-only，需 sudo） | `spisendfile0402seek.c` |
| 角色 | 哪吒 = master，适配器/RK3568 = slave | — |
| 模式 | **SPI_MODE_0**（slave 侧 `SPI_SubMode_0`） | 收发两端代码 |
| 位序 | MSB first（slave 侧 `SPI_MSB`） | `ConfigSPIParamSlave` |
| 速率 | **1125000 Hz**（1.125 MHz） | sender `speed=1125000` |
| 字长 | 8 bit | `bits=8` |
| 分块 | **4096 B / 块** | `MAX_BLOCK_SIZE` |
| 块间延时 | 5 ms（代码注释写 50ms，实际 `usleep(5000)`） | sender 内层循环 |
| 帧间延时 | 50 ms（`usleep(50000)`，整文件发完后） | sender 外层循环 |

---

## 三、收发端代码与数据格式

### 发送端（哪吒，x86 原生编译）

- 源码：`单光子项目/哪吒相关代码/哪吒向RK发送/SPIsend_tsh/spisendfile0402seek.c`
- 哪吒现存可执行：`/home/ding/SPIsend_tsh/spisendfile0402`（x86-64 ELF，可直接跑）
- 行为：循环读固定文件 `/home/ding/SPIsend_tsh/raw.dat`，整文件按 4096B 分块经 `SPI_IOC_MESSAGE` 发出，发完 sleep 50ms 再从头发；带文件锁/mtime 检测（采集端在写则等待）。
- 重编译：`cd ~/SPIsend_tsh && gcc -o spisendfile0402 spisendfile0402seek.c`
- 运行（spidev1.0 仅 root）：`echo <密码> | sudo -S ~/SPIsend_tsh/spisendfile0402`

### 接收端（RK3568，交叉编译）

- 源码：`单光子项目/RK3568相关代码/RK3568使用SPI接收数据代码/spi_rev_slavemyloop0411.c`（0411 为最新稳定版，0402 会卡住）
- 板上部署：`/myApp/mytest/spireceive/`，含 `spi_rev_slavemyloop`、`spi_rev_slavemyloop.sh`、`USB2UARTSPIIICDLL.h`；动态库 `libUSB2UARTSPIIIC.so` 在 `/lib/`
- **必须用脚本启动**：`cd /myApp/mytest/spireceive/ && ./spi_rev_slavemyloop.sh`（直接跑可执行会出问题——见旧 readme）
- 行为：`OpenUsb(0)` → `ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0)` → 循环 `SPISlaveRcvData` 累积到全局缓冲，校验通过后写 `received.dat`（`flock` 互斥、`ftruncate` 清空覆盖写）
- 开机自启动（旧版）：`/etc/init.d/S99myspireceive`

### 数据帧格式（旧版文本协议）

接收端**硬校验**，不符合直接丢弃：

```
第1行: Frame=0\n               <- isFrameValid: 首行必须严格等于 "Frame=0"
第2行: v1 v2 v3 ... v1024      <- isDataValid: 必须恰好 1024 个空格分隔数
```

- 哪吒现存 `raw.dat`：2159 B，第1行 `Frame=0`，第2行恰好 **1024** 字段（与接收端 `TARGET_DATA_COUNT=1024` 匹配）。
- 接收端 `BUFFER_SIZE=8192`，缓冲超 4096 仍不完整则清空。
- ⚠️ TOF3.0 实际要传**二进制 `.tof`**（类型/数据量都变），此文本协议仅用于**复用旧链路做通路验证**；二进制传输需另行适配收发端解析。

---

## 四、连通性测试方法

> 目的：仅验证「哪吒原生 SPI → 适配器 → RK3568」物理链路与收发程序是否还通。用旧文本协议去风险，不引入新代码。

1. RK3568：清空 `received.dat` → 后台启动 `./spi_rev_slavemyloop.sh`
2. 哪吒：`echo 1234 | sudo -S ~/SPIsend_tsh/spisendfile0402` 跑数秒后停
3. RK3568：停接收端，检查 `received.dat` —— 首行 `Frame=0`、第2行 1024 字段、大小 ≈2159B；与哪吒 `raw.dat` 的 `md5sum` 对比
4. 判定：`md5` 完全一致 = 链路完好；结构合法但有帧尾残字节 = 链路通（分帧尾差，旧版亦如此）；`received.dat` 不变/空 = 链路不通（优先查 SPI 引脚↔适配器排针接线）

### 测试结果（2026-05-19）—— ✅ 链路通

实跑：RK3568 起 `spi_rev_slavemyloop.sh`（接收端），哪吒 `sudo spisendfile0402` 发 `raw.dat` 约 8s。

| 侧 | 证据 |
|----|------|
| 哪吒发送 | `s.log`：`文件总大小: 2159 字节` / `[批次 1] 已发送 2159 字节`（经 `/dev/spidev1.0` 循环发出） |
| RK3568 接收 | `r.log`：`Successfully opened USB device` → `configured SPI slave: Mode 0, MSB` → `Start receiving data...` → 数十次 `收到有效数据帧，写入文件` |
| 落盘 | `received.dat` 0 → **4054 B**，头部 `Frame=0\n4 7 5 5 3 2 4 1 1 12 6 2 8 3 4...` 与哪吒 `raw.dat` **逐字节一致** |

**结论**：哪吒原生 SPI 引脚 → USB 转 SPI 适配器 → RK3568 物理链路与收发程序**仍然通**，哪吒发的数据 RK3568 能收到。

**已知现象（非故障）**：

- `received.dat` 大小 4054 ≠ raw.dat 2159，`md5` 不一致：旧发送端**死循环**整文件连发、仅 50ms 帧间隔且帧无显式定界，接收端缓冲会把下一帧开头一并写入（一整帧 2159 + 下一帧残段 ≈ 4054）。这是旧文本协议的**分帧尾差**，旧项目即如此，靠上层按 `Frame=` 标记切分；**不是传输损坏**（内容前缀完全匹配）。
- 启动初期约 24 次 `无效帧头，清空缓冲区`：上电对齐期，正常。
- 内核 `usbfs: process did not claim interface 2 before use`：`libUSB2UARTSPIIIC` 的良性告警，旧版一直有，不影响收数。

**对 TOF3.0 的提示**：二进制 `.tof` 传输需自定义带长度/CRC 的显式分帧，不能沿用「`Frame=0`+1024 文本数」这套隐式定界；适配器/物理链路本身已验证可用。

### 串口操作要点（连 RK3568 调试踩坑）

- CH340 1.5Mbaud 下板子输入会**丢首字节**：写命令须**逐块慢写**（≤3 字节/块，间隔 ~6ms），每条命令前发 `Ctrl-U`(0x15) 清行，否则命令被截断（典型 `Done(127)`）。
- 命令带唯一 marker（如 `echo X_$(...)_END`）再从回显里提取；勿用 here-doc / 长管道批处理。
- 全程**单一持久 fd**，`cflag` 清 `HUPCL`、置 `CLOCAL`；多次重开 CH340 会翻转 DTR 复位板子。
- `.sh` 用 `#!/bin/bash`，板上 `/bin/bash`(968K) 存在、`/bin/sh→bash`，可直接 `nohup .../xxx.sh &`。
