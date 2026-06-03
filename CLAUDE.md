# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

TOF 单光子 3.0：双机协作架构。
- **哪吒 NUC**（Intel N97，x86_64）：采集、算法处理、激光实时闭环、**本地全量存档**（raw+depth）。生产环境**无网络**（当前网线仅调试）。
- **RK3568**（aarch64，Buildroot，有 Qt+MIPI 屏 + 5G）：**实时 Qt MIPI 屏显深度图** + 镜头电机控制 +（日后）5G 上行网关。

## 已锁定决策（2026-05-19，权威；2026-06-03 更新同步模式）

1. **RK3568 屏幕实时 Qt MIPI 显示深度图**（硬需求，v1.0 单光子已在 RK3568 跑过 Qt 显示）。
2. 深度帧（TofFrame 2KB）走 **SPI 实时流**；原始 TCSPC（2MB）**只哪吒本地存档**，不过 SPI/5G。
3. **RK3568 经 5G 上云（raw+depth）本阶段暂缓**，日后稳定再加；`rk3568/cloud_syncer`（已实现+e2e 过）保留不动归暂缓阶段。
4. SPI 接收走 **USB转SPI 适配器**（USB ID 0483:5740，非 RK3568 原生 SPI），物理链路已实测可用。
5. 电机 **RK3568 直连 STM32 串口**（19200 8N1，非经 SPI CMD=0x06）。
6. **TCSPC 同步模式：laser_master**（2026-06-03 确认）。PF32 sys_master TRIG SMA 输出硬件故障（无信号，SDK 1.5.21/1.5.25 均排查无效），改用信号发生器同时驱动激光 P3 和 PF32 SYNC SMA（+3.3V peak，50Ω）；ExampleTOF.cpp 已切换至 `setMode(TCSPC_laser_master)`。

> 完整架构见 `ARCHITECTURE.md`；RK3568 侧权威设计见 `docs/rk3568_framework.md`。

## 硬件环境

| 设备 | 规格 | 连接 |
|------|------|------|
| 哪吒 SBC | **AAEON「哪吒」开发套件**（Intel N97 / Alder Lake-N，x86_64 嵌入式 SBC，仿树莓派 85×56mm），Ubuntu，**生产无网络**。**40-pin HAT GPIO** + 10-pin USB/UART wafer（CN7）+ HDMI + 3×USB3 + 1GbE。HAT UART 在 CN3 pin 8 (TX) / pin 10 (RX)，3.3V TTL。规格 `refs/hardware/AAEON_哪吒_用户手册_含pinout.pdf` | SSH: ding/1234（调试期） |
| RK3568 | **ATK-DLRK3568 改版底板**（基于 V1.5），aarch64，Buildroot，内核 4.19，**有 5G** | 串口 /dev/ttyUSB0@1500000；USB 接 SPI 适配器 |
| PF32 探测器 | 32×32 SPAD，TCSPC，55ps/bin，TCSPC **laser_master**（SYNC 输入驱动时序） | USB（Opal Kelly）→ 哪吒 |
| 激光驱动器 | YSC-SO-M04-4，Modbus RTU 9600 8N1（**激光侧 5V TTL**），**信号发生器外触发** | 推荐 **哪吒 HAT CN3 pin 8/10 UART** + 5V↔3.3V 电平转换板 → 激光 TTL 串口；外触发 P3 ← 信号发生器（同轴）；PF32 SYNC SMA ← 同一信号发生器（+3.3V peak，50Ω，同轴） |
| STM32F103C8T6 | 调焦电机控制 + 板内串口桥，**焊死在改版底板**（不再外挂模块） | USART1 → RK3568 **`/dev/ttyS4`**（JP2 短接 3-5/4-6，19200 8N1） |
| TMC2209 ×2 | 步进电机驱动，**直接焊在改版底板** | STM32 GPIO → MOTOR1（调焦滑台）/ MOTOR2（光圈齿轮） |
| USB转SPI 适配器 | STM32 方案，USB ID 0483:5740 | 哪吒 SPI 引脚 ↔ 适配器，适配器 USB ↔ RK3568 |

> 改版板原理图：`refs/hardware/ATK-DLRK3568_改版底板原理图_2026-05-29.pdf`
> UART 全表 + JP 跳线 + 激光接线方案：`docs/board_custom_uart_mapping.md`（权威）

## SPI 链路（哪吒 ↔ RK3568）

> ✅ 已确认（2026-05-19，物理链路实测逐字节通）：RK3568 侧用 **USB转SPI 适配器模块**做 slave，沿用旧版已验证物理链路；**不**使用 RK3568 原生 SPI。详见 `docs/spi硬件接口.md`、`docs/rk3568_framework.md`。

