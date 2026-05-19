# P-RT 实施计划：哪吒深度图 → RK3568 MIPI 屏实时显示

> 版本：2026-05-19
> 状态：**步骤1–5 完成；步骤6 联调：数据链路端到端实测通过（USB reset 后再验）；I2 屏显仍黑屏（QPA 已定位到 wayland、进程层已修但无可见输出，更深层问题未解）；I1 已得 USB unbind/bind 复位手段。详见 §9 / §9.6**
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
| `QT_QPA_PLATFORM` | ⚠️**已更正（§9.6）**：`/etc/profile.d/weston.sh` 实际**有设** `QT_QPA_PLATFORM=wayland` + `XDG_RUNTIME_DIR=/var/run`；旧 `SinglePhoton207_5` 是 **Weston wayland 客户端**（**不是** linuxfb——linuxfb 会与 Weston 抢 fb0 致黑屏）。新程序须 `. /etc/profile` 复用此环境 |
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
# 运行平台：⚠️ 更正——须 wayland（Weston 客户端），启动脚本 `. /etc/profile` 注入
#   QT_QPA_PLATFORM=wayland + XDG_RUNTIME_DIR=/var/run（详见 §9.6；旧"linuxfb"结论错误）
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
| ~~R4~~ → 转 I2 | 默认 QPA 平台 | **已定位（§9.6）**：实际是 `wayland`（Weston 客户端），**非** linuxfb。但用对平台后屏仍黑，问题升级为 I2（更深层，未解）|
| R5 | 屏 800×1280 竖屏，32×32 方图需取向/缩放 | depthWidget KeepAspectRatio 居中，必要时旋转，集成时目视调 |
| R6 | 协议偏离已锁文档（裸帧 vs 信封 O4） | 步骤7 回写，过渡期以本文件为准 |

---

## 7. 待办前置（动代码前）

- [x] Qt 5.15.2 aarch64 交叉编译环境 —— `~/rk3568_linux_sdk` 已确认（§3.5）
- [x] 交叉工具链 —— SDK `aarch64-buildroot-linux-gnu-gcc` 10.3.0 已确认（§3.5）
- [x] `libUSB2UARTSPIIIC.so` 入 `rk3568/spi_receiver/deps/{aarch64,x86_64}/`（本地 `单光子项目` 同库直接拷，比串口取更稳）
- [x] 用户批准本计划

## 8. 进度（2026-05-19 实施）

- [x] 步骤1 `nezha/spi_syncer/`（移植 spisendTOF + seq 去重）—— x86_64 编译通过
- [x] 步骤2 `rk3568/spi_receiver/`（传输层照搬 0411.c + 二进制重组 → /tmp/received.dat）—— aarch64 交叉 + x86_64 编译通过
- [x] 步骤3 `rk3568/qt_display/`（移植 depthParser/depthWidget + 精简骨架）—— SDK qmake 交叉编译通过（Qt5.15.2）
- [x] 步骤4 交叉编译验证（三者均通过，无报错/警告）
- [x] 步骤5 自启脚本 `rk3568/autostart/S95tof_spi_receiver`+`S96tof_display`
- [~] 步骤6 板上联调（2026-05-19，两轮）—— **数据链路端到端实测通过（USB reset 后再验，seq 持续递增）；I1 得 USB unbind/bind 复位手段；I2 QPA 已定位到 wayland、进程层修复但屏仍黑（更深层未解）。见 §9 / §9.6**
- [ ] 步骤7 联调全通过后回写 O4/O6 到 ARCHITECTURE/CLAUDE/AGENTS/framework

## 9. 联调实测结果与未决问题（2026-05-19）

### 9.1 已实测通过（数据链路端到端）

部署：哪吒源码在 `~/tof3-rt/`（板无网，gcc 11.4 本地编译 sim_pf32+spi_syncer）；
RK3568 产物 `/myApp/tof3/{spi_receiver,qt_display}/`（串口 base64 推，md5 校验一致）。

