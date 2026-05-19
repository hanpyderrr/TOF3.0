# 工作进度

> 最后更新：2026-05-19
> 主控：Claude Opus 4.7

---

## 当前状态快照

**架构锁定并全项目文档重写：RK3568 实时 Qt MIPI 显示深度图；深度走 SPI 实时流；原始只哪吒本地存；5G 上云暂缓。SPI 物理链路已实测逐字节通。**

| 节点 | 状态 |
|------|------|
| 哪吒侧代码（P1–P6, P5a/b/c） | ✅ 已迁移；P5b/c（哪吒 CloudSyncer/FastAPI）仅本地开发用 |
| 哪吒 SSH 连通 | ✅ 192.168.31.79 ding/1234（paramiko；调试期有网） |
| RK3568 串口连通 | ✅ `/dev/ttyUSB0`@1500000（CH340 须慢写，见 docs/spi硬件接口.md） |
| **SPI 物理链路 哪吒→适配器→RK3568** | ✅ **实测逐字节通**（旧文本协议验证，详见 docs/spi硬件接口.md） |
| RK3568 5G | ✅ 插 SIM 冷启动后已注册联网（暂缓接入，本阶段不用） |
| 架构锁定 + 文档重写 | ✅ ARCHITECTURE/CLAUDE/framework/README/progress 已按锁定决策重写 |
| cloud_syncer 深度上传 | ✅ 已实现+离线 e2e；**归暂缓阶段，保留不动** |
| 哪吒 SpiSyncer（实时深度发送端） | ⬜ **本阶段新写** |
| RK3568 spi_receiver + Qt MIPI 显示 | ⬜ **本阶段新写**（交叉编译） |

---

## RK3568 硬件摸底（2026-05-18）

### 基本信息

| 项目 | 详情 |
|------|------|
| 板型 | ATK-DLRK3568（正点原子） |
| 系统 | Buildroot 2018.02-rc3（2024-08-29 编译） |
| 架构 | aarch64 |
| 登录 | root，无密码，开机自动进 shell |
| 内核 | Linux 4.19.232 aarch64，#4 SMP 2025-01-13（Linaro GCC 6.3.1） |
| 串口 | Linux `/dev/ttyUSB0`（CH340 `1a86:7523`），1500000 8N1；Windows COM7 为历史记录 |

### 可用环境

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.8.6 | ✅ 可直接写脚本 |
| Perl | 已装 | |
| BusyBox | v1.34.1 | 基本工具齐全 |
| make | 4.2.1 | ✅ |
| pip3 | 已装 | ✅ 可装 pyserial 等（开发主机端未装 pyserial，用 termios） |
| gcc/g++ | **无** | ❌ 不能原生编译 C/C++ |
| cmake | 无 | |

### 网络现状（2026-05-19 更新）

| 接口 | 状态 | 备注 |
|------|------|------|
| 哪吒 enp1s0 | UP，192.168.31.79，可上公网 | **生产无网，当前网线仅调试**；生产态数据不经哪吒上云 |
| RK3568 usb0 (5G) | ✅ 插 SIM 冷启动后已注册联网（NAT 出口） | China Telecom；**本阶段暂缓接入** |
| RK3568 eth0/eth1 | DOWN | 未接网线 |

> 5G 初次失败根因：SIM 未在模块上电时在位 → 冷启动（带 SIM）后注册成功。5G 链路本身已验证可通，但本阶段不接入（5G 上云暂缓）。

### SPI 设备树（2026-05-18 串口实测）

| 控制器 | status | 说明 |
|--------|--------|------|
| `spi@fe610000` | **disabled** | 未启用（此前文档假设的总线，实际不可用） |
| `spi@fe620000` | **okay** | 唯一启用；设备树已挂子节点 `stm32spi@0`（STM32 调焦电机） |
| `spi@fe630000` | disabled | 未启用 |
| `spi@fe640000` | disabled | 未启用 |

- spidev 驱动已加载，**`/dev/spidev1.0` 存在**。
- ✅ **已决策（2026-05-19）**：RK3568 侧不使用原生 SPI，改用 **USB转SPI 适配器模块**做 slave（沿用旧版已验证链路），fe620000 被 STM32 占用的问题就此绕开。详见 `docs/rk3568_framework.md`。

---

## 已完成工作记录

### 2026-05-19 — 联调连通 + 架构锁定 + 全项目文档重写