```
哪吒 /dev/spidev1.0 → SPI master（MODE0, 1.125MHz）原生引脚（需 root）
   │ USB转SPI 适配器模块（0483:5740）
RK3568 USB → 适配器做 SPI slave（libUSB2UARTSPIIIC）→ Qt MIPI 实时显示
```

**本阶段传输模式：实时深度流**（2KB/帧，低延迟），承载 `[MAGIC][CMD=0x10][SEQ][LEN][TofFrame 2070B][CRC32]`。
原始 TCSPC（2MB）只哪吒本地存档；文件队列/5G 批量上传协议（CMD 0x01–0x05）属**暂缓阶段**。

## 构建命令

```bash
# 哪吒上执行 ——
# acquisition
cd ~/TOF3.0/nezha/acquisition && g++ -std=c++17 -O2 -o sim_pf32 sim_pf32.cpp
# qt_app
cd ~/TOF3.0/nezha/qt_app && qmake tof_viewer.pro && make -j4
# 运行（哪吒本地可选显示 + 实时深度推 SPI）
DISPLAY=:1 ./tof_viewer --depth-file /tmp/depth.dat --laser-port /dev/ttyUSB0 --data-dir ~/tof-data

# RK3568 侧 spi_receiver / Qt 显示程序 —— 板上无 gcc，交叉编译（见 docs/rk3568_framework.md）
# 工具链：rk3568_linux_sdk 的 aarch64-linux-gnu-gcc（Linaro 6.3.1，匹配板子内核）

# cloud（仅本地开发；生产暂缓）
cd ~/TOF3.0/cloud/server && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8765 &
```

## 核心架构

### 数据流（本阶段）

```
PF32 → nezha/acquisition/ExampleTOF 或 sim_pf32
  → /tmp/depth.dat              (轻量帧，Qt 实时读)
  → ~/tof-data/raw_tcspc/      (TCSPC 原始 2MB/帧，仅哪吒本地存档)
  → ~/tof-data/depth_queue/    (深度帧本地存档，DataRecorder)

哪吒 Qt (nezha/qt_app/tof_viewer)
  → DepthWidget / PointCloudWidget (哪吒本地可选显示)
  → FeedbackController → LaserUart (激光实时闭环，不过 SPI)
  → SpiSyncer【本阶段新写】低延迟推 TofFrame(2KB) → /dev/spidev1.0

RK3568 (rk3568/spi_receiver + 新 Qt 显示程序)
  → SpiReceiver 收二进制深度帧
  → Qt MIPI 屏实时渲染深度图 → 即弃（RK 不落盘）
  → MotorController → 串口 → STM32 → TMC2209 镜头电机（本地直控，不经 SPI）

【暂缓】RK3568 → 5G → 公网云平台（raw+depth 批量上传）
```

### SPI CMD 定义

| CMD | 方向 | 含义 | 本阶段 |
|-----|------|------|--------|
| 0x10 | 哪吒→RK | DEPTH_FRAME 实时深度帧（TofFrame 2070B） | ✅ 核心 |
| 0x01–0x05 | 双向 | QUERY/FILE_SEND/CHUNK/ACK/UPLOAD_STATUS | 暂缓（5G 阶段） |

> ~~0x06 电机控制命令~~ **已废弃**：电机改 RK3568 直连 STM32 串口本地控制。

## 目录结构

```
TOF3.0/
├── nezha/            哪吒 NUC 侧代码
│   ├── acquisition/  C++ 采集（sim_pf32, ExampleTOF, depth_proto.h）
│   ├── qt_app/       Qt 主程序（tof_viewer，含待写 SpiSyncer）
│   ├── spi_syncer/   实时深度帧推送 /dev/spidev1.0
│   └── autostart/    systemd 服务（tof-acquisition, tof-spi-syncer）
├── rk3568/           RK3568 侧工程
│   ├── legacy/       v1.0 遗留代码（电机、SPI slave、Qt 显示参考）
│   ├── spi_receiver/ SPI slave 收二进制深度帧
│   ├── qt_display/   Qt MIPI 屏实时深度图显示
│   ├── cloud_syncer/ 5G 上传（已实现+e2e；归暂缓阶段，保留不动）
│   ├── motor_controller/ 串口→STM32 电机（待实现，节点已定 /dev/ttyS4）
│   └── autostart/    BusyBox init.d（S95/S96）
├── research/         算法研究（本机运行，不部署到哪吒/RK）
│   ├── algorithms/   传统算法（argmax、spatial_argmax 等）
│   ├── eval/         评估指标 + 可视化
│   ├── tests/        单元测试
│   ├── ml_offline/   离线训练 + ONNX 导出（边缘推理路线）
│   ├── datasets/     Gutierrez SimSPADDataset（.gitignore，本地缓存）
│   └── out/          可视化输出（.gitignore）
├── cloud/            本地开发用 FastAPI（server/；5G 上云暂缓）
│   └── server/       FastAPI 服务（main.py, models.py）
├── deploy/           部署脚本（paramiko SFTP）
├── refs/             参考文档（PF32 手册、RK3568 文档、USB转SPI 资料）
└── docs/             设计文档、算法、连接/SPI 硬件说明
```

