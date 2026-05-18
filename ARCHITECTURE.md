# TOF 单光子 3.0 架构文档

> 版本：2026-05-18
> 决策：双机协作——哪吒负责采集与算法，RK3568 负责 5G 上行与电机控制

---

## 一、架构演进背景

| 版本 | 架构 | 问题 |
|------|------|------|
| TOF 1.0 | 哪吒采集 → SPI → RK3568 处理/显示 | SPI 实时流不稳定，ARM 交叉编译复杂 |
| TOF 2.0 | 全部集中到哪吒 | 哪吒无网络，数据上不了云端 |
| **TOF 3.0** | **哪吒算法主机 + RK3568 5G 网关** | SPI 改为文件队列异步，各司其职 |

---

## 二、硬件拓扑

```
PF32 探测器（32×32 SPAD，TCSPC）
    │ USB（Opal Kelly FPGA）
    │
激光驱动器（YSC-SO-M04-4，Modbus RTU）
    │ USB-UART → /dev/ttyUSB0
    │
哪吒 NUC（Intel N97，Ubuntu 22.04，无网络）
    │ 40pin GPIO → SPI master (spidev0.0)
    │ INT 引脚（输入，RK3568→哪吒）
    │
RK3568（ARM，Ubuntu，5G 模块）
    │ SPI slave
    │ 电机驱动引脚 → STM32F103 → TMC2209 → 镜头
    │ 5G 上行 → 云端
    │
哪吒 HDMI → 本地显示器
```

---

## 三、软件模块

```
nezha/（哪吒 NUC — 采集 + 算法主机）
├── acquisition/（数据采集层，C/C++）
│   ├── sim_pf32         模拟器，写 /tmp/depth.dat
│   ├── ExampleTOF       真实 PF32（待 P7）
│   └── depth_proto.h    TofFrame 协议结构体
│
└── qt_app/（Qt 应用 — tof_viewer）
    ├── DepthParser      读 /tmp/depth.dat，CRC 校验
    ├── DepthWidget      2D 伪彩深度图
    ├── PointCloudWidget 3D 点云（OpenGL）
    ├── FeedbackController 实时反馈控制（每 10 帧）
    │   └── LaserUart    Modbus RTU → 激光强度
    ├── DataRecorder     本地数据落盘
    └── SpiSyncer        SPI master，异步推送数据给 RK3568（待 P9）

rk3568/（RK3568 — 5G 网关 + 电机控制）
├── legacy/              v1.0 遗留代码（电机驱动 / SPI 参考）
├── spi_receiver/        SPI slave，接收哪吒推来的文件（待实现）
├── cloud_syncer/        HTTP POST 到云端 FastAPI（5G 上传，待实现）
├── MotorController      驱动 STM32 → 调焦电机
└── 本地缓冲 ~/tof-buffer/

cloud/（云端）
├── server/（FastAPI + SQLite）
│   ├── GET  /api/health
│   ├── POST /api/frames/depth
│   ├── POST /api/frames/tcspc   （P9 新增）
│   ├── GET  /api/sessions
│   └── GET  /api/sessions/{id}/frames
└── ml/（ML 脚手架，云端 GPU 训练）
    ├── data/     数据集工具（tof_dataset.py）
    ├── models/   神经网络（Hist3DNet, DepthUNet）
    ├── train/    训练脚本
    ├── export/   ONNX 导出
    └── infer/    本地推理（ONNX Runtime）
```

---

## 四、数据分层

### 数据量估算

| 数据类型 | 大小/帧 | 2fps 时速率 |
|----------|---------|------------|
| 轻量深度帧 | 2070 B | ~4 KB/s |
| TCSPC 原始直方图 | 2 MB | ~4 MB/s |

### 三层数据策略

```
实时控制层（哪吒主线程，< 100ms）
    DepthParser → FeedbackController → LaserUart
    不存储，仅用于激光实时调整

本地存储层（哪吒磁盘，离线优先）
    深度帧  → ~/tof-data/depth_queue/
    TCSPC   → ~/tof-data/raw_tcspc/
    上传状态 → ~/tof-data/upload_state.sqlite

SPI 传输层（哪吒→RK3568，异步）
    深度帧：5s 周期推送，< 10KB/s
    TCSPC：空闲期分块，64KB/chunk，不阻塞采集

云端研究层（RK3568 通过 5G 上传）
    轻量帧：近实时
    TCSPC：批量补传（5G 上行约 5Mbps，7 倍延迟）
```

---

## 五、SPI 协议

### 物理层

```
哪吒：spidev0.0（40pin GPIO 扩展接口）
RK3568：SPI slave 外设
时钟：1~4 MHz（保守稳定）
信号：MOSI / MISO / SCLK / CS / INT
INT：RK3568→哪吒，有网+buffer有空间时拉高
```

