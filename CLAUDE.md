# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

TOF 单光子 3.0：双机协作架构。
- **哪吒 NUC**（Intel N97）：采集、算法处理、本地存储、Qt 显示、激光控制
- **RK3568**：5G 上行网关、电机控制、SPI 接收转发数据

## 硬件环境

| 设备 | 规格 | 连接 |
|------|------|------|
| 哪吒 NUC | Intel N97，4C，7.5GB RAM，Ubuntu 22.04，**无网络** | 主机，SSH: ding/1234 |
| RK3568 | ARM，Ubuntu，**有 5G 模块** | 通过 SPI 与哪吒连接 |
| PF32 探测器 | 32×32 SPAD，TCSPC，55ps/bin | USB（Opal Kelly）→ 哪吒 |
| 激光驱动器 | YSC-SO-M04-4，Modbus RTU 9600 8N1 | USB-UART → 哪吒 /dev/ttyUSB0 |
| STM32F103 | 调焦电机控制，TMC2209 | → RK3568 电机驱动引脚（v1.0 代码） |

## SPI 链路（哪吒 ↔ RK3568）

```
哪吒 40pin GPIO → SPI master (spidev0.0)
RK3568 SPI 外设  → SPI slave
额外: INT 引脚（RK3568→哪吒）: 有网+buffer有空间时拉高
```

传输模式：**文件队列异步**，不做实时流。
- 轻量深度帧（2KB）：5s 周期推送
- TCSPC 原始（2MB）：空闲期分块传输（64KB/chunk）

## 构建命令（在哪吒上执行）

```bash
# acquisition
cd ~/TOF3.0/nezha/acquisition
g++ -std=c++17 -O2 -o sim_pf32 sim_pf32.cpp

# qt_app
cd ~/TOF3.0/nezha/qt_app
qmake tof_viewer.pro && make -j4

# 运行
DISPLAY=:1 ./tof_viewer --depth-file /tmp/depth.dat \
  --laser-port /dev/ttyUSB0 \
  --data-dir ~/tof-data \
  --cloud-url http://localhost:8765

# cloud (哪吒本地或服务器)
cd ~/TOF3.0/cloud/server
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8765 &
```

## 核心架构

### 数据流

```
PF32 → nezha/acquisition/ExampleTOF 或 sim_pf32
  → /tmp/depth.dat              (轻量帧，Qt实时读)
  → ~/tof-data/raw_tcspc/      (TCSPC原始，2MB/帧)
  → ~/tof-data/depth_queue/    (轻量帧队列)

哪吒 Qt (nezha/qt_app/tof_viewer)
  → DepthWidget / PointCloudWidget (本地HDMI显示)
  → FeedbackController → LaserUart (激光控制)
  → SpiSyncer (后台线程) → SPI → RK3568

RK3568 (rk3568/spi_receiver + rk3568/cloud_syncer)
  → SpiReceiver → ~/tof-buffer/
  → CloudSyncer → POST 云端 FastAPI (5G)
  → 电机控制 (rk3568/legacy 代码) ← SPI CMD=0x06 来自哪吒
```

### SPI CMD 定义

| CMD | 方向 | 含义 |
|-----|------|------|
| 0x01 | 哪吒→RK | 查询状态（网络/buffer） |
| 0x02 | 哪吒→RK | 发送文件头 |
| 0x03 | 哪吒→RK | 发送文件块 |
| 0x04 | RK→哪吒 | 文件确认 ACK |
| 0x05 | RK→哪吒 | 上传进度上报 |
| 0x06 | 哪吒→RK | 电机控制命令 |

## 目录结构

```
TOF3.0/
├── nezha/            哪吒 NUC 侧代码
│   ├── acquisition/  C++ 采集（sim_pf32, ExampleTOF, depth_proto.h）
│   └── qt_app/       Qt 主程序（tof_viewer）
├── rk3568/           RK3568 侧工程
│   ├── legacy/       v1.0 遗留代码（电机、SPI slave 参考）
│   ├── spi_receiver/ SPI slave 接收（待实现）
│   └── cloud_syncer/ 5G 上传（待实现）
├── cloud/            云端代码
│   ├── server/       FastAPI 服务（main.py, models.py）
│   └── ml/           ML 脚手架（云端GPU训练）
│       ├── data/     数据集工具
│       ├── models/   神经网络（Hist3DNet, DepthUNet）
│       ├── train/    训练脚本
│       ├── export/   ONNX 导出
│       └── infer/    本地推理
├── deploy/           部署脚本（paramiko SFTP）
├── refs/             参考文档（PF32手册、RK3568文档）
└── docs/             设计文档、算法思路、文献
```

## 关键设计约定

- `depth_proto.h`：TofFrame (2070B)，与 TOF 1.0 保持协议兼容
- PF32 **反向 start-stop**：`distance = (1023 - bin) × 55ps × c/2`
- 哪吒 **无网络**，所有云端上传经 SPI→RK3568→5G
- SPI 传输失败不阻塞采集，数据继续本地积累
- 激光控制 **留在哪吒**（FeedbackController 实时闭环）
- 电机控制 **在 RK3568**（有专用引脚，复用 v1.0）

## 开发阶段

| 阶段 | 状态 | 说明 |
|------|------|------|
| P1–P6, P5a/b/c | ✅ | 从 TOF2.0 继承，哪吒已验证 |
| P7 真实 PF32 | ⬜ | ExampleTOF 联调 |
| P8 调焦标定 | ⬜ | 需先完成 RK3568 电机接线 |
| P9 数据管道 | ⬜ | TCSPC 上传端点 + SpiSyncer 实现 |
| P10 ML 训练 | ⬜ | 物理算法先行，ML 待真实数据 |
| P11 本地推理 | ⬜ | ONNX Runtime on 哪吒 |
| P12 闭环优化 | ⬜ | ML 置信度驱动激光/电机 |
| P13 主动调制分离 | ⬜ | 焦距/功率差分区分雾/目标（创新） |

## 注意事项

- `dialout` 组：ding 需在 dialout 组才能访问串口
- TCSPC 原始约 2MB/帧，本地先存，SPI 空闲期批传
- 详细算法思路：`docs/active_modulation_separation_algorithm.md`
- RK3568 接入方案：`docs/rk3568_reintegration_architecture.md`
- RK3568 连接现状（串口 COM7）：`docs/rk3568_connection.md`
- RK3568 当前无网络（无 SIM 卡），串口 1500000 baud 是唯一通道，Buildroot 系统，root 无密码
- 完整架构：`ARCHITECTURE.md`
