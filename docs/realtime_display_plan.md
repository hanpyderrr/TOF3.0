# P-RT 实施计划：哪吒深度图 → RK3568 MIPI 屏实时显示

> 版本：2026-05-19
> 状态：**计划待批准**（用户同意后才动代码）
> 关联：`docs/rk3568_framework.md`、`docs/spi硬件接口.md`、`ARCHITECTURE.md`
> 决策来源（用户 2026-05-19）：①走**裸 TofFrame**，不加外层信封 ②先用**文件桥**跑通 ③已串口上板实测

---

## 0. 范围与已定决策

- 本阶段只做：哪吒出深度帧 → SPI → RK3568 收 → Qt 渲染到 MIPI 屏。**不做** 5G 上云、电机控制（各自独立阶段）。
- **裸帧**：SPI 上传输的就是 2070B 的 `TofFrame`（自带 magic `"TOFP"` + crc16-Modbus），**不加** `0xABCD/CMD/CRC32` 外层信封。外层信封留给暂缓的 5G 文件队列阶段。
- **文件桥**：spi_receiver 收齐一帧写 `received.dat`（二进制 2070B，flock），Qt 定时读——沿用旧版 `spi_rev_slavemyloop`→`received.dat`→Qt 已验证部署形态，改动最小。延迟（接收轮询+50ms Qt 定时）几十 ms 级，2fps 无感。
- 复用最大化：哪吒发送端、RK 解析+渲染、自启脚本均有现成可移植件（见 §2）。

---

## 1. 板上实测现状（2026-05-19 串口巡检，权威）

| 项 | 实测值 |
|----|--------|
| 系统/内核 | Buildroot，Linux **4.19.232 aarch64** |
| 板上编译器 | **无 gcc/g++/qmake**，仅 `python3 3.8.6` → 必须交叉编译 |
| Qt | **Qt 5.15.2** 完整安装（`/usr/lib/libQt5Core.so.5.15.2`），含 Widgets/Gui/OpenGL/Network/SerialPort/Sql 等 |
| Qt 平台插件 | `/usr/lib/qt/plugins/platforms`：`linuxfb`、`minimal`、`offscreen`、`vnc`、`wayland-egl`、`wayland-generic`（**无 eglfs/xcb**）|
| 显示 | `/dev/fb0`，DRM `card0-DSI-1`（MIPI），**虚拟分辨率 800×1280（竖屏）**，mode `U:800x1280p-0`；`S49weston` 在跑 |
| `QT_QPA_PLATFORM` | `/etc/profile` **未设**；旧 `SinglePhoton207_5` 经 `S51mydisplay` 以默认平台运行且可用 → 新程序复用同启动方式即可 |
| SPI slave 库 | **`/lib/libUSB2UARTSPIIIC.so`（aarch64，207K）已在板上** |
| 旧部署形态 | `/myApp/mytest/spireceive/`（`spi_rev_slavemyloop`+`.sh`+`received.dat`），`/myApp/mytest/qttest/SinglePhoton207_5` |
| 旧自启 | `/etc/init.d/S99myspireceive`（跑 `spi_rev_slavemyloop.sh`）+ `S51mydisplay`（跑 Qt，PID `/var/run`，日志 `/var/log`）|
| 当前 received.dat | **文本**（`Frame=0\n4 7 5...`）——新链路替换两端为二进制 2070B |
| 内存 | 3729MB，空闲 3532MB（Qt 充裕）|
| 唯一通道 | 串口 `/dev/ttyUSB0@1500000`（无网，传文件靠 base64，≈100KB/s）|

---

## 2. 可复用资产（来自 `单光子项目`）

| 用途 | 现成文件 | 复用方式 |
|------|---------|---------|
| 哪吒 SPI 发送 | `TOF/哪吒端/spisendTOF.c` | 移植，**改去重逻辑**（见步骤1）|
| RK 帧解析核心 | `TOF/RK3568端/tof_frame_parser_core.h` | 直接用，协议与 TOF3.0 `depth_proto.h` v1 一致 |
| RK Qt 解析层 | `TOF/RK3568端/depthParser.{cpp,h}` | 直接用（已读 2070B 二进制 + flock LOCK_SH）|
| RK Qt 渲染 | `TOF/RK3568端/depthWidget.{cpp,h}`、`pointCloudWidget.{cpp,h}` | 移植（jet 伪彩）|
| RK Qt 骨架 | `RK3568相关代码/客户端代码/SinglePhoton207_5/{main,mainwindow}.cpp` | 移植窗口/定时器骨架，**剔除**阿里云/课题2/转台/电机/文本 `image.cpp` |
| SPI 从机传输层 | `RK3568相关代码/.../spi_rev_slavemyloop0411.c` | 照搬传输层调用序列，应用层换二进制重组 |
| 自启脚本 | 板上 `S99myspireceive`、`S51mydisplay`、`spi_rev_slavemyloop.sh` | 镜像改路径 |

---

## 3. 线路帧格式（本阶段权威）

SPI 上**直接是 `TofFrame`，2070B，小端**（定义见 `nezha/acquisition/depth_proto.h` v1，RK 侧 `tof_frame_parser_core.h` 同协议）：

