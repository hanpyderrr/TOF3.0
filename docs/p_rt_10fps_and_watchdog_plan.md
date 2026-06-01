# P-RT 链路 10 fps 升级 + USB 抖动兜底 实施计划

> 日期：2026-05-31
> 上下文：P-RT 全链路（PF32 → 哪吒 → SPI → RK3568 → MIPI 屏）端到端已通；
> 本文是后续两项优化的实施计划，关联 `docs/realtime_display_plan.md`（原始实施计划）。

---

## 1. 项目当前状态（2026-05-31 节点）

### 1.1 已落地（本周新增，已 commit）

| 文件 | 改动要点 |
|---|---|
| `nezha/acquisition/ExampleTOF.cpp`（新） | 基于 PF32 SDK 1.5.21，TCSPC sys_master 全初始化序列；写 `/tmp/depth.dat` + 可选 `.tch` raw 落盘 |
| `nezha/acquisition/CMakeLists.txt` | SDK 锁 1.5.21（1.5.23 库要 GLIBCXX_3.4.32 哪吒 g++ 11.4 装不动）+ rpath |
| `deploy/setup_pf32_runtime.sh`（新） | 幂等建 `~/Firmware`、`~/tof3-rt/source` 符号链接；解 SDK 内部相对/默认路径找不到资源 |
| `nezha/autostart/tof-acquisition.service` | `sim_pf32` → `ExampleTOF` + ExecStartPre 跑 setup + Env 默认值 |
| `nezha/spi_syncer/spi_syncer.c` | `setvbuf(_IOLBF)` 让 journal 实时 + POLL_USEC 20000→5000 削轮询延迟 |
| `docs/rk3568_connection.md` 等 | CH340 命令首字节被吃 + 加 8 空格 padding 自动化方案入档 |

### 1.2 端到端链路（已实测通）

```
PF32 (USB) → 哪吒 ExampleTOF (2 fps) → /tmp/depth.dat
  → spi_syncer (root, SPI MODE0 1.125MHz, 2070B/帧)
  → USB-SPI 适配器 (0483:5740)
  → RK3568 spi_receiver → /tmp/received.dat
  → qt_display (50ms timer) → MIPI 屏 (1280×773)
```

### 1.3 实测延迟拆分（端到端 ≈ 580 ms 最坏，~330 ms 平均）

| 段 | 实测/估算 | 主导因素 |
|---|---|---|
| **PF32 积分窗** | **500 ms** | `TOF_INTEGRATION_S=0.5`，物理积分，**最大瓶颈** |
| ExampleTOF proc + 写盘 | 3 ms | |
| spi_syncer 平均轮询 | 2.5 ms | POLL_USEC=5000 |
| SPI wire 2070B | 14.7 ms | 1.125 MHz |
| USB-SPI 适配器中转 | ~5-10 ms | STM32 转发 |
| RK spi_receiver | 2-5 ms | usleep(2000) 轮询 + 写盘 |
| qt_display timer | 25 ms 平均 | `setInterval(50)` |
| Qt paintEvent + MIPI vsync | 17 ms | 60 Hz |

---

## 2. 问题 1：USB 抖动后链路冻屏

### 2.1 症状

跑一段时间（实测 ~925 秒后）MIPI 屏冻在最后一帧。`/tmp/received.dat` seq 停在某值（如 5490），qt_display log 反复 `received.dat readable, waiting for new seq = 5490`。

### 2.2 根因

```
dmesg: usb 2-1: new high-speed USB device number 5  ← USB 设备重新枚举
       cdc_acm 2-1:1.0: ttyACM0: USB ACM device     ← cdc_acm 抢绑 interface 0/1（实际不冲突）
       process X (spi_receiver) did not claim interface 2 before use
spi_receiver.log: SPISlaveRcvData=-2, reconnect
                  OpenUsb=-1 (循环)
```

USB 设备短暂 disconnect → reconnect 让 device number 变化，`libUSB2UARTSPIIIC` 不能处理 device renumber，spi_receiver 内部 reconnect 死循环 OpenUsb=-1。`/etc/init.d/S95tof_spi_receiver restart` 能临时恢复（杀进程 + rmmod cdc_acm + USB unbind/bind），但启动后无运行期监控。

### 2.3 修复 → Phase 1

---

## 3. 问题 2：当前 2 fps 偏低

### 3.1 各段位能力 vs 实测

| 段 | 物理/工程上限 | 当前实测 | 富余 |
|---|---|---|---|
| **PF32 累积成直方图** | 100 fps（10ms 积） | **2 fps**（瓶颈） | 1× |
| ExampleTOF 处理 | > 100 fps | 不限 | 50× |
| spi_syncer SPI 推送 | ~50 fps（SPI wire + POLL）| 不限 | 25× |
| USB-SPI 适配器 | ~50 fps | 不限 | 25× |
| RK spi_receiver | > 100 fps | 不限 | 50× |
| **qt_display** | 20 fps（`setInterval(50)`） | 跟着上游 | 第二瓶颈 |
| MIPI 屏 | 60 Hz | 60 fps | OK |

### 3.2 帧率 vs 信号 tradeoff

| `TOF_INTEGRATION_S` | 帧率 | SNR | 适用 |
|---|---|---|---|
| 0.5 s（当前） | 2 fps | ★★★★★ | 调试 / 远距 / 弱信号 |
| **0.1 s** | **10 fps** | ★★★ | **推荐工作点**：流畅 + 信号够亚 bin cm 精度 |
| 0.05 s | 20 fps | ★★ | 强光近距、运动跟踪 |
| 0.033 s | 30 fps | ★ | 极限，5 ns 脉宽下 SNR 逼近底噪 |

