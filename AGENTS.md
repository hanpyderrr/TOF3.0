# AGENTS.md

给 Codex / 其他 agent 使用的项目工作手册。Claude 负责主控与审查，Codex 负责实现。

---

## 开始工作前必读

**每次启动必须先读：**
1. `docs/agent-work/progress.md` — 最近工作节点、当前任务、已知问题
2. 本文件（项目结构 + 约束）

---

## 项目定位

TOF 单光子 2.0：PF32 32×32 SPAD 探测器 + 哪吒 NUC（Intel N97），单机实时成像 + 云端深度研究。
当前主要目标：**透雾成像**，通过深度学习优化 TCSPC 直方图分析，取代简单峰值检测。

---

## 硬件

| 设备 | 角色 | 连接 |
|------|------|------|
| 哪吒 NUC | 主机，Ubuntu 22.04，192.168.31.79 | SSH: ding/1234 |
| PF32 | 32×32 SPAD，TCSPC 55ps/bin | USB |
| 激光驱动 | YSC-SO-M04-4，Modbus RTU 9600 | /dev/ttyUSB0 |
| STM32F103 | 调焦电机，TMC2209 | /dev/ttyUSB1 |

---

## 项目结构

```
TOF单光子2.0/
├── acquisition/            # C++ 采集层（哪吒运行）
│   ├── sim_pf32.cpp        # 帧模拟器（P1 ✅）
│   ├── ExampleTOF.cpp      # 真实 PF32（P7 ⬜，需 SDK）
│   ├── depth_proto.h       # TofFrame 协议（2070B）
│   └── peak_detect.h       # 峰值检测算法（待 ML 替换）
│
├── qt_app/                 # Qt5 主程序（哪吒运行）
│   ├── mainwindow.{h,cpp}  # 主窗口
│   ├── depthparser.{h,cpp} # 解析 /tmp/depth.dat
│   ├── depthwidget.{h,cpp} # 2D 热图
│   ├── pointcloudwidget.{h,cpp} # 3D OpenGL 点云
│   ├── feedbackcontroller.{h,cpp} # 激光/电机反馈控制
│   ├── laseruart.{h,cpp}   # Modbus RTU
│   ├── motoruart.{h,cpp}   # STM32 串口
│   ├── datarecorder.{h,cpp} # 本地 .tof 录制
│   ├── cloudsyncer.{h,cpp} # SQLite 队列 + 异步上传
│   └── tof_viewer.pro      # QT += core gui widgets serialport opengl network sql
│
├── cloud/                  # 云端平台
│   ├── server/main.py      # FastAPI (✅ 运行在哪吒 8765)
│   ├── server/models.py    # aiosqlite 表结构
│   └── requirements.txt
│
├── ml/                     # 深度学习（P9-P11，待实现）
│   ├── data/               # 数据集工具
│   ├── models/             # 模型定义
│   ├── train/              # 训练脚本
│   └── export/             # ONNX 导出
│
├── deploy/                 # 哪吒部署脚本（Python paramiko）
│   ├── upload_qt.py        # 上传 qt_app 源码
│   ├── build_qt.py         # 在哪吒远程编译
│   ├── restart_all.py      # 重启所有服务
│   └── status.py           # 检查进程状态
│
├── docs/
│   ├── agent-work/
│   │   └── progress.md     # ← 必读，工作进度
│   └── 文献/               # 27 篇参考论文（.md 格式）
│
├── ARCHITECTURE.md         # 完整架构设计
├── CLAUDE.md               # Claude 工作指南
└── AGENTS.md               # 本文件
```

---

## 构建与部署

### Qt 应用（在哪吒上编译）

```bash
cd ~/TOF2.0/qt_app
qmake tof_viewer.pro && make -j4
```

依赖：`libqt5serialport5-dev libqt5opengl5-dev libqt5sql5-dev`

### 运行全套服务

```bash
# 1. FastAPI 服务（必须从 cloud/server/ 目录启动）
cd ~/TOF2.0/cloud/server
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8765 > /tmp/fastapi.log 2>&1 &

# 2. 采集模拟器
nohup ~/TOF2.0/acquisition/sim_pf32 > /tmp/sim_pf32.log 2>&1 &

# 3. Qt 主程序
DISPLAY=:1 nohup ~/TOF2.0/qt_app/tof_viewer \
  --depth-file /tmp/depth.dat \
  --data-dir ~/tof-data/depth_queue \
  --cloud-url http://localhost:8765 \
  > /tmp/tof_viewer.log 2>&1 &
```

### 部署更新到哪吒

```bash
# 上传 qt_app 并重新编译
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
magic       8B  "TCHIST1\0"
seq/width/height/bins  各 2-4B
payload     uint16[32×32×1024] = 2MB
```

---

## 开发阶段状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| P1 采集验证 | ✅ | sim_pf32 在哪吒运行 |
| P2 Qt 骨架 | ✅ | 编译并在哪吒 HDMI 运行 |
| P3 2D 显示 | ✅ | jet 色图热图 |
| P4 3D 点云 | ✅ | OpenGL，鼠标旋转/缩放 |
| P6 串口外设 | ✅ | 激光 + 电机 + 反馈控制 |
| P5a 本地录制 | ✅ | DataRecorder，.tof 文件 |
| P5b 离线上传 | ✅ | CloudSyncer，SQLite 队列 |
| P5c 云端平台 | ✅ | FastAPI + SQLite |
| P7 真实 PF32 | ⬜ | 等待硬件 + PF32 SDK |
| P8 调焦标定 | ⬜ | 等待硬件 |
| P9 数据采集管道 | ⬜ | TCSPC 上传 + 数据集构建 |
| P10 ML 训练 | ⬜ | 透雾深度学习模型 |
| P11 本地推理 | ⬜ | ONNX Runtime 部署到哪吒 |
| P12 闭环优化 | ⬜ | 模型输出驱动反馈控制 |

---

## 编码约束

- C++ 标准：C++17，Qt5，GLSL 1.x（Mesa 兼容）
- Python：3.10+（哪吒系统 Python）
- 不硬编码串口设备名、IP、端口，全部通过命令行参数传入
- 串口访问需 dialout 组：`sudo usermod -aG dialout ding`
- Qt 主线程只做渲染和串口控制，不做阻塞 IO
- CloudSyncer 上传失败不得阻塞采集和显示
- 修改 `depth_proto.h` 前先确认与 acquisition 层同步
- 不读取 .env、私钥、token 等凭据文件