```
[0..3]  magic 0x50464F54 "TOFP"   [4] version=1   [5] headerSize=16
[6..7]  flags=0   [8..11] seq   [12..13] w=32   [14..15] h=32
[16..17] validCount   [18..19] reserved
[20..2067] depths 1024×uint16 mm (0=无效)   [2068..2069] crc16-Modbus(bytes[4..2067])
```

无外层信封、无 CMD、无 CRC32、无 ACK、不补传（丢帧只丢一帧画面）。RK 侧靠 magic `54 4F 46 50` 做流同步。

---

## 3.5 交叉编译环境（已确认 2026-05-19，R1/R2 已解决）

SDK 在 `~/rk3568_linux_sdk`，内含 Buildroot SDK，**与板子 userspace 同源**（板子是 Buildroot 2018.02-rc3 / Qt 5.15.2，SDK 一致）：

| 项 | 实测值 |
|----|--------|
| 输出根 | `~/rk3568_linux_sdk/buildroot/output/rockchip_rk3568/` |
| 交叉工具链 | `host/bin/aarch64-buildroot-linux-gnu-gcc`/`g++` **GCC 10.3.0**（Buildroot 2018.02-rc3-g06ff920f）|
| qmake | `host/bin/qmake` —— QMake 3.1，**Qt 5.15.2**，sysroot 已内建指向 |
| 目标 sysroot | `host/aarch64-buildroot-linux-gnu/sysroot/`（Qt5 头文件 `usr/include/qt5/` 全：Core/Gui/Widgets/OpenGL/Network/SerialPort/Sql…）|
| Qt 平台插件（SDK target）| `linuxfb`、`minimal`、`offscreen`、`vnc` —— **`linuxfb` SDK 与板上都有，作安全默认平台** |

> ⚠️ 修正：之前文档/记忆称交叉编译器 "Linaro 6.3.1" 是**内核**编译器（`docs/rk3568_connection.md` 内核行），与 userspace 无关。**应用层（spi_receiver/qt_display）一律用 SDK 的 `aarch64-buildroot-linux-gnu-gcc` 10.3.0**，它正是构建板子 Buildroot 2018.02-rc3 / Qt 5.15.2 的同一套，ABI 必匹配。

构建命令（确认可用）：

```bash
SDK=~/rk3568_linux_sdk/buildroot/output/rockchip_rk3568
HOST=$SDK/host/bin
# spi_receiver（纯 C + 板上 /lib 的 .so）
$HOST/aarch64-buildroot-linux-gnu-gcc -O2 -Wall -o spi_receiver spi_receiver.c \
    -Ideps -Ldeps/aarch64 -lUSB2UARTSPIIIC
# qt_display（用 SDK qmake，已自动接 sysroot）
$HOST/qmake qt_display.pro && make -j4
# 运行平台：linuxfb（与 legacy 一致，不设 QT_QPA_PLATFORM 也可，复用 S51 启动环境）
```

---

## 4. 分步实施

### 步骤 1 — 哪吒侧 `spi_syncer`（移植，小）
- 落点：`nezha/spi_syncer/spi_syncer.c`（独立进程，需 root 跑 `/dev/spidev1.0`；Qt 不改）。
- 基于 `TOF/哪吒端/spisendTOF.c`：`/dev/spidev1.0` MODE0/8bit/1.125MHz，单次 `SPI_IOC_MESSAGE(1)` 发 2070B。
- **必改**：原代码用 `is_file_modified()`（mtime，秒级粒度，sim 500ms/帧会漏发或重发）。改为读出 `TofFrame.seq`，**seq 变化才发**（与哪吒 Qt `onTimer` 去重一致）；读时 flock LOCK_SH，与写端 LOCK_EX 互斥。
- 验证：本机 `gcc -Wall` 编过；哪吒上 `sim_pf32` + `spi_syncer` 跑通不报错。

### 步骤 2 — RK3568 `spi_receiver`（新写，中，唯一真缺口）
- 落点：`rk3568/spi_receiver/spi_receiver.c` + `deps/`（`USB2UARTSPIIICDLL.h` + `libUSB2UARTSPIIIC.so` aarch64/x86_64）。
- 传输层照搬 `spi_rev_slavemyloop0411.c`：`OpenUsb(0)`→`ConfigSPIParamSlave(SPI_MSB,SPI_SubMode_0,0)`→循环 `SPISlaveRcvData(buf,len,0)`。
- 应用层（替换旧文本校验）：环形/累积 buffer → 扫 magic `54 4F 46 50` 对齐 → 凑满 2070B → `tof::parseFrameBuffer` 校验（magic/version/尺寸/crc16/范围）→ 通过则 flock LOCK_EX 覆写 `received.dat`（截断后写满 2070B）→ 失败丢弃并重新找 magic。
- 接收异常仅记日志重连，不阻塞（哪吒侧数据继续本地积累）。

