# AGENTS.md

给 Codex / 其他 agent 使用的项目工作手册。Claude 负责主控与审查，Codex 负责实现。

---

## 开始工作前必读

**每次启动必须先读：**
1. `docs/agent-work/progress.md` — 最近工作节点、当前任务、已知问题
2. 本文件（项目结构 + 约束）

---

## 项目定位

TOF 单光子 3.0：双机协作架构（已锁定决策见 `ARCHITECTURE.md` / `docs/rk3568_framework.md`）。
- **哪吒 NUC**（Intel N97）：采集、算法、激光闭环、**本地全量存档**（生产无网，当前网线仅调试）
- **RK3568**：**实时 Qt MIPI 屏显深度图** + 电机控制 + SPI slave 收实时深度帧 +（日后）5G 网关
- **云端**：FastAPI + ML（GPU）——**本阶段暂缓接入**
- 本阶段链路：哪吒实时深度(2KB)→SPI→RK3568 Qt MIPI 显示→即弃；原始 TCSPC 只哪吒本地存；5G 上云暂缓

---

## 硬件

| 设备 | 角色 | 连接 |
|------|------|------|
| 哪吒 NUC | 主机，x86_64，192.168.31.127，**生产无网（网线仅调试）** | SSH: ding/1234（paramiko，无 sshpass）|
| RK3568 | aarch64 Buildroot，实时 Qt MIPI 显示+电机+5G | 串口 /dev/ttyUSB0@1500000；USB 接 SPI 适配器 |
| USB转SPI 适配器 | STM32 方案，USB 0483:5740（物理链路实测通） | 哪吒 SPI 引脚 ↔ 适配器，适配器 USB ↔ RK3568 |
| PF32 | 32×32 SPAD，TCSPC 55ps/bin | USB（Opal Kelly）→ 哪吒 |
| 激光驱动 | YSC-SO-M04-4，Modbus RTU 9600 | /dev/ttyUSB0 → 哪吒 |
| STM32F103 | 调焦电机，TMC2209 | → RK3568 串口（19200 8N1，/dev 节点待定 O2）|

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
│       ├── motoruart.{h,cpp}   # 电机（过渡实现，最终迁 RK3568 串口）
│       ├── datarecorder.{h,cpp} # 深度帧本地录制（.tofrec，不含 raw）
│       ├── cloudsyncer.{h,cpp} # 仅本地开发用（POST localhost:8765）
│       ├── （待写）spisyncer   # 实时深度帧 → /dev/spidev1.0（本阶段新写）
│       └── tof_viewer.pro      # QT += core gui widgets serialport opengl network sql
│
├── rk3568/                     # RK3568 侧代码
│   ├── legacy/                 # v1.0 遗留（含 RK3568 Qt 显示参考）
│   ├── spi_receiver/           # SPI slave 收实时深度帧（本阶段新写）
│   ├── （待建）qt_display/      # 深度帧 → MIPI 屏渲染（本阶段新写）
│   ├── motor_controller/       # 串口→STM32（待 O2）
│   └── cloud_syncer/           # 5G 上传（已实现+e2e；⏸️ 暂缓阶段保留不动）
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
[MAGIC:2B 0xABCD][CMD:1B][SEQ:4B LE][LEN:4B LE][PAYLOAD:N][CRC32:4B]
```

| CMD | 方向 | 含义 | 本阶段 |
|-----|------|------|--------|
| 0x10 | 哪吒→RK | DEPTH_FRAME：实时深度帧（PAYLOAD=TofFrame 2070B） | ✅ 核心 |
| 0x01 | 哪吒→RK | QUERY_STATUS | ⏸️ 暂缓（5G 阶段） |
| 0x02 | 哪吒→RK | FILE_SEND：文件头 | ⏸️ 暂缓 |
| 0x03 | 哪吒→RK | FILE_CHUNK：文件块 | ⏸️ 暂缓 |
| 0x04 | RK→哪吒 | FILE_ACK | ⏸️ 暂缓 |
| 0x05 | RK→哪吒 | UPLOAD_STATUS | ⏸️ 暂缓 |

> ~~0x06 MOTOR_CMD~~ **已废弃**：电机 RK3568 本地串口直控，不经 SPI。
> 实时深度流不补传、不 ACK（丢帧只影响一帧画面）；0x01–0x05 文件队列属暂缓的 5G 批量上传。

---

## 开发阶段状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| P1 采集验证 | ✅ | sim_pf32 在哪吒运行 |
| P2 Qt 骨架 | ✅ | 编译并在哪吒 HDMI 运行（开发可选；生产显示在 RK3568 MIPI）|
| P3 2D 显示 | ✅ | jet 色图热图 |
| P4 3D 点云 | ✅ | OpenGL，鼠标旋转/缩放 |
| P6 串口外设 | ✅ | 激光 + 反馈控制 |
| P5a 本地录制 | ✅ | DataRecorder，.tof 文件 |
| P5b 离线上传 | ✅ | CloudSyncer，SQLite 队列 |
| P5c 云端平台 | ✅ | FastAPI + SQLite |
| P7 真实 PF32 | ⬜ | 等待硬件 + PF32 SDK；raw .tch 落盘由它产出 |
| **P-RT 实时显示链路** | ⬜ | **本阶段核心**：哪吒 SpiSyncer + RK3568 spi_receiver + Qt MIPI 显示 |
| P8 调焦标定 | ⬜ | 电机步数→焦距映射，需 RK3568 接线（O2）|
| P9 算法管道 | ⬜ | 物理基线 + 雾/目标分离 |
| P-5G 上云 | ⏸️ | **暂缓**：net_manager + cloud_syncer 接真实云 + 哪吒批量上行 |
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
- 电机控制 **RK3568 本地直连 STM32 串口**（19200 8N1），不经 SPI、哪吒不直接驱动
- 深度帧走 SPI 实时流（CMD 0x10）；原始 TCSPC 只哪吒本地存；5G 上云暂缓
- 不读取 .env、私钥、token 等凭据文件