### 帧格式

```
[MAGIC:2B 0xABCD] [CMD:1B] [SEQ:4B] [LEN:4B] [PAYLOAD:N] [CRC32:4B]
```

### CMD 列表

| CMD | 方向 | 含义 |
|-----|------|------|
| 0x01 | 哪吒→RK | QUERY_STATUS：查询网络状态和 buffer 剩余 |
| 0x02 | 哪吒→RK | FILE_SEND：发送文件头（filename, total_size） |
| 0x03 | 哪吒→RK | FILE_CHUNK：发送文件块 |
| 0x04 | RK→哪吒 | FILE_ACK：确认收到完整文件 |
| 0x05 | RK→哪吒 | UPLOAD_STATUS：上传进度上报 |
| 0x06 | 哪吒→RK | MOTOR_CMD：电机步数/方向 |

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

### TCSPC 原始直方图（.tch）

```
magic        8B   "TCHIST1\0"
seq          4B LE
width/height 2B LE  32
bins         2B LE  1024
sampleBytes  2B LE  2
payloadBytes 8B LE  2097152
payload      uint16[32×32×1024]
```

**注意：PF32 反向 start-stop：** `distance = (1023 - bin_index) × 55ps × c/2`

---

## 七、实时反馈控制

FeedbackController 每 10 帧评估（哪吒主线程）：

### 激光强度控制

```
ratio = validCount / 1024
ratio < 0.50 → level += 5
ratio > 0.95 → level -= 5
level 范围：[10, 150]，步长 5
```

### 电机焦距控制（P8 后）

命令经 SPI CMD=0x06 发给 RK3568，再驱动 STM32。
评估指标：平均深度变化 > 300mm 时触发。

---

## 八、透雾成像算法路径（P9–P13）

### 阶段一：物理基线（优先，无需数据）

```
背景估计 → 背景减除 → CFAR 峰检测 → Gaussian 亚 bin 拟合
→ 深度图 + 置信度图
```

### 阶段二：雾/目标分离（EM 方法）

```
lognormal 雾散射峰 + Gaussian 目标峰 + EM 拟合
→ 升级：Gamma + DBSCAN 残差聚类（火箭军 2025 方法）
```

### 阶段三：主动调制分离（创新，P13）

两种差分思路：

**A. 焦距扫描差分**
- 雾：体散射，对焦距不敏感
- 目标：点/面反射，焦距变化时信号强度显著变化
- 测量两个焦距位置 H₁, H₂，联立解出 H_fog, H_tgt

**B. 激光功率差分（利用 pile-up）**
- 高功率时 pile-up 对早期 bin（雾峰）压制更强
- 比较高低功率直方图差异区分雾/目标
- 需标定 pile-up 模型（P7 后）

详细见：`docs/active_modulation_separation_algorithm.md`

### 阶段四：ML 增强（P10–P12）

- 物理算法输出作为 ML 训练标签
- 3D CNN 处理极端雾天 EM 失效场景
- ONNX Runtime 部署到哪吒（CPU 推理，< 50ms/帧）

---

## 九、实施阶段

| 阶段 | 目标 | 状态 |
|------|------|------|
| P1 采集验证 | sim_pf32 + verify PASS | ✅ |
| P2 Qt 骨架 | tof_viewer 编译启动 | ✅ |
| P3 2D 显示 | DepthWidget jet 色图 | ✅ |
| P4 3D 点云 | PointCloudWidget OpenGL | ✅ |
| P6 串口外设 | LaserUart + FeedbackController | ✅ |
| P5a 本地录制 | DataRecorder | ✅ |
| P5b 离线上传 | CloudSyncer | ✅ |
| P5c 云端平台 | FastAPI + SQLite | ✅ |
| P7 真实 PF32 | ExampleTOF 联调 | ⬜ 等待硬件 |
| P8 调焦标定 | 电机步数→焦距表 | ⬜ 需 RK3568 接线 |
| P9 数据管道 | TCSPC 端点 + SpiSyncer + RK3568 工程 | ⬜ 进行中 |
| P10 ML 训练 | 3D CNN on TCSPC | ⬜ 待数据 |
| P11 本地推理 | ONNX Runtime 部署 | ⬜ |
| P12 闭环优化 | ML 置信度驱动反馈 | ⬜ |
| P13 主动调制分离 | 焦距/功率差分算法 | ⬜ 需 P8 标定 |

---

## 十、命令行参数

```bash
# 在哪吒上运行（nezha/qt_app/tof_viewer）
DISPLAY=:1 ./tof_viewer \
  --depth-file  /tmp/depth.dat \
  --laser-port  /dev/ttyUSB0 \
  --data-dir    ~/tof-data \
  --cloud-url   http://localhost:8765
```