### 3.3 推荐：10 fps + qt_display 跟到 60 Hz → Phase 2 + Phase 3

---

## 4. 实施计划（4 阶段，预计 ~40 min）

### Phase 1 — RK3568 USB 抖动兜底（~10 min）

| 步骤 | 动作 | 验证 |
|---|---|---|
| 1.1 | 即时关 USB autosuspend：`echo on > /sys/bus/usb/devices/2-1/power/control` | `cat .../power/control == on` |
| 1.2 | udev rule 持久化：`/etc/udev/rules.d/99-usb-spi-autosuspend.rules` 匹配 idVendor=0483 idProduct=5740 → `ATTR{power/control}="on"` | reload + 重 plug 验 |
| 1.3 | watchdog 脚本：每 30s 看 `/tmp/received.dat` mtime，停滞 > 60s 就 `/etc/init.d/S95tof_spi_receiver restart`，含 90s cooldown 防循环 | 手动 echo off 模拟，60s 内自愈 |
| 1.4 | `init.d` 拉起 watchdog：`/etc/init.d/S97tof_spi_watchdog`（BusyBox 风格 nohup loop） | `pgrep watchdog` |
| 1.5 | 入仓：`rk3568/autostart/99-usb-spi-autosuspend.rules`、`rk3568/autostart/tof_spi_watchdog.sh`、`rk3568/autostart/S97tof_spi_watchdog` | git status |

### Phase 2 — 哪吒 10 fps（~5 min，最简单）

| 步骤 | 动作 |
|---|---|
| 2.1 | 改 `nezha/autostart/tof-acquisition.service`：`Environment=TOF_INTEGRATION_S=0.1`（0.5 → 0.1） |
| 2.2 | sftp 推 → sudo cp 到 `/etc/systemd/system/` → daemon-reload → restart tof-acquisition |
| 2.3 | 验证：ExampleTOF journal seq 涨速 ~10/s；spi_syncer journal `last_seq` 跟上、`dropped=0` |

### Phase 3 — qt_display setInterval 50→16 ✅ 完成（2026-06-01）

**经历**：本机交叉编译 + 串口部署失败（Rockchip FIQ Debugger 反复劫持 console，CH340 长流量伪 break 触发，25 chunks 只能稳传 ~8 个）→ 改 U 盘 vfat 分区部署成功。

**关键经验**：
- RK3568 文件系统**只支持 vfat，不支持 exfat**。Ventoy U 盘要用其 VTOYEFI 分区（vfat 32 MB）不是主 Ventoy 分区（exfat）。
- 替换正在运行的 ELF 报 `Text file busy`，必须先 `S96 stop` 释放文件锁、cp、`S96 start`，不能用 `restart`（restart = stop + start，但 stop 和 cp 之间有窗口被旧进程占住）。
- 不要在替换流程里嵌套 `if/fi` + 双引号 + 变量插值——CH340 串口下复合命令易解析炸。分步原子命令更稳。
- U 盘插 RK 后会被自动 mount 到 `/media/udisk0`（不是 `/mnt`）。

**实际部署步骤**：

| 步骤 | 动作 | 结果 |
|---|---|---|
| 3.1 | 改 `rk3568/qt_display/mainwindow.cpp:47` setInterval(50) → 16 | ✅ |
| 3.2 | 本机交叉编译 `$SDK/host/bin/qmake && make -j4` | ✅ ELF 58 KB md5 `37bcf80b…` |
| 3.3 | `file` 校验 ELF 64-bit aarch64 | ✅ |
| 3.4 | 本机 `cp qt_display /media/ding/VTOYEFI/`（vfat 分区，不是 exfat 主分区）+ `sync` | ✅ |
| 3.5 | U 盘插 RK：自动 mount 到 `/media/udisk0/qt_display` | ✅ |
| 3.6 | `/etc/init.d/S96tof_display stop` 释放文件锁 → `cp /media/udisk0/qt_display /myApp/tof3/qt_display/qt_display` → `chmod +x` | ✅ |
| 3.7 | 目标位置 md5 校验匹配本机 | ✅ `37bcf80b…` |
| 3.8 | `/etc/init.d/S96tof_display start` + 看 log | ✅ PID 2561，paintEvent 启动、read frame seq 持续 |
| 3.9 | `umount /media/udisk*` 后拔 U 盘 | ✅ |

### Phase 4 — 端到端验证 + commit（~5 min）

| 步骤 | 动作 |
|---|---|
| 4.1 | 哪吒 ExampleTOF 10fps → spi_syncer → RK spi_receiver → qt_display → MIPI 屏全链路目视 |
| 4.2 | 模拟 USB 抖动（echo off + on autosuspend），看 watchdog 60s 内自愈 |
| 4.3 | git status / diff，一个 commit 收口（涉及 nezha/autostart、rk3568/autostart、rk3568/qt_display） |

---

## 5. 风险与对策

| 风险 | 对策 |
|---|---|
| watchdog 误判反复 restart 拖死 SPI | 90 s cooldown；连续 N 次 restart 失败则停止 + 报错日志 |
| udev rule 影响其他 USB 设备 | rule 精确 idVendor=0483 idProduct=5740 锁定 |
| qt_display 交叉编译用了主机 GCC | step 3.3 `file` 校验 aarch64 |
| 串口传输中途丢字节、装错二进制让 qt_display 起不来 | md5 不一致**不替换**；老二进制保留可一键回退 |
| 改 `setInterval(16)` 后 qt_display CPU 上升 | 当前 5.2%，预估 10-15% 可接受 |
| 10 fps 后链路某段瓶颈未察觉 | Phase 2 完成时查 spi_syncer `dropped=0` + qt_display `read frame seq` 与上游一致 |
