# 工作进度

> 最后更新：2026-05-18
> 主控：Claude Sonnet 4.6 | Worker：Codex (gpt-5.5)

---

## 当前状态快照

**P1–P6 + P5a/P5b/P5c 全部完成并在哪吒验证运行。**

哪吒上正在运行：
- `sim_pf32`（帧模拟器，~2Hz）
- `tof_viewer`（Qt 主程序，DISPLAY=:1）
- `FastAPI`（8765 端口，/api/health 正常）

下一阶段重点：**透雾成像深度学习（P9→P10→P11）**

---

## 已完成工作记录

### 2026-05-18 — P5a/P5b/P5c 实现与验证

**实现内容：**
- `qt_app/datarecorder.{h,cpp}` — 本地 .tof 文件录制
- `qt_app/cloudsyncer.{h,cpp}` — SQLite 上传队列 + 异步 HTTP
- `cloud/server/main.py` — FastAPI 接收端
- `mainwindow.{h,cpp}` 更新 — Record 面板 UI
- `main.cpp` 更新 — `--data-dir` / `--cloud-url` 参数
- `tof_viewer.pro` 更新 — `QT += network sql`

**验证结果：**
- tof_viewer 编译成功（163KB，0 错误）
- FastAPI `/api/health` 返回 `{"status":"ok"}`
- CloudSyncer 30s 轮询正常，在线状态检测正常

**已知限制：**
- 录制需在 UI 复选框手动启用（无法通过 SSH 触发）
- TCSPC 原始上传未实现（P9 任务）

---

## 当前任务：P9 数据采集管道

### 目标
收集配对数据集：`(TCSPC 原始直方图, 地面真值深度图)`，上传云端，用于深度学习训练。

### 子任务

#### P9-1 TCSPC 上传（云端接收）
- **文件：** `cloud/server/main.py`
- **任务：** 新增 `POST /api/frames/tcspc` 端点
  - multipart/form-data 接收 .tch 文件
  - 存储到 `data/tcspc/` 目录
  - 在 SQLite 记录元数据
- **格式参考：** AGENTS.md 中 TCSPC .tch 格式

#### P9-2 TCSPC 本地写入（ExampleTOF）
- **文件：** `acquisition/ExampleTOF.cpp`（待 PF32 SDK）
- **任务：** 采集时同步写 .tch 文件到 `~/tof-data/raw_tcspc/`
- **当前状态：** 等待 PF32 硬件，先写文件格式和 writer 工具类

#### P9-3 TCSPC 上传队列（CloudSyncer 扩展）
- **文件：** `qt_app/cloudsyncer.{h,cpp}`
- **任务：** 在 upload_queue.db 新增 tcspc 类型队列
- **注意：** 2MB/帧，不能阻塞深度帧上传

#### P9-4 数据集工具（云端）
- **文件：** `ml/data/`
- **任务：** Python 脚本从 FastAPI 拉取数据，构建训练集

---

## 下一阶段规划

### P10 — 透雾 ML 训练（云端 GPU）

**核心思路：**
TCSPC 直方图包含完整光子到达时间分布，雾散射表现为早期返回的背景噪声，信号峰被淹没。深度学习直接从直方图中学习分离信号。

**模型方案（按优先级）：**

1. **基线：2D CNN 深度图去噪**
   - 输入：32×32 噪声深度图
   - 输出：32×32 去雾深度图
   - 快速验证可行性

2. **主模型：3D CNN on TCSPC 直方图**
   - 输入：32×32×1024 光子计数直方图
   - 输出：32×32 深度图
   - 参考：赫瑞瓦特大学贝叶斯重建、密度聚类高斯拟合
   - 文献：docs/文献/08_、09_、10_

3. **进阶：物理引导网络**
   - 内嵌泊松噪声模型
   - 更好泛化性，需要更少数据

**训练数据需求：**
- 雾天/晴天配对数据（室外采集）
- 或仿真数据（基于雾散射物理模型生成）

### P11 — 本地推理部署（哪吒）

