# AGENTS.md

给 Codex / 其他 agent 使用的项目工作手册。Claude 负责主控与审查，Codex 负责实现。

---

## 开始工作前必读

**每次启动必须先读：**
1. `docs/agent-work/progress.md` — 最近工作节点、当前任务、已知问题
2. 本文件（项目结构 + 约束）

---

## 项目定位

TOF 单光子 3.0：双机协作架构。
- **哪吒 NUC**（Intel N97）：采集、算法、本地存储、Qt 显示、激光控制（无网络）
- **RK3568**：5G 上行网关、电机控制、SPI slave 接收
- **云端**：FastAPI 数据存储 + ML 训练（GPU）

---

## 硬件

| 设备 | 角色 | 连接 |
|------|------|------|
| 哪吒 NUC | 主机，Ubuntu 22.04，192.168.31.79，**无网络** | SSH: ding/1234 |
| RK3568 | 5G 网关 + 电机控制，Ubuntu，**有 5G** | SPI slave |
| PF32 | 32×32 SPAD，TCSPC 55ps/bin | USB（Opal Kelly）→ 哪吒 |
| 激光驱动 | YSC-SO-M04-4，Modbus RTU 9600 | /dev/ttyUSB0 → 哪吒 |
| STM32F103 | 调焦电机，TMC2209 | → RK3568 电机驱动引脚 |

---

## 项目结构

```
TOF3.0/
├── nezha/                      # 哪吒 NUC 侧代码
│   ├── acquisition/            # C++ 采集层
│   │   ├── sim_pf32.cpp        # 帧模拟器（P1 ✅）
│   │   ├── ExampleTOF.cpp      # 真实 PF32（P7 ⬜，需 SDK）
│   │   ├── depth_proto.h       # TofFrame 协议（2070B）
│   │   └── peak_detect.h       # 峰值检测算法（待 ML 替换）
│   │
│   └── qt_app/                 # Qt5 主程序
│       ├── mainwindow.{h,cpp}  # 主窗口
│       ├── depthparser.{h,cpp} # 解析 /tmp/depth.dat
│       ├── depthwidget.{h,cpp} # 2D 热图
│       ├── pointcloudwidget.{h,cpp} # 3D OpenGL 点云
│       ├── feedbackcontroller.{h,cpp} # 激光/电机反馈控制
│       ├── laseruart.{h,cpp}   # Modbus RTU
│       ├── motoruart.{h,cpp}   # 电机（待改为 SPI CMD=0x06）
│       ├── datarecorder.{h,cpp} # 本地 .tof 录制
│       ├── cloudsyncer.{h,cpp} # SQLite 队列 + SPI 推送
│       └── tof_viewer.pro      # QT += core gui widgets serialport opengl network sql
│
├── rk3568/                     # RK3568 侧代码
│   ├── legacy/                 # v1.0 遗留代码（参考用）
│   ├── spi_receiver/           # SPI slave 接收（P9 ⬜）
│   └── cloud_syncer/           # 5G 上传（P9 ⬜）
│
├── cloud/                      # 云端代码
│   ├── server/                 # FastAPI 平台
│   │   ├── main.py             # 接口实现（✅）
│   │   └── models.py           # aiosqlite 表结构
│   └── ml/                     # 深度学习（P10-P11）
│       ├── data/               # 数据集工具（tof_dataset.py）
│       ├── models/             # 模型定义（Hist3DNet, DepthUNet）
│       ├── train/              # 训练脚本
│       ├── export/             # ONNX 导出
│       └── infer/              # 本地推理
│
├── deploy/                     # 部署脚本（Python paramiko）
│   ├── upload_qt.py            # 上传 nezha/qt_app 源码
│   ├── build_qt.py             # 在哪吒远程编译
│   ├── restart_all.py          # 重启所有服务
│   └── status.py               # 检查进程状态
│
├── refs/                       # 参考文档（PF32 手册、RK3568 文档）
├── docs/
│   ├── agent-work/
│   │   └── progress.md         # ← 必读，工作进度
│   └── 文献/                   # 27 篇参考论文（.md 格式）
│
├── ARCHITECTURE.md             # 完整架构设计
├── CLAUDE.md                   # Claude 工作指南
└── AGENTS.md                   # 本文件
```

---

## 构建与部署

### Qt 应用（在哪吒上编译）

```bash
cd ~/TOF3.0/nezha/qt_app
qmake tof_viewer.pro && make -j4
```

依赖：`libqt5serialport5-dev libqt5opengl5-dev libqt5sql5-dev`

### 运行全套服务