链路逐项实测 OK：
```
哪吒 sim_pf32 → /tmp/depth.dat(2070B, seq 递增)
哪吒 spi_syncer(root) → /dev/spidev1.0 SPI master MODE0/1.125MHz
USB转SPI 适配器 0483:5740（已枚举）
RK3568 spi_receiver → /tmp/received.dat
```
- `received.dat` 恒 **2070B**，magic `54 4f 46 50`(TOFP)、ver01/hdr16 正确
- seq 连续递增（实测 0x858→0x860→…→0xb57，多次确认，~2fps），
  说明 SPI 流重组 + crc16 校验全过、无明显丢帧
- **结论：裸 TofFrame 经 SPI 实时传输 + 文件桥 设计成立，已验证。**

### 9.2 未决问题（暂缓，用户叫停）

| # | 问题 | 现状/线索 |
|---|------|----------|
| I1 | **SPI 链路长跑会卡死** | 跑一阵后 spi_receiver 丢适配器，`ConfigSPIParamSlave=-2` 进重连死循环，received.dat 冻结（哪吒侧仍在产帧）。清杀两端 + 单实例重启可恢复；疑似适配器需 USB reset/断电。**适配器易 wedge，需稳定性方案** |
| I2 | **qt_display 屏显未目视确认** | 板上 Weston 在跑（PID608，wayland socket `/var/run/wayland-0`）。前台带 tty 跑 wayland 版 ≥6s 静默不崩；`start-stop-daemon -b` 守护化时 wayland-egl 版即死、无 env 版存活但屏显未确认。旧 `SinglePhoton207_5` 经 `S51mydisplay`(init 上下文) 可显示——那是已知可行启动方式 |
| I3 | 串口 DTR 杀进程 | 已解：两二进制加 `signal(SIGHUP,SIG_IGN)`，板上常驻用 `start-stop-daemon -b` |

### 9.3 本次代码改动（已编译/部署）

- `rk3568/spi_receiver/spi_receiver.c`：+ `signal(SIGHUP,SIG_IGN)`；默认输出 `/tmp/received.dat`
- `rk3568/qt_display/main.cpp`：+ `signal(SIGHUP,SIG_IGN)`
- 二者已重编（SDK 交叉）、重推板上、md5 校验一致

### 9.4 下一步建议（待用户定）

1. **I2 走已知可行路径**：仿 `S51mydisplay`(init/无 tty 上下文 + `. /etc/profile`) 启动 qt_display，
   而非交互串口；或定位 legacy 实际 QPA 平台与 Weston 集成方式。
2. **I1 稳定性**：spi_receiver 重连时主动 USB reset 适配器（USBDEVFS_RESET）；
   或确认适配器供电/线缆；评估长跑丢帧率。
3. 装 `S95/S96` 自启 + 禁旧自启（哪吒 crontab、RK3568 S99）后整机重启在生产上下文复测。

### 9.5 环境状态（仅本次会话，未持久化）

- 哪吒：停了 legacy `test207final.sh`/`spisendfile0402`；crontab `@reboot` 旧管线**未改**，重启复活
- RK3568：停了 legacy `spi_rev_slavemyloop`；`S99myspireceive` **未改**，重启复活
- 旧自启与新 S95/S96 均**未安装/未禁用**，未改两机持久配置（待用户决定切换）

---

## 9.6 第二轮联调（2026-05-19，清现场 + USB reset + QPA 定位）

### 9.6.1 现场清理 + 数据链路再验通过

- 杀两机残留：哪吒 `sim_pf32`/`spi_syncer`；RK3568 旧 wedged `spi_receiver`(PID1117)/`qt_display`(PID1470，无 env 版)
- 板上二进制曾丢失（仅剩旧 received.dat），**三件套全部重新交叉编译 + 重新部署**：
  spi_syncer(x86_64,SFTP→哪吒)、spi_receiver(aarch64)、qt_display(aarch64)，串口 base64 推 + md5 校验一致
- 哪吒源 `sim_pf32` 用 `~/tof3-rt/acquisition/sim_pf32`（TOF3.0 版，2fps，场景=7000mm 背景墙＋2800mm 正弦移动球体＋5% 无效像素，即"球状突出"图）
- **数据链路 USB reset 后再次端到端实测通过**：received.dat 恒 2070B、magic TOFP/ver1/hdr16，
  seq 实时持续递增（564→590→830，多次确认），证明清掉 wedge 后链路稳定流动