**用户锁定决策：**
- RK3568 屏幕**实时 Qt MIPI 显示深度图**（硬需求）
- 深度帧（2KB）走 **SPI 实时流**；原始 TCSPC（2MB）**只哪吒本地存档**
- **5G 上云（raw+depth）本阶段暂缓**，日后稳定再加；cloud_syncer 保留不动
- 哪吒生产无网（当前网线仅调试）；电机 RK3568 直连 STM32 串口

**实测/验证：**
- 哪吒 SSH 通（paramiko，无 sshpass）；RK3568 串口通（CH340 须慢写，否则丢首字节致 `Done(127)`）
- **SPI 物理链路哪吒原生引脚→USB-SPI 适配器(0483:5740)→RK3568 实测逐字节通**：哪吒旧 `spisendfile0402` 发 `raw.dat`，RK3568 旧 `spi_rev_slavemyloop` 收，received.dat 头部逐字节一致（md5/大小差为旧文本协议分帧尾差，非传输损坏）
- RK3568 5G 插 SIM 冷启动后注册联网（暂缓接入）
- 关键带宽事实：原始 14GB/h 受哪吒→RK SPI ~50–140KB/s 卡死，全量自动上云物理不可行

**文档重写（仅文档，不动代码）：**
- `ARCHITECTURE.md`、`CLAUDE.md`、`docs/rk3568_framework.md` 按锁定决策重写
- `rk3568/README.md` 及 spi_receiver/cloud_syncer/motor_controller/autostart 各 README 同步
- `docs/rk3568_reintegration_architecture.md` 横幅补新推翻项
- 新增 `docs/登录方式.md`、`docs/spi硬件接口.md`
- 旧"RK3568 不做显示/SPI 不做实时流/哪吒无网必经 SPI→5G 上云"表述全部更正

**风险/遗留：**
- 实时显示链路（哪吒 SpiSyncer + RK3568 spi_receiver + Qt 显示）三块未写，本阶段核心
- STM32 接 RK3568 哪个 /dev 节点未定（开放项 O2）
- SPI 链路验证用的是旧文本协议；TOF3.0 二进制深度帧协议（CMD0x10）细节待定（O4）

### 2026-05-19 — cloud_syncer 深度上传实现 + 离线 e2e

**用户确认：** 先做深度上传（D1=A 本地状态库续传；TCSPC 本轮不做）

**实现内容（`rk3568/cloud_syncer/`，Python 3.8 仅标准库）：**
- `config.py` 命令行/环境变量配置（不硬编码）
- `tof_parser.py` 解析 `.tof`（头 `TOFREC1\0` + 2062B/帧，与 datarecorder 一致）
- `state_db.py` sqlite 断点续传/幂等（仅 accepted 后推进 units_sent）
- `uploader.py` urllib POST `/api/frames/depth` + health；区分可重试/致命错误
- `buffer_scanner.py` 选完整 `.tof`（跳 `.part`/`.bad`）+ 坏文件隔离
- `status_writer.py` 原子写 `.upload_status.json`（供 spi_receiver 发 CMD=0x05）
- `cloud_syncer.py` 守护循环 + 信号 + 日志滚动；`sync_pass()` 可测试
- `tests/`：合成 `.tof` 生成器 + stdlib mock 云端 + e2e 脚本

**验证：** `python3 tests/test_e2e.py` —— 3 场景 14 项断言**全过**：
全量 137 帧上传、断网中断后续传（无重复/不丢帧，验证 D1=A 正确性）、坏文件隔离。
`py_compile` 全模块通过。本机 Python 3.10，已按 3.8 兼容写（仅标准库）。

**风险/遗留：**
- 仅 mock 云端验证，未对真实 FastAPI / RK3568 / 5G 联调（板上无网络、无 SIM）
- D1=A 残留：POST 成功但响应丢失时最多 1 个 batch 可能重复（设计内可接受）
- net_manager 未接入，暂用 `/api/health` 自探；与 spi_receiver 落盘/状态联调待做

### 2026-05-19 — 全项目梳理 + RK3568 框架定稿 + 修明显 bug

**用户确认决策：**
- SPI 接收：沿用 **USB转SPI 适配器**（旧版已验证，绕开原生 SPI 设备树问题）
- 电机控制：**RK3568 直连 STM32 串口**（19200 8N1，非经 SPI CMD=0x06，非留哪吒）
- 本轮范围：梳理 + 决策文档 + 修明显 bug，不写大块新实现