```bash
# 1. FastAPI 服务（必须从 cloud/server/ 目录启动）
cd ~/TOF3.0/cloud/server
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8765 > /tmp/fastapi.log 2>&1 &

# 2. 采集模拟器
nohup ~/TOF3.0/nezha/acquisition/sim_pf32 > /tmp/sim_pf32.log 2>&1 &

# 3. Qt 主程序
DISPLAY=:1 nohup ~/TOF3.0/nezha/qt_app/tof_viewer \
  --depth-file /tmp/depth.dat \
  --data-dir ~/tof-data/depth_queue \
  --cloud-url http://localhost:8765 \
  > /tmp/tof_viewer.log 2>&1 &
```

### 部署更新到哪吒

```bash
# 上传 nezha/qt_app 并重新编译
python deploy/upload_qt.py
python deploy/build_qt.py

# 检查服务状态
python deploy/status.py
```

---

## 数据格式

### .tof 文件（本地录制）

```
Header:  8B  magic "TOFREC1\0"
每帧:   2062B
  seq        uint32 LE   4B
  ts_ms      uint64 LE   8B
  validCount uint16 LE   2B
  depths[1024] uint16 LE  2048B
```

### TofFrame（/tmp/depth.dat 共享内存协议）

```
magic     4B  0x50464F54
version   2B  0x0001
seq       4B
timestamp 8B  Unix ms
rows/cols 2B each  (32×32)
validCount 2B
depths    2048B  uint16[1024]
crc16     2B
总计:     2070B
```

### TCSPC 原始直方图（.tch 文件，P9 实现）

```
magic           8B  "TCHIST1\0"
seq             4B LE
width/height    2B LE  (32)
bins            2B LE  (1024)
sampleBytes     2B LE  (2)
payloadBytes    8B LE  (2097152)
payload         uint16[32×32×1024] = 2MB
```

**注意：PF32 反向 start-stop**：`distance = (1023 - bin_index) × 55ps × c/2`
- 雾峰在高 bin 端（接近 1023），目标峰在低 bin 端（接近 0）

### SPI 帧格式（哪吒 ↔ RK3568）

```
[MAGIC:2B 0xABCD][CMD:1B][SEQ:4B][LEN:4B][PAYLOAD:N][CRC32:4B]
```

| CMD | 方向 | 含义 |
|-----|------|------|
| 0x01 | 哪吒→RK | QUERY_STATUS：查询网络/buffer 状态 |
| 0x02 | 哪吒→RK | FILE_SEND：发送文件头 |
| 0x03 | 哪吒→RK | FILE_CHUNK：发送文件块（64KB/chunk） |
| 0x04 | RK→哪吒 | FILE_ACK：确认收到完整文件 |
| 0x05 | RK→哪吒 | UPLOAD_STATUS：5G 上传进度上报 |
| 0x06 | 哪吒→RK | MOTOR_CMD：电机步数/方向 |

---

## 开发阶段状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| P1 采集验证 | ✅ | sim_pf32 在哪吒运行 |
| P2 Qt 骨架 | ✅ | 编译并在哪吒 HDMI 运行 |
| P3 2D 显示 | ✅ | jet 色图热图 |
| P4 3D 点云 | ✅ | OpenGL，鼠标旋转/缩放 |
| P6 串口外设 | ✅ | 激光 + 反馈控制 |
| P5a 本地录制 | ✅ | DataRecorder，.tof 文件 |
| P5b 离线上传 | ✅ | CloudSyncer，SQLite 队列 |
| P5c 云端平台 | ✅ | FastAPI + SQLite |
| P7 真实 PF32 | ⬜ | 等待硬件 + PF32 SDK |
| P8 调焦标定 | ⬜ | 电机步数→焦距映射，需 RK3568 接线 |
| P9 数据管道 | ⬜ | TCSPC 端点 + SpiSyncer + RK3568 工程 |
| P10 ML 训练 | ⬜ | 3D CNN on TCSPC，云端 GPU |
| P11 本地推理 | ⬜ | ONNX Runtime 部署到哪吒 |
| P12 闭环优化 | ⬜ | ML 置信度驱动反馈控制 |
| P13 主动调制分离 | ⬜ | 焦距/功率差分区分雾/目标（需 P8） |

---

## 编码约束

- C++ 标准：C++17，Qt5，GLSL 1.x（Mesa 兼容）
- Python：3.10+（哪吒系统 Python）
- 不硬编码串口设备名、IP、端口，全部通过命令行参数传入
- 串口访问需 dialout 组：`sudo usermod -aG dialout ding`
- Qt 主线程只做渲染和串口控制，不做阻塞 IO
- CloudSyncer / SpiSyncer 失败不得阻塞采集和显示
- 修改 `depth_proto.h` 前先确认与 nezha/acquisition 层同步
- SPI 传输失败时数据继续本地存储，不阻塞采集主线程
- 电机控制经 SPI CMD=0x06 发给 RK3568，哪吒不直接驱动电机
- 不读取 .env、私钥、token 等凭据文件