### 9.6.2 I1 — 根因 + 已验证复位手段

- **根因**：USB-SPI 适配器（0483:5740，板上枚举为 **CDC-ACM**，sysfs 端口 `2-1`）在 USB 层 wedge；
  设备号反复递增（003→011）即重复重枚举的证据。`CloseUsb/OpenUsb` 不做真正 USB 复位，故 wedge 后死循环
- **已验证复位手段**：起 spi_receiver 前执行
  `echo 2-1 > /sys/bus/usb/drivers/usb/unbind; sleep1; echo 2-1 > /sys/bus/usb/drivers/usb/bind`
  → 内核 `cdc_acm 2-1:1.0: ttyACM0` 干净重枚举，wedged 态清除，链路恢复。
  与控制台 CH340（`1a86:7523`，不同端口）互不影响，安全
- **未做**：把该复位内置进 spi_receiver 重连逻辑（长跑中再 wedge 时自动 USBDEVFS_RESET / sysfs rebind）。
  当前仅为启动前一次性手动复位

### 9.6.3 I2 — 根因定位（进程层已修，屏仍黑，未解决）

- **关键定位**：旧可运行 `SinglePhoton207_5` 经 `S51mydisplay` 启动，脚本 `. /etc/profile`；
  `/etc/profile.d/weston.sh` 设 `XDG_RUNTIME_DIR=/var/run` + **`QT_QPA_PLATFORM=wayland`**
  → 旧 app 是 **Weston 下的 wayland 客户端**（**非** linuxfb；linuxfb 抢 fb0 与 Weston 冲突 → 黑屏）。
  之前守护版崩，是因为用了板上**无 EGL 软栈**的 `wayland-egl`
- 本轮 qt_display 用 `/tmp/qd.sh`(`. /etc/profile` + `exec qt_display`) 经 `start-stop-daemon -Sbx` 启动：
  **进程稳定存活不崩**（PID1824，>25s），qt_display 已链接 `libwayland-client`，
  日志仅 1 条无害告警 `QStandardPaths: runtime directory '/var/run' is ... symbolic link`，
  **无 QPA 致命错误、无 "cannot connect to wayland display"、无崩溃**
- **但用户目视：屏幕仍黑屏**。即"进程层已修复（平台选对、连上 Weston、不崩）但仍无可见输出"，
  **I2 未解决**，属更深层问题。候选方向（下一步排查，未做）：
  1. Weston 是否已被别的全屏客户端占用 / qt_display 窗口未 map / 未 raise / 未 fullscreen
  2. 800×1280 竖屏窗口几何（show() 后实际尺寸/位置；旧 app 是否 `showFullScreen()`）
  3. `DepthWidget` 重绘路径：QTimer 是否真触发、`received.dat` 是否真被解析、`update()`/paintEvent
  4. wayland 共享内存 buffer 是否真提交（对照旧 `SinglePhoton207_5` 的窗口创建/显示调用）
  5. 直接以 `S51mydisplay` 同款 init 上下文（而非 start-stop-daemon）启动对照

### 9.6.4 本轮改动

- **无源码改动**（沿用上轮 SIGHUP-ignore）；本轮为部署/环境层定位
- 新增板上启动方式 `/tmp/qd.sh`：`. /etc/profile` → `exec /tmp/qt_display`（注入 wayland 环境）
- 仓库整理：补 `.gitignore`（新目录二进制 / qmake 生成 Makefile/moc / .qmake.stash），
  清构建产物，提交源码+脚本+文档（不提交二进制/`.so`/`.o`），推 GitHub

### 9.6.5 环境状态（仍仅本次会话）

- 哪吒：`sim_pf32`/`spi_syncer`(root) 仍在跑（可按需停）；crontab 旧自启**未改**
- RK3568：`spi_receiver`(1791)/`qt_display`(1824,黑屏) 仍在跑；适配器已 unbind/bind 过一次；
  `S99myspireceive` **未改**；新 S95/S96 仍未装。两机持久配置均未动，重启复活旧管线