**实现内容：**
- 新增 `docs/rk3568_framework.md`（RK3568 侧权威框架：目录结构/模块/数据流/协议/部署/开放项/缺口）
- 搭建 `rk3568/` 骨架：`README.md` + `spi_receiver`/`cloud_syncer`/`motor_controller`/`autostart` 各模块设计 README
- 修正全项目文档架构矛盾（按确认决策）：
  - `CLAUDE.md`：SPI 链路改 USB转SPI；废弃 CMD 0x06；电机归属/STM32 连接更正；新增框架文档指引
  - `ARCHITECTURE.md`：硬件拓扑/SPI 物理层/CMD 表/电机焦距控制更正 + 顶部已确认决策提示
  - `docs/rk3568_reintegration_architecture.md`：顶部加"已被推翻/留档"横幅（原文两处自相矛盾）
- 修 `nezha/qt_app/motoruart.cpp` 协议 bug：
  - 第 6 字节由硬编码 `0x00` 改为校验和 `(0x02+device+cmdHi+cmdLo)&0xFF`
  - 齿轮指令 cmdHi 由错误的 `0x20/0x22`（滑台值）改为 `0x40/0x42`
  - 已与 STM32 串口指令文档/旧版 `motor.cpp` 全表逐条核对一致

**验证：**
- 文档改动：人工核对，无构建依赖
- `motoruart.cpp`：本机无 Qt5（开发机），无法本地编译；改动为常量算术 + 数组初始化，无 API/头文件变化，风险低；需在哪吒 `qmake && make` 验证（见 AGENTS.md 部署流程）

**风险/遗留：**
- `libUSB2UARTSPIIIC.so`（aarch64/x86_64）与已编译 `spi_rev_slavemyloop` 仅在 `单光子项目`，未拷入 TOF3.0（框架文档 §7 已记录为缺口）
- 电机闭环控制通道为开放项 O1（框架文档 §6）
- motoruart 校验和修正未经真实 STM32 回环验证，仅与协议文档核对

### 2026-05-18 — TOF3.0 项目初始化与目录重组

**实现内容：**
- 从 TOF2.0 迁移所有代码到 TOF3.0，保留 TOF2.0 不动
- 复制 `refs/`（PF32 手册、RK3568 文档）
- 复制 `rk3568/legacy/`（v1.0 电机 / SPI 参考代码）
- 按设备分层重组目录：
  - `acquisition/` → `nezha/acquisition/`
  - `qt_app/` → `nezha/qt_app/`
  - `ml/` → `cloud/ml/`
  - 新增 `rk3568/spi_receiver/`、`rk3568/cloud_syncer/`（占位）
- 更新 ARCHITECTURE.md、CLAUDE.md、AGENTS.md 所有路径
- 更新 `deploy/` 下 4 个脚本的本地/远程路径（TOF2.0→TOF3.0）
- 新增 `docs/rk3568_connection.md`（串口连接与硬件现状）
- 编写算法文档：
  - `docs/active_modulation_separation_algorithm.md`
  - `docs/rk3568_reintegration_architecture.md`

**已提交 commits：**
- `init: TOF 3.0 项目初始化`
- `refactor: 按设备分层重组目录结构 nezha/rk3568/cloud`

### 2026-05-18 — 哪吒侧（继承自 TOF2.0，已验证）

- `nezha/acquisition/sim_pf32.cpp` — 帧模拟器，~2Hz
- `nezha/qt_app/tof_viewer` — Qt 主程序，HDMI 显示
- `cloud/server/main.py` — FastAPI 4 端点，8765 端口
- CloudSyncer SQLite 队列，DataRecorder 本地录制

---

## 关键决策记录

