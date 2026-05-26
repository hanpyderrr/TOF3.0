# TOF 单光子 3.0 架构文档

> 版本：2026-05-19（按已锁定决策重写）
> 决策：双机协作——哪吒负责采集/算法/本地全量存档，RK3568 负责**实时 Qt MIPI 深度显示** + 电机控制 +（日后）5G 上行
>
> ✅ 已锁定（2026-05-19）：
> ① **RK3568 屏幕实时 Qt MIPI 显示深度图**（硬需求；v1.0 单光子已在 RK3568 跑过 Qt 显示）；
> ② 深度帧（2KB）走 **SPI 实时流**；原始 TCSPC（2MB）只在**哪吒本地存档**；
> ③ **RK3568 经 5G 上云（raw+depth）本阶段暂缓**，日后稳定再加；
> ④ SPI 接收走 **USB转SPI 适配器**（非 RK3568 原生 SPI），物理链路已实测可用；
> ⑤ 电机 **RK3568 直连 STM32 串口**（非经 SPI CMD=0x06）。
>
> 本文与 `docs/rk3568_framework.md` 一致；早期 `docs/rk3568_reintegration_architecture.md` 仅留档。

---

## 一、架构演进背景

| 版本 | 架构 | 问题 / 结论 |
|------|------|------|
| TOF 1.0 | 哪吒采集 → SPI → RK3568 处理/显示 | 把 **2MB TCSPC 原始**实时流推过 SPI，4MB/s 超 SPI 带宽，不稳定 |
| TOF 2.0 | 全部集中到哪吒 | 哪吒生产无网络，数据上不了云端 |
| **TOF 3.0** | **哪吒算法主机 + RK3568 实时显示/电机/(日后)5G 网关** | 只把 **2KB 深度帧**走 SPI 实时流（带宽富余）；2MB 原始不过 SPI，只哪吒本地存 |

> 关键纠正：当年 SPI 坏在 **2MB 原始实时流**，不是 SPI 本身。2KB 深度帧实时流（30fps 也仅 60KB/s）远在 SPI(~50–140KB/s) 与显示需求之内，可行。

---

## 二、硬件拓扑

```
PF32 探测器（32×32 SPAD，TCSPC，sys_master）
    │ USB（Opal Kelly FPGA）→ 哪吒
    │ TRIG 输出（TTL）→ 激光器外触发；PF32 内部 EXTSTOP 做 stop（反向 start-stop）
激光驱动器（YSC-SO-M04-4，Modbus RTU；PF32 外触发，频率随 PF32 TRIG）
    │ USB-UART → 哪吒 /dev/ttyUSB0
    │
哪吒 NUC（Intel N97，x86_64，Ubuntu；生产环境无网络）
    │ /dev/spidev1.0 → SPI master（MODE0，1.125MHz）原生引脚
    ▼
USB转SPI 适配器模块（STM32，USB ID 0483:5740）
    │ USB
RK3568（aarch64，Buildroot，内核 4.19，有 Qt + MIPI 屏，有 5G）
    │ 适配器做 SPI slave（libUSB2UARTSPIIIC）
    ├── Qt MIPI 屏 → 实时显示深度图
    ├── 串口 → STM32F103 → TMC2209 → 镜头电机（19200 8N1，本地直控）
    └── 5G Quectel RM500U-CNV → 公网云平台【本阶段暂缓】
```

- 物理链路（哪吒原生 SPI 引脚 → 适配器 → RK3568）**今日已实测逐字节通**，硬件不动。
- 哪吒**生产环境无网络**；当前接的网线/局域网仅为开发调试。
- 哪吒本地有显示器（HDMI）可选用于开发；**生产态深度图主显示在 RK3568 MIPI 屏**。

---

## 三、软件模块