- 训练完成后导出 ONNX
- ONNX Runtime CPU 推理（N97 AVX2，约 10-50ms/帧）
- 集成点：替换 `acquisition/peak_detect.h` 中峰值检测逻辑
- 或在 Qt 层作为后处理：`DepthParser → ML Refiner → DepthWidget`

### P12 — 闭环优化

- ML 输出的置信度图 → FeedbackController
- 雾浓度估计 → 自适应激光功率调整

---

## 关键决策记录

| 时间 | 决策 | 原因 |
|------|------|------|
| 2026-05-18 | 去掉 RK3568，单机哪吒 | SPI 链路脆弱，哪吒性能够用 |
| 2026-05-18 | 深度帧和 TCSPC 分开上传 | TCSPC 2MB/帧，不能阻塞实时链路 |
| 2026-05-18 | ONNX Runtime 部署 | 跨平台，CPU 推理性能足够 32×32 分辨率 |
| 2026-05-18 | 先做 2D CNN 基线 | 快速验证端到端流程，再升级到 3D |
| 2026-05-18 | **RK3568 回归**，作为 5G 上行网关 | 哪吒无网络，RK3568 有 5G 模块 |
| 2026-05-18 | 电机控制迁移到 RK3568 | RK3568 有专用电机驱动引脚，复用 v1.0 代码 |
| 2026-05-18 | SPI 改为文件队列异步传输 | 避免重蹈实时流 SPI 不稳定覆辙 |
| 2026-05-18 | 主动调制分离算法思路 | 利用激光功率/焦距变化区分雾和目标，文献中无此方法 |

---

## 新增算法文档（本次整理）

| 文档 | 路径 | 内容 |
|------|------|------|
| 主动调制分离算法 | `docs/active_modulation_separation_algorithm.md` | 焦距差分 + 激光 pile-up 差分分离雾/目标 |
| RK3568 回归架构 | `docs/rk3568_reintegration_architecture.md` | SPI 文件队列 + 5G 上行 + 电机迁移 |
| 算法部署建议 | `docs/pf32_x86_tof_algorithm_deployment.md` | 哪吒/RK3568 分工，算法实施顺序 |
| 文献综述与路线 | `docs/tof_algorithm_literature_review_and_plan.md` | 27 篇文献，三阶段算法路线 |

---

## 待做事项（按优先级）

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| 🔴 高 | P7：真实 PF32 联调 | PF32 硬件到位 |
| 🔴 高 | P8：电机焦距标定 | P7 + RK3568 电机接线 |
| 🟡 中 | P9-1：TCSPC 上传端点 | 可先做 |
| 🟡 中 | SpiSyncer 实现（哪吒侧）| 哪吒 GPIO 接线 |
| 🟡 中 | RK3568 工程初始化 | v1.0 代码移植 |
| 🟢 低 | P10 ML 训练 | 需要真实数据 |
| 🟢 低 | 主动调制分离算法实现 | 需要 pile-up 标定 / P8 标定 |

---

## 文件变更追踪

| 文件 | 最近变更 | 状态 |
|------|---------|------|
| `qt_app/mainwindow.cpp` | 加入 Record 面板 | ✅ 已部署 |
| `qt_app/cloudsyncer.cpp` | SQLite 队列实现 | ✅ 已部署 |
| `cloud/server/main.py` | FastAPI 4 端点 | ✅ 运行中 |
| `cloud/server/main.py` | 加 /api/frames/tcspc | ⬜ P9-1 |
| `qt_app/cloudsyncer.cpp` | TCSPC 上传队列 / 改为 SPI 推送 | ⬜ P9-3 |
| `qt_app/motoruart.*` | 抽象为 MotorController 接口 | ⬜ RK3568 回归时 |
| 新增 `spi_syncer/` | 哪吒侧 SPI master 推送器 | ⬜ RK3568 回归时 |
| 新增 `rk3568/` | RK3568 侧工程 | ⬜ RK3568 回归时 |
| `ml/` | ML 全部文件（Codex 已创建框架） | ⬜ P10 待数据 |