| 时间 | 决策 | 原因 |
|------|------|------|
| 2026-05-18 | RK3568 回归，作为 5G 上行网关 | 哪吒无网络，RK3568 有 5G 模块 |
| 2026-05-18 | 电机控制迁移到 RK3568 | 有专用电机驱动引脚，复用 v1.0 代码 |
| 2026-05-18 | SPI 改为文件队列异步传输 | 避免实时流 SPI 不稳定 |
| 2026-05-18 | 主动调制分离算法思路 | 焦距/功率差分区分雾目标，文献无此方法 |
| 2026-05-18 | RK3568 侧优先用 Python 实现 | 板上无 gcc，Python 3.8 可用，无需交叉编译 |
| 2026-05-19 | SPI 接收用 USB转SPI 适配器（非原生 SPI） | 旧版已验证；绕开 fe620000 被 STM32 占用、其余 disabled 的设备树阻塞 |
| 2026-05-19 | 电机 RK3568 直连 STM32 串口（非 SPI CMD=0x06） | 沿用旧版 motorUart 已验证思路；SPI 仅文件队列，不承载实时控制 |
| 2026-05-19 | spi_receiver 走交叉编译（非纯 Python） | 需复用 aarch64 `libUSB2UARTSPIIIC.so` + 二进制帧解析；cloud_syncer/motor 仍 Python |
| 2026-05-19 | **RK3568 实时 Qt MIPI 显示深度图** | 用户硬需求；v1.0 已在板上跑过 Qt 显示 |
| 2026-05-19 | **深度帧走 SPI 实时流**（推翻"不做实时流"） | 2KB 帧带宽富余；当年坏的是 2MB 原始，非 SPI 本身 |
| 2026-05-19 | **原始 TCSPC 只哪吒本地存档** | 14GB/h 受 SPI ~50–140KB/s 卡死，全量自动上云不可行 |
| 2026-05-19 | **5G 上云本阶段暂缓** | 先打通实时显示；cloud_syncer 已就绪日后接 |

---

## 下一步工作计划

### 优先级排序（本阶段：打通实时深度显示链路）

| 优先级 | 任务 | 在哪做 | 依赖 |
|--------|------|--------|------|
| 🔴 | 补缺口：拷 `libUSB2UARTSPIIIC.so`(aarch64/x86_64)+头文件 入 `rk3568/spi_receiver/deps/` 与 `rk3568/legacy/lib/`（板上 /lib 已有可取） | 本地 | 无 |
| 🔴 | 定二进制深度帧协议细节（MAGIC/CMD0x10/CRC32，开放项 O4） | 本地 | 无 |
| 🔴 | 哪吒 SpiSyncer：算法出帧 → 低延迟推 `/dev/spidev1.0`（需 root） | 哪吒 | 协议定 |
| 🔴 | RK3568 spi_receiver：传输层照搬 0411.c + 二进制深度帧解析 → 交叉编译 | SDK 机 | 缺口+协议 |
| 🔴 | RK3568 Qt 显示程序：消费 TofFrame → MIPI 屏渲染 → 交叉编译 | SDK 机 | spi_receiver |
| 🟡 | 实时链路联调（哪吒发→RK 收→MIPI 屏显） | 两机 | 上述 |
| 🟡 | motor_controller（Python 串口下发） | 板上 | 开放项 O2（节点待定） |
| 🟡 | autostart（spi_receiver + Qt 显示） | 板上 | 上述实现 |
| ⏸️ | 【暂缓】5G 阶段：net_manager + cloud_syncer 接真实云 + 哪吒批量上行 + TCSPC 端点 | — | 系统稳定后 |
| 🟢 | P9 物理算法层 / P10 ML 训练 | 哪吒/云 | 真实数据 |

> 详细实施顺序见 `docs/rk3568_framework.md` §8。

### RK3568 SpiReceiver 开发方案

> 方案已定稿，详见 `docs/rk3568_framework.md` §3.1 / §8。要点：
> RK3568 是 **aarch64**，已编译的 `spi_rev_slavemyloop` 与 `libUSB2UARTSPIIIC.so` 均为 aarch64。
> 因需在传输层（OpenUsb/ConfigSPIParamSlave/SPISlaveRcvData）之上新增二进制组帧，
> 须在 SDK 机用 `aarch64-linux-gnu-gcc` 链接 aarch64 `libUSB2UARTSPIIIC.so` 交叉编译，
> 产物经串口 base64 传到板上。**不可纯 Python**（须链接厂商 .so）。

### 串口传输文件方法（无网络时）

```bash
# 在开发机：base64 编码
base64 binary_file > binary_file.b64

# 在串口 shell 中：
base64 -d binary_file.b64 > binary_file
chmod +x binary_file
```

---

## 待确认事项