### 步骤 3 — RK3568 Qt 显示（移植，中）
- 落点：`rk3568/qt_display/`（`main.cpp`、`mainwindow.{cpp,h}`、移入 `depthParser`/`depthWidget`/`tof_frame_parser_core.h`、`qt_display.pro`）。
- 骨架取自 `SinglePhoton207_5`：`QMainWindow` + `QTimer`(50ms) 轮询 `received.dat`。**剔除**：阿里云/课题2/转台/电机/文本 `image.cpp`。
- 渲染换 `depthParser::parse(received.dat)` → `depthWidget`（jet 伪彩，按 seq 去重）→ 适配 **800×1280 竖屏**（KeepAspectRatio，居中/letterbox）；窗口按屏幕几何全屏。
- `.pro`：`QT += core gui widgets`（点云可选 `opengl`）；去掉 legacy 的 `network serialport opengl -lz`（裸帧无 CRC32，不需 zlib）。

### 步骤 4 — 交叉编译与打包
- 用 §3.5 已确认的 SDK：`spi_receiver` 走 `aarch64-buildroot-linux-gnu-gcc` 10.3.0 链 `libUSB2UARTSPIIIC.so`；`qt_display` 走 SDK `host/bin/qmake`（Qt 5.15.2，sysroot 已内建）。
- 产物经串口 base64 传板（`base64 f>f.b64`→串口→板上 `base64 -d`），慢写规则见 `docs/rk3568_connection.md`。Qt 二进制 MB 级，串口 ≈100KB/s，数分钟可接受。

### 步骤 5 — 部署与自启
- 路径：`/myApp/tof3/spi_receiver/`、`/myApp/tof3/qt_display/`；`.so` 已在 `/lib/`。
- 自启镜像 legacy：`S99tof_spi_receiver`（跑 spi_receiver，PID `/var/run`、日志 `/var/log`）+ `S51tof_display`（在其后启 Qt）。落点 `rk3568/autostart/`。先手动验证再装自启。

### 步骤 6 — 联调验证
哪吒 `sim_pf32` + `spi_syncer` ↔ RK `spi_receiver` + `qt_display`：MIPI 屏出实时滚动深度图；核对 seq 连续、帧率≈2fps、`received.dat` 恒 2070B、crc16 全过。

### 步骤 7 — 回写文档
实测通过后改 O4（"本阶段裸 TofFrame，外层信封留 5G 阶段"）、O6（文件桥）于 `rk3568_framework.md`/`ARCHITECTURE.md`/`CLAUDE.md`/`AGENTS.md`/`progress.md`。

---

## 5. TOF3.0 内新增/改动文件

```
nezha/spi_syncer/spi_syncer.c              新增（移植 spisendTOF.c + seq 去重）
rk3568/spi_receiver/spi_receiver.c         新增
rk3568/spi_receiver/deps/                  新增（USB2UARTSPIIICDLL.h + aarch64/x86_64 .so）
rk3568/legacy/lib/libUSB2UARTSPIIIC.so     新增（留参考）
rk3568/qt_display/{main,mainwindow}.*      新增
rk3568/qt_display/{depthParser,depthWidget,pointCloudWidget,tof_frame_parser_core}.*  移植
rk3568/qt_display/qt_display.pro           新增
rk3568/autostart/S99tof_spi_receiver       新增
rk3568/autostart/S51tof_display            新增
```
不改现有 `nezha/qt_app/*` 和 `rk3568/cloud_syncer/*`。

---

## 6. 风险与开放项（需在动手前/中确认）

| # | 风险 | 处理 |
|---|------|------|
| ~~R1~~ ✅已解决 | Qt 交叉编译环境 | `~/rk3568_linux_sdk` 内 Buildroot SDK 含 qmake+Qt5.15.2 sysroot，与板子同源（§3.5）|
| ~~R2~~ ✅已解决 | aarch64 交叉工具链 | SDK `aarch64-buildroot-linux-gnu-gcc` **10.3.0**（非 Linaro 6.3.1，那是内核编译器），与板子 Buildroot 同套（§3.5）|
| R3 | Qt 二进制经 1.5M 串口 base64 传输慢（MB 级数分钟） | 可接受；spi_receiver 仅几十 KB 很快 |
| R4 | 默认 QPA 平台未最终确认 | 不阻塞：`linuxfb` SDK 与板上都有，作默认；复用 `S51mydisplay` 启动环境；集成时核对 |
| R5 | 屏 800×1280 竖屏，32×32 方图需取向/缩放 | depthWidget KeepAspectRatio 居中，必要时旋转，集成时目视调 |
| R6 | 协议偏离已锁文档（裸帧 vs 信封 O4） | 步骤7 回写，过渡期以本文件为准 |

---

## 7. 待办前置（动代码前）

- [x] Qt 5.15.2 aarch64 交叉编译环境 —— `~/rk3568_linux_sdk` 已确认（§3.5）
- [x] 交叉工具链 —— SDK `aarch64-buildroot-linux-gnu-gcc` 10.3.0 已确认（§3.5）
- [ ] 从板上取 `/lib/libUSB2UARTSPIIIC.so` 入 `rk3568/spi_receiver/deps/aarch64/`（串口 base64 回传）
- [ ] 用户批准本计划 → 即可开工（R1/R2 已清，无前置阻塞）
