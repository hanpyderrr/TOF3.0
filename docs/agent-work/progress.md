# 工作进度

> 最后更新：2026-05-18
> 主控：Claude Sonnet 4.6

---

## 当前状态快照

**TOF 3.0 项目初始化完成，目录结构按设备分层，RK3568 串口已通。**

| 节点 | 状态 |
|------|------|
| 哪吒侧代码（P1–P6, P5a/b/c） | ✅ 已从 TOF2.0 迁移，路径更新完毕 |
| 目录重组（nezha/rk3568/cloud） | ✅ 已提交 |
| RK3568 串口连通 | ✅ COM7, 1500000 baud |
| RK3568 硬件摸底 | ✅ 完成（见下方） |
| RK3568 SpiReceiver 代码 | ⬜ 待编写 |
| P9 TCSPC 上传端点 | ⬜ 待实现 |

---

## RK3568 硬件摸底（2026-05-18）

### 基本信息

| 项目 | 详情 |
|------|------|
| 板型 | ATK-DLRK3568（正点原子） |
| 系统 | Buildroot 2018.02-rc3（2024-08-29 编译） |
| 架构 | aarch64 |
| 登录 | root，无密码，开机自动进 shell |
| 串口 | COM7（Windows），CH340，USB 转 Type-C，1500000 baud |

### 可用环境

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.8.6 | ✅ 可直接写脚本 |
| Perl | 已装 | |
| BusyBox | v1.34.1 | 基本工具齐全 |
| make | 4.2.1 | ✅ |
| gcc/g++ | **无** | ❌ 不能原生编译 C/C++ |
| cmake | 无 | |

### 网络现状（暂无网络）

| 接口 | 状态 | 原因 |
|------|------|------|
| eth0/eth1 | DOWN | DMA init 失败，未接网线 |
| usb0 (5G) | NO-CARRIER | Quectel RM500U-CNV，**未插 SIM 卡** |

5G 模块信号强度 13（中等），模块本身正常，缺 SIM 卡。

### SPI 设备树

`/proc/device-tree/spi@fe610000` 存在，SPI 控制器可用，slave 模式待确认配置。

---

## 已完成工作记录

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

---

## 下一步工作计划

### 优先级排序（当前无 PF32、RK3568 无网络）

| 优先级 | 任务 | 在哪做 | 依赖 |
|--------|------|--------|------|
| 🔴 | RK3568 SPI slave receiver（Python） | Linux SDK 机 / 串口传文件 | 无 |
| 🔴 | P9-1：TCSPC 云端接收端点 | 本地 | 无 |
| 🟡 | sim_tcspc 模拟 TCSPC 生成器 | 哪吒 | 无 |
| 🟡 | 物理算法层（background/CFAR/Gaussian） | 本地 | sim_tcspc |
| 🟡 | 哪吒侧 SpiSyncer（Python 或 C++） | Linux SDK 机 | RK3568 GPIO 接线 |
| 🟢 | P10 ML 训练 | 云端 GPU | 真实数据 |

### RK3568 SpiReceiver 开发方案

**推荐：在有 SDK 的 Linux 机上交叉编译**
```bash
# 安装交叉编译器
sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu

# 编译
aarch64-linux-gnu-gcc -o spi_receiver spi_receiver.c

# 传输到 RK3568（有网后 scp，或串口 base64 编码传输）
```

**备选：Python 版本**（无需编译，串口直接传脚本文本）
```python
# rk3568/spi_receiver/spi_receiver.py
# 用 spidev 或 /sys/bus/spi 访问 SPI slave
```

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
| RK3568 SPI slave 设备树是否已配置 | ⬜ 待查 `/proc/device-tree/spi@*/status` |
| spidev kernel module 是否已加载 | ⬜ 待查 `ls /dev/spidev*` |
| SIM 卡何时插入 | ⬜ 待用户准备 |
| 网线是否可接 | ⬜ 待用户确认 |
| Linux SDK 机上的交叉编译器版本 | ⬜ 待确认 |

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
| `docs/rk3568_connection.md` | 新增，串口连接文档 | ✅ |
| `cloud/server/main.py` | 加 POST /api/frames/tcspc | ⬜ P9-1 |
| `rk3568/spi_receiver/` | SPI slave 接收实现 | ⬜ 下一步 |
| `rk3568/cloud_syncer/` | 5G 上传实现 | ⬜ |
| `nezha/qt_app/cloudsyncer.*` | 改为 SPI 推送模式 | ⬜ |