| 问题 | 状态 |
|------|------|
| 哪吒↔RK3568 SPI 物理链路 | ✅ 实测逐字节通（USB转SPI 适配器 0483:5740） |
| SIM 卡 / 5G | ✅ 已插，冷启动注册联网；本阶段暂缓接入 |
| 二进制深度帧协议细节（MAGIC/CMD0x10/CRC32、是否用 INT 线、丢帧策略） | 🔴 开放项 O4，本阶段需先定 |
| STM32 接 RK3568 哪个 /dev 节点 | 🔴 开放项 O2，待用户确认接线 |
| spi_receiver 与 Qt 显示进程模型（合一/拆分） | 🟡 开放项 O6，实现时定 |
| 电机闭环控制通道（开放项 O1） | 🟡 当前默认 RK3568 本地/手动 |
| aarch64 交叉编译器（aarch64-linux-gnu-gcc）版本 | ⬜ 待确认（本机 rk3568_linux_sdk 内 Linaro 6.3.1 应匹配） |

---

## 文件变更追踪

| 文件 | 最近变更 | 状态 |
|------|---------|------|
| `nezha/qt_app/mainwindow.cpp` | Record 面板 UI | ✅ 已部署 |
| `nezha/qt_app/cloudsyncer.cpp` | SQLite 队列实现 | ✅ 已部署 |
| `cloud/server/main.py` | FastAPI 4 端点 | ✅ 运行中 |
| `ARCHITECTURE.md` | 按 3.0 双机架构重写 | ✅ |
| `CLAUDE.md` | 路径/架构全面更新 | ✅ |
| `AGENTS.md` | 更新为 TOF3.0 内容 | ✅ |
| `deploy/*.py` | 路径更新 TOF2.0→TOF3.0 | ✅ |
| `docs/rk3568_connection.md` | 补 Linux 连接(termios) + readline 自动化限制 | ✅ |
| `docs/rk3568_framework.md` | 新增 RK3568 权威框架文档 | ✅ 2026-05-19 |
| `rk3568/README.md` + 各模块 README | 目录骨架与模块设计 | ✅ 2026-05-19 |
| `CLAUDE.md` / `ARCHITECTURE.md` | 修正 SPI/电机架构矛盾 + 框架指引 | ✅ 2026-05-19 |
| `docs/rk3568_reintegration_architecture.md` | 加"已被推翻/留档"横幅 | ✅ 2026-05-19 |
| `nezha/qt_app/motoruart.cpp` | 修协议 bug（校验和 + 齿轮 cmdHi） | ✅ 2026-05-19 待哪吒编译验证 |
| `cloud/server/main.py` | 加 POST /api/frames/tcspc | ⬜ P9-1 |
| `rk3568/spi_receiver/spi_receiver.c` | 传输层 + 二进制组帧实现 | ⬜ 下一步 |
| `rk3568/spi_receiver/deps/` | 拷入 .h + aarch64/x86_64 .so | ⬜ 缺口 |
| `rk3568/cloud_syncer/*.py` | 深度上传实现（7 模块 + tests） | ✅ 2026-05-19 离线 e2e 通过 |
| `rk3568/cloud_syncer/` 全部 | 已实现+e2e；归暂缓阶段保留不动 | ⏸️ 暂缓 |
| `docs/cloud_syncer_plan.md` | 代码计划 + 决策 | ✅ 2026-05-19 |
| `rk3568/motor_controller/motor_ctl.py` | 串口下发电机指令 | ⬜ 待 O2 |
| `ARCHITECTURE.md` / `CLAUDE.md` / `docs/rk3568_framework.md` | 按锁定决策重写（实时显示/实时流/raw 本地/5G 暂缓） | ✅ 2026-05-19 |
| `rk3568/README.md` + spi_receiver/cloud_syncer/motor/autostart README | 同步锁定决策 | ✅ 2026-05-19 |
| `docs/登录方式.md` / `docs/spi硬件接口.md` | 新增（两机登录 + SPI 硬件接口+实测） | ✅ 2026-05-19 |
| `docs/rk3568_reintegration_architecture.md` | 横幅补新推翻项 | ✅ 2026-05-19 |
| 哪吒 `qt_app` 新 SpiSyncer（实时深度发送端） | 本阶段新写 | ⬜ |
| `rk3568/spi_receiver/spi_receiver.c` + RK3568 Qt 显示程序 | 本阶段新写（交叉编译） | ⬜ |
| `nezha/qt_app/cloudsyncer.*` | 维持本地开发用，不改 | — |