```
nezha/（哪吒 NUC — 采集 + 算法 + 本地全量存档）
├── acquisition/（数据采集层，C/C++）
│   ├── sim_pf32         模拟器，写 /tmp/depth.dat（仅深度，无 raw）
│   ├── ExampleTOF       真实 PF32（待 P7）；raw .tch 落盘由它产出
│   └── depth_proto.h    TofFrame 协议结构体（2070B）
│
└── qt_app/（Qt 应用 — tof_viewer）
    ├── DepthParser      读 /tmp/depth.dat，CRC 校验
    ├── DepthWidget      2D 伪彩深度图（哪吒本地可选显示）
    ├── PointCloudWidget 3D 点云（OpenGL，本地可选）
    ├── FeedbackController 实时反馈控制（每 10 帧）→ LaserUart（激光闭环，不过 SPI）
    ├── DataRecorder     深度帧本地存档（.tofrec）—— 注意：不含 raw TCSPC
    ├── SpiSyncer        【本阶段新写】实时深度帧 → /dev/spidev1.0（低延迟流）
    └── cloudsyncer      仅本地开发用（POST localhost:8765）；生产不走此路

rk3568/（RK3568 — 实时显示 + 电机 +（日后）5G 网关）
├── legacy/              v1.0 遗留代码（电机 / SPI / Qt 显示参考，只读）
├── spi_receiver/        【本阶段新写】SPI slave 收二进制深度帧
├── （新）Qt 显示程序     【本阶段新写】深度帧 → MIPI 屏实时渲染 → 即弃
├── motor_controller/    串口 → STM32 → 镜头电机（待实现）
├── cloud_syncer/        5G 上传（已实现+e2e 过）——【归暂缓阶段，保留不动】
└── autostart/           BusyBox init.d 自启动（待实现）

cloud/（本地开发用 FastAPI；本阶段不上云）
└── server/（FastAPI + SQLite）跑哪吒 localhost:8765；仅本地开发

ml_offline/（离线训练 + ONNX 导出；原 cloud/ml，边缘推理路线）
├── schema/         session/frame 元数据 JSON Schema
├── data/           raw_dump / meta / labels（本地不入仓）
├── train/ export/ infer/ eval/ tests/
└── models/         Hist3DNet / DepthUNet
```

---

## 四、数据分层

### 数据量

| 数据类型 | 大小/帧 | 2fps 速率 | 走向 |
|----------|---------|----------|------|
| 轻量深度帧 TofFrame | 2070 B | ~4 KB/s | **SPI 实时流 → RK3568 显示** + 哪吒本地存档 |
| TCSPC 原始 .tch | 2 MB | ~4 MB/s（≈14GB/h） | **只哪吒本地存档**（不过 SPI/5G） |

### 三层数据策略（本阶段）

```
实时控制层（哪吒主线程，<100ms）
    DepthParser → FeedbackController → LaserUart   不存储，激光实时闭环

实时显示层（哪吒 → RK3568，本阶段核心）
    哪吒 SpiSyncer 低延迟推 TofFrame(2KB) → /dev/spidev1.0
      → 适配器 → RK3568 spi_receiver → Qt MIPI 屏渲染 → 即弃（RK 不落盘）

本地存档层（哪吒磁盘，全量，不上传）
    深度  → ~/tof-data/depth_queue/   (DataRecorder)
    TCSPC → ~/tof-data/raw_tcspc/     (采集层产出，待 P7 真实 PF32)

云端研究层【本阶段暂缓】
    日后 RK3568 经 5G 批量上传 raw+depth → 公网云平台
    现有 rk3568/cloud_syncer（离线 e2e 过）保留，将来直接接 5G
```

> 带宽现实：原始 14GB/h，受哪吒→RK SPI ≈50–140KB/s 卡死，全量自动上云物理不可行 → raw 本阶段只哪吒本地，日后人工/选择性再议。

---

## 五、SPI 协议

### 物理层（已实测可用）

```
哪吒：/dev/spidev1.0，SPI master，MODE0，1.125MHz，需 root（sudo）
介质：USB转SPI 适配器模块（USB ID 0483:5740，插 RK3568 USB 口）
RK3568：适配器做 SPI slave（libUSB2UARTSPIIIC，SPI_SubMode_0 / SPI_MSB）
```

### 帧格式（本阶段：实时深度二进制帧）

```
[MAGIC:2B 0xABCD] [CMD:1B] [SEQ:4B LE] [LEN:4B LE] [PAYLOAD:N] [CRC32:4B]
PAYLOAD = TofFrame(2070B)
```

- 旧版文本协议（首行 `Frame=0` + 1024 空格数）仅 v1.0 用，**不复用**；新链路走上面的二进制帧。
- 实时流时序细节（是否用适配器 INT 中断线、回包时序）见 `docs/rk3568_framework.md` §6 开放项。

### CMD 列表

| CMD | 方向 | 含义 | 本阶段 |
|-----|------|------|--------|
| 0x10 | 哪吒→RK | DEPTH_FRAME：实时深度帧（PAYLOAD=TofFrame 2070B） | ✅ 本阶段核心 |
| 0x01 | 哪吒→RK | QUERY_STATUS | 暂缓（5G 阶段） |
| 0x02 | 哪吒→RK | FILE_SEND（文件头） | 暂缓 |
| 0x03 | 哪吒→RK | FILE_CHUNK（文件块） | 暂缓 |
| 0x04 | RK→哪吒 | FILE_ACK | 暂缓 |
| 0x05 | RK→哪吒 | UPLOAD_STATUS | 暂缓 |