## 关键设计约定

- `depth_proto.h`：TofFrame (2070B)，与 TOF 1.0 协议兼容
- PF32 **反向 start-stop**：`distance = (1023 - bin) × 55ps × c/2`
- PF32 跑 **TCSPC laser_master**（2026-06-03 切换，sys_master TRIG 输出硬件故障无信号）：信号发生器同时驱动激光 P3（外触发）和 PF32 SYNC SMA（+3.3V peak，50Ω），PF32 以 SYNC 作为 TDC 时序参考；`refs/pf32/docs/SyncInput_3300mV.pdf` 是本项目 SYNC 接线规范
- 哪吒**生产无网络**；深度图实时显示在 **RK3568 MIPI 屏**（哪吒 HDMI 仅开发可选）
- 深度帧走 **SPI 实时流**；原始 TCSPC 只哪吒本地存档；**5G 上云暂缓**
- SPI 传输失败不阻塞采集，数据继续本地积累
- 激光控制 **留在哪吒**（FeedbackController 实时闭环，不过 SPI）。激光工作在**信号发生器外触发模式**（信号发生器 → 激光 P3 + PF32 SYNC）：重复频率由信号发生器决定，激光 `setFreqHz` 在外触发下无效，闭环只调电平/功率
- 电机控制 **在 RK3568，板内 STM32 + TMC2209**（改版底板焊死）；UART4/`ttyS4` 是 STM32 ↔ RK3568 通道（JP2 跳线短接 3-5/4-6）。哪吒 `motoruart` 为过渡实现，最终迁出
- SPI 接收走 **USB转SPI 适配器**（非 RK3568 原生 SPI）

## 开发阶段

| 阶段 | 状态 | 说明 |
|------|------|------|
| P1–P6, P5a/b/c | ✅ | 哪吒侧已验证；P5b/c（哪吒 CloudSyncer/FastAPI）仅本地开发用 |
| P7 真实 PF32 | ⬜ | ExampleTOF 联调；raw .tch 落盘 |
| **P-RT 实时显示链路** | ⬜ | **本阶段核心**：哪吒 SpiSyncer + RK3568 spi_receiver + Qt MIPI 显示 |
| P8 调焦标定 | ⬜ | 需 RK3568 电机接线 |
| P9 算法管道 | ⬜ | 物理基线 + 雾/目标分离 |
| P-5G 上云 | ⬜ | **暂缓**，日后稳定再加（cloud_syncer 已就绪） |
| P10–P13 | ⬜ | ML 训练/推理/闭环/主动调制分离 |

## PDF 阅读规范

读取任何 PDF 后，必须在**同一目录**下建立两个文件（已存在则更新）：

1. **同名 `.md`**（如 `foo.pdf` → `foo.md`）：提取本项目关心的关键信息，含 PDF 总体介绍。
2. **目录级 `README.md`**：每个 PDF 一行简介，作为索引。

下次需要查阅该 PDF 内容时，**优先读 `.md` 文件**，找不到或信息不足再读原 PDF。

`.md` 文件内容格式（无需读取日期）：
```
# <PDF 文件名>

> <一句话说明这是什么文档>

## 关键信息

（本项目关心的信息，按主题分节提取，不转录全文）
```

## 注意事项

- `dialout` 组：访问串口需在 dialout 组
- TCSPC 原始约 2MB/帧（2fps≈14GB/h），只哪吒本地存；瓶颈是哪吒→RK SPI ~50–140KB/s
- 两机访问与串口踩坑（CH340 慢写）：`docs/登录方式.md`、`docs/spi硬件接口.md`、`docs/rk3568_connection.md`
- RK3568 侧框架（权威）：`docs/rk3568_framework.md`
- 详细算法思路：`docs/active_modulation_separation_algorithm.md`
- 早期思考（部分被推翻，留档）：`docs/rk3568_reintegration_architecture.md`
- 完整架构：`ARCHITECTURE.md`
