# 深度学习深度估计方案

> 针对 PF32 32×32 SPAD + TCSPC laser_master 的 DL 接入建议。
> 背景：刘洪瑞建议从每像素 TCSPC 直方图提取峰值特征，送入 3D 点云或学习型滤波网络重建空间深度图。

---

## 现有学术开源网络

### 1. Lindell et al. 2018 — 最直接对口

**论文**：Single-Photon 3D Imaging with Deep Sensor Fusion（SIGGRAPH Asia 2018）
**代码**：`computational-imaging/single-photon-3D`（GitHub）

- 3D CNN 沿 1024 bin 轴压缩直方图，2D 解码器输出深度图
- 传感器分辨率也是低分辨率 SPAD（32×32 量级），输入格式 H×W×1024 与 PF32 完全一致
- **项目现有 `Hist3DNet` 就是在复现这篇的核心思路**，权重可直接加载做 finetune
- 在仿真数据 + 真实数据上联合训练，对光子稀疏场景鲁棒

**接入点**：替换 `research/ml_offline/models/hist3d_net.py` 中的 `Hist3DNet`，跑 `run_benchmark.py` 对比 argmax 基线。

---

### 2. Gutierrez-Barragan — 数据格式已完全对齐

**论文**：Compressive Single-Photon 3D Cameras（CVPR 2022）及后续 ICCV 2023
**代码**：`felipegb94/compressive-spad-lidar`（GitHub）

- 项目 `sim_spad_loader.py` 已对齐其 `.mat` 数据格式（`SpadSample` 契约）
- 仓库含配套基线网络（1D/3D CNN 变体 + unmixing 网络）
- **零格式转换**：把他的网络代码放入 `research/ml_offline/models/`，用现有 loader 直接喂数据

**接入点**：这是最快可跑通的路径，建议作为第一步。

---

### 3. PointCleanNet — 对应刘洪瑞"点云学习滤波"建议

**论文**：Learning to Denoise and Inpaint 3D Point Clouds（CGF 2020）
**代码**：`mrakotosaon/pointcleannet`（GitHub）

- 输入稀疏点云（含噪声），输出去噪后点云
- 流程：每像素 argmax → (x, y, depth, confidence) 点集 → PointCleanNet → 精化深度
- 局限：32×32=1024 点偏少，需缩减网络规模；邻域去噪效果依赖点云密度

**接入点**：`research/algorithms/` 加 top-K 峰值提取 → 点云构建 → 接 PointCleanNet。

---

## 三条落地路线

### 路线 A：峰值特征 + 2D CNN 去噪（最快，2 周内可跑）

对应刘洪瑞"找几个大值作为原始数据"的建议。

```
TCSPC 直方图 [32×32×1024]
   ↓ top-3 峰值提取（bin位置 + 计数 + FWHM）
特征图 [32×32×9]
   ↓ DepthUNet（research/ml_offline/models/hist3d_net.py，已有）
深度图 [32×32]
```

- 计算量小，哪吒 CPU 可跑；导出 ONNX 后 OpenVINO 加速约 3-5x
- 不需要全量 TCSPC 直方图参与推理，延迟低
- 需在 `peak_detect.h` 扩展 `pd_top3_peaks()`，Python 侧 `research/algorithms/` 对齐

### 路线 B：端到端 Hist3DNet / Lindell 权重（中期）

```
TCSPC 直方图 [32×32×1024]
   ↓ Hist3DNet（3D CNN + U-Net）
深度图 [32×32]
```

- 用 SimSPADDataset 预训练，再用 `~/tof-data/raw_tcspc/` 真实数据微调
- 推理延迟待实测（N97 CPU 约 50-200ms 量级，需 OpenVINO 量化）
- `ml_offline/export/to_onnx.py` 已有导出骨架

### 路线 C：多峰分离（激光回波 + 背景雾，长期）

现有 argmax 只取最大峰，**双峰场景（前景目标 + 雾散射）完全无法处理**。

```
每像素直方图 [1024]
   ↓ 轻量 1D CNN（逐像素，参数共享）
峰值类型分类 + 前景深度
```

- 这是 DL 相对传统算法最大的差异化价值
- 训练数据：`inject_fog.py`（已有）可生成带雾仿真样本作为监督信号

---

## 推荐路线图

```
现在
 ├─ 路线 A（2周）：top-3峰特征 + DepthUNet + OpenVINO 部署
 │      ↓ 用真实 raw_tcspc 数据标注（50-100帧即可启动）
 ├─ 路线 B（1-2月）：Lindell/Gutierrez 网络 finetune，ONNX 导出
 │      ↓ 积累双峰场景（雾/近物遮挡）数据
 └─ 路线 C（长期）：1D CNN 多峰分离，解耦前景/背景
```

---

## 与现有代码的接合关系

| 现有文件 | 接入网络 | 说明 |
|----------|----------|------|
| `sim_spad_loader.py` | Gutierrez 网络 | 格式零转换 |
| `ml_offline/models/hist3d_net.py` | Lindell 2018 权重 | 架构一致，可加载 |
| `research/algorithms/argmax.py` | PointCleanNet | argmax 出点云后接去噪 |
| `ml_offline/export/to_onnx.py` | 三个网络均支持 | ONNX 导出骨架已有 |
| `inject_fog.py` | 路线 C 训练数据 | 雾仿真样本生成 |
| `peak_detect.h` | 路线 A 前置 | 扩展为 top-3 峰输出 |

---

## 硬件部署约束

- **哪吒 Intel N97**：支持 OpenVINO（Alder Lake-N），推理加速首选；避免完整 3D CNN 在 CPU 裸跑
- **RK3568**：只负责显示，不跑推理；深度图经 SPI 从哪吒推送过来
- **推理位置**：哪吒采集后本地推理 → 结果写 `/tmp/depth.dat` → SPI 发 RK3568

---

## 第一步行动项

1. 克隆 `felipegb94/compressive-spad-lidar`，把基线网络放入 `research/ml_offline/models/gutierrez_net.py`
2. 写 wrapper 接 `SpadSample.hist` → 网络输入 → 深度图输出
3. 跑 `run_benchmark.py` 对比 argmax / lmf / Gutierrez 网络三条基线的 hit_rate 和 RMSE