> ~~0x06 MOTOR_CMD~~ 已废弃：电机 RK3568 本地串口直控。0x01–0x05 文件队列协议属暂缓的 5G 批量上传阶段，本阶段只用 0x10 实时深度帧。

---

## 六、关键数据格式

### 轻量深度帧（TofFrame / depth_proto.h）

```
magic      4B   0x50464F54 ("TOFP")
version    2B   0x0001
seq        4B
timestamp  8B   Unix ms
rows/cols  2B   32
validCount 2B
depths     2048B  uint16[1024]，0=无效
crc16      2B
```
（合计 2070B；本地存档容器 DataRecorder 头 `TOFREC1\0`）

### TCSPC 原始直方图（.tch，仅哪吒本地）

```
magic        8B   "TCHIST1\0"
seq          4B LE
width/height 2B LE  32
bins         2B LE  1024
sampleBytes  2B LE  2
payloadBytes 8B LE  2097152
payload      uint16[32×32×1024]
```

**PF32 反向 start-stop：** `distance = (1023 - bin_index) × 55ps × c/2`

---

## 七、实时反馈控制

> **同步前提**：激光工作在 PF32 外触发模式（PF32 sys_master 出 TRIG → 激光 P3）。重复频率由 PF32 TRIG 决定，闭环**只调电平/功率，不调频率**（laser `setFreqHz` 在外触发下被驱动拒绝）。

FeedbackController 每 10 帧评估（哪吒主线程，本地闭环，不过 SPI）：

### 激光强度控制

```
ratio = validCount / 1024
ratio < 0.50 → level += 5
ratio > 0.95 → level -= 5
level 范围：[10, 150]，步长 5
```

### 电机焦距控制（P8 后）

电机在 RK3568 直连 STM32 串口本地控制，与哪吒反馈闭环解耦（开放项 O1，见 `docs/rk3568_framework.md` §6）。

---

## 八、透雾成像算法路径（P9–P13）

### 阶段一：物理基线（优先，无需数据）

```
背景估计 → 背景减除 → CFAR 峰检测 → Gaussian 亚 bin 拟合 → 深度图 + 置信度图
```

### 阶段二：雾/目标分离（EM 方法）

```
lognormal 雾散射峰 + Gaussian 目标峰 + EM 拟合
→ 升级：Gamma + DBSCAN 残差聚类（火箭军 2025 方法）
```

### 阶段三：主动调制分离（创新，P13）

**A. 焦距扫描差分**：雾体散射对焦距不敏感，目标随焦距信号显著变化；测两焦距 H₁,H₂ 解出 H_fog,H_tgt。
**B. 激光功率差分（pile-up）**：高功率对早期 bin（雾峰）压制更强，比较高低功率直方图差异。需标定 pile-up 模型（P7 后）。

详见 `docs/active_modulation_separation_algorithm.md`。

### 阶段四：ML 增强（P10–P12）

物理算法输出作 ML 训练标签；3D CNN 处理极端雾天 EM 失效场景；ONNX Runtime 部署哪吒（CPU 推理 <50ms/帧）。

---

## 九、实施阶段

| 阶段 | 目标 | 状态 |
|------|------|------|
| P1–P4, P6, P5a | 采集/Qt/2D/3D/激光闭环/本地录制（哪吒侧） | ✅ |
| P5b/P5c | 哪吒 CloudSyncer + 云端 FastAPI（仅本地开发用） | ✅ |
| **P7 真实 PF32** | ExampleTOF 联调；raw .tch 落盘 | ⬜ 等待硬件 |
| **P-RT 实时显示链路** | 哪吒 SpiSyncer（实时深度）+ RK3568 spi_receiver + Qt MIPI 显示 | ⬜ **本阶段核心** |
| P8 调焦标定 | 电机步数→焦距表（需 RK3568 接线） | ⬜ |
| P9 算法管道 | 物理基线 + 雾/目标分离 | ⬜ |
| **P-5G 上云**（暂缓） | RK3568 5G + cloud_syncer 接真实云 + net_manager + 自启动 | ⬜ 日后稳定再加 |
| P10–P13 | ML 训练 / 本地推理 / 闭环优化 / 主动调制分离 | ⬜ 待数据 |

---

## 十、命令行参数

```bash
# 哪吒上运行（nezha/qt_app/tof_viewer）
DISPLAY=:1 ./tof_viewer \
  --depth-file  /tmp/depth.dat \
  --laser-port  /dev/ttyUSB0 \
  --data-dir    ~/tof-data \
  --cloud-url   http://localhost:8765   # 仅本地开发；生产不走哪吒上云
```

RK3568 侧实时显示程序、SpiSyncer 参数待这两块实现时补（见 `docs/rk3568_framework.md`）。
