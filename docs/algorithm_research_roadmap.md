# 单光子 LiDAR 深度估计算法路线图

> 本文档综合当前调研、已实现代码与数据集特性，梳理算法全景，并给出在 Gutierrez SimSPADDataset 上取得好效果的具体策略。

---

## 一、算法全景

### 1.1 直接峰值检测类

| 算法 | 思路 | 本项目状态 | 低 SBR 表现 |
|------|------|-----------|------------|
| Argmax | histogram 直接取最大 bin | ✅ 已实现 (`argmax_v0`) | 差（噪声峰胜出） |
| Weighted centroid | 峰值附近 bins 加权平均 | ⬜ 未实现 | 略优于 argmax |
| Matched filter / LMF | histogram 与 IRF 做互相关再取峰 | ⬜ 未实现 | 好 |
| ZNCC | 零均值归一化互相关 | ⬜ 未实现 | 好（对强度不敏感） |

**Argmax 失效原因**：SBR=0.2 时背景噪声是信号的 5 倍，单次采集几乎必然有背景 bin 的峰值高于信号峰值。

### 1.2 背景感知类

| 算法 | 核心思路 | 实现难度 | 来源 |
|------|---------|---------|------|
| 常数背景减除 | 减去均值 → 再 argmax | ⚠️ **数学等价**，不改变结果 | — |
| 尾部背景估计 | 取直方图末端（无信号区域）bins 均值为背景，减除后再找峰 | 低 | 工程经验 |
| 指数/Gamma 背景拟合 | 把雾散射建模为指数衰减曲线，拟合后整体减除 | 中 | M2R3D (2021) |
| Poisson MLE | 建立信号+背景 Poisson 模型，联合最大似然求 depth | 中高 | 统计方法 |
| Hierarchical Bayes / MAP | 加空间先验（MRF），鲁棒联合估计 | 高 | M2R3D (2021) |

> **关键洞察**：在真实雾散射场景中，背景不是均匀分布，而是近端 bins 有强 backscatter，必须建指数模型才能正确扣除。

### 1.3 空间 / 多像素协同类

| 算法 | 思路 | 本项目状态 |
|------|------|-----------|
| 空间 histogram 池化 | 3×3/5×5 邻域直方图求和，再找峰 | ✅ 已实现 (`spatial_argmax_3x3`) |
| 超分辨率空间重建 | 低分辨率 histogram cube → 高分辨率 depth map | ⬜ 参考 M2R3D |
| 双边滤波后处理 | 在 depth map 上做边缘保持平滑 | ⬜ 简单 |
| Total variation 正则化 | depth map TV 范数最小化 | ⬜ 中等 |

### 1.4 联合估计类

| 算法 | 思路 | 实现难度 | 来源 |
|------|------|---------|------|
| 联合 depth + reflectivity | timestamp 同时编码飞行时间和反射强度，联合 MLE | 中高 | SPLiDER (2025) |
| 多光谱联合重建 | 多波长 histogram 约束同一深度 | 高 | Halimi et al. (2019) |

### 1.5 机器学习类

| 算法 | 思路 | 适用场景 |
|------|------|---------|
| 深度展开（deep unrolling） | 把迭代算法展开为可训练网络 | 有配对数据集 |
| SPLiDER | 双分支网络 + cross-attention，处理 timestamp frames | 动态场景 |
| 多尺度概率网络 | histogram cube → 超分辨率 depth + 不确定度 | 大规模训练数据 |

> ML 类方法放 `research/ml_offline/`，本阶段不部署到哪吒/RK3568。

---

## 二、当前数据集特性分析

### Gutierrez SimSPADDataset

| 参数 | 值 |
|------|---|
| 分辨率 | 64×64 SPAD |
| 时间分辨率 | 1024 bins，80 ps/bin |
| 最大量程 | ~1024 × 80ps × c/2 ≈ 12.3 m |
| 场景数 | 20 室内场景，2091 个样本 |
| SBR | 0.2（背景是信号的 5 倍） |
| 平均信号光子数 | 2 光子/像素 |
| start-stop 方向 | forward（bin 大 = 远） |

### 关键字段

```
spad          (64,64,1024) float32  单次泊松采样，稀疏存储 → 这是算法输入
rates         (64,64,1024) float64  期望直方图（无限次平均值）→ 算法上界参考
bin           (64,64)      uint16   GT 深度（bin 索引，raw 值，无需乘以 BINS）
intensity     (64,64)      float64  强度图
est_range_bins_argmax  (64,64)  uint16  数据集提供的 argmax 估计（在 rates 上算的）
est_range_bins_lmf     (64,64)  uint16  数据集提供的 LMF 估计
est_range_bins_zncc    (64,64)  uint16  数据集提供的 ZNCC 估计
```

### 核心差距：single shot vs ensemble

> 以下数字来自 `research/run_verify_baseline.py`（2026-05-28 实测），跑 5 个不同场景的
> `spad_0011_p1.mat` 样本，hit_rate 在 4 个容差档上取均值，RMSE 取均值。

```
5 样本均值（hit@200mm / RMSE）：
  argmax_spad   (单次泊松直接 argmax)             0.178   1976 mm
  est_argmax    (数据集自带，在 spad 上算)         0.580   1815 mm
  est_lmf       (数据集自带，在 spad 上算)         0.633   2359 mm
  est_zncc      (数据集自带，在 spad 上算)         0.631   2383 mm
  argmax_rates  (反归一化 rates 上 argmax，上界)   1.000     12 mm

差距根源：
  spad  = 单次泊松采样，每像素仅 ~12 个光子（2 signal + 10 background）
  rates = 反归一化的期望直方图，等价于无穷长积分时间
  est_* = 数据集制作者在带噪 spad 上预算的传统算法 baseline
```

**关键事实**：
- `argmax_rates` RMSE 恰为 1 bin（12 mm），是 argmax 离散化的本征下界，**rates 上算法上界 ≈ 100%**。
- `est_argmax`/`lmf`/`zncc` 三个数据集自带字段都是**在带噪 spad 上**算的（不是 rates）；其中 LMF 输出 max 可达 1031（>1024），看起来是循环卷积 padding 痕迹。
- 场景间难度方差大：最难 dining_room_0022 spad-argmax 8.6%，最易 office_0002c 27.7%（4 倍），单样本结果不可推广。
- 早期描述里把 0.323 称作 "rates 上 argmax 的上界" 属误传——它实际是 dining_room_0022/spad_0011_p1 这个**单样本**上 est_argmax 的 hit@200mm，与 rates 无关。

**算法工作区间**：

```
0.178 ← 我们当前 baseline (argmax_spad)
   │
   │   ↑↑↑ Step 2 (tail_bg + 空间池化) / Step 3 (LMF with shared PSF) 目标区间
   │
0.633 ← 数据集传统算法天花板 (est_lmf/zncc on spad)
   │
   │   ↑↑↑ Step 4 (Poisson MLE 物理建模) 目标区间
   │
1.000 ← rates 无噪上界 (argmax_rates)
```

---

## 三、在数据集上取得好效果的策略

### 策略层级（按实现成本排序）

```
Level 0  在 rates 上验证实现正确性
Level 1  改进 spad 上的单次估计（背景估计 + LMF）
Level 2  空间聚合提升有效光子数
Level 3  多样本聚合模拟积分时间
Level 4  物理模型拟合（Poisson MLE / 背景建模）
Level 5  ML 超分辨率 / 联合估计
```

---

### Level 0：在反归一化 `rates` 上建立算法上界（已实测）

**目的**：钉死算法上界，排除实现 bug。

注意：`.mat` 文件里的 `rates` 字段是**归一化的**（值域 [0,1]），必须用同文件的
`rates_norm_params.rates_offset/rates_scaling` 反归一化才能当期望直方图用。
loader 提供 `SpadSample.denormalized_rates()` 方法。

```python
from research.sim_spad_loader import load_spad_mat
sample = load_spad_mat(path)
dense_rates = sample.denormalized_rates()    # (H,W,BINS) 反归一化期望直方图
pred_bin = dense_rates.argmax(axis=2)        # 在无噪期望上 argmax
# 实测 hit_rate@12mm = 100%, RMSE = 12mm（恰好 1 bin）
```

**验收标准**：`hit_rate@200mm ≥ 99%`，RMSE ≤ 13 mm（约 1 bin）。
入口：`python research/run_verify_baseline.py`

---

### Level 1：尾部背景估计 + 减除

**原理**：  
histogram 末端（远距离 bins，无真实目标）的计数几乎全是均匀背景噪声。

```
bg_level = mean(spad[:, :, 900:1024], axis=2)   # 取末端 124 个 bins 的均值
spad_sub = spad - bg_level[:, :, None]           # 每个像素减去自己的背景估计
spad_sub = max(spad_sub, 0)                      # clip 负值
peak_bin = spad_sub.argmax(axis=2)
```

**预期收益**：能在不知道 IRF 的情况下，将信噪比提升约 2-5 倍（取决于背景均匀程度）。

> ⚠️ 注意：对 PF32（reverse start-stop），背景估计区域应取 **低 bin 端**（bin 0:124），不是末端。

---

### Level 2：LMF 实现（需 IRF）

**原理**：  
用 IRF（激光脉冲 + 探测器响应的联合脉冲形状）与 histogram 做互相关，相当于匹配滤波，大幅抑制背景噪声。

**IRF 获取方案（数据集中无直接 IRF 字段）**：
```python
# 方案 A：用高斯近似，sigma 约 2-3 bins（代表 ~160-240 ps 系统展宽）
irf = gaussian(n_bins=1024, center=512, sigma=2.5)

# 方案 B：从 rates 字段反推 IRF
# 选取强度高、深度确定的像素，其 rates[y,x,:] 的形状即为 IRF 形状
# 用 est_range_bins_argmax[y,x] 对齐后平均多个像素

# 方案 C：从数据集 LMF 与 argmax 结果差异反推
```

**LMF 互相关**：
```python
from scipy.signal import fftconvolve
irf_flipped = irf[::-1]
corr = fftconvolve(spad[y, x, :], irf_flipped, mode='same')
peak_bin = corr.argmax()
```

**预期收益**：在 `rates` 上实现后应与 `est_range_bins_lmf` 完全匹配；在 `spad` 上约比 argmax 提升 10-20 个百分点 hit_rate。

---

### Level 2b：空间池化（已实现，可扩展）

| 核大小 | 有效光子数 | 代价 |
|--------|-----------|------|
| 1×1（原始） | 2 光子 | 无 |
| 3×3 | 18 光子 | 轻微空间模糊 |
| 5×5 | 50 光子 | 明显边缘模糊 |
| 7×7 | 98 光子 | 严重模糊 |

**建议**：3×3 是工程折中点。对于本数据集（室内精细场景），7×7 会损失深度边缘信息。

---

### Level 3：多样本聚合（模拟积分）

**原理**：  
数据集中同一场景有多个样本（spad_XXXX_pN.mat，N 为不同采样次数），可以：

```python
# 加载同一像素位置的多个 spad 样本并累加，模拟更长积分时间
hist_accum = np.zeros((64, 64, 1024))
for path in scene_samples[:K]:
    hist_accum += load_spad_mat(path).spad
# 对 hist_accum 做 argmax 或 LMF
```

**预期效果**：K=10 次累加相当于 10 倍积分时间，SBR 等效提升 √10 ≈ 3.16 倍，hit_rate 应显著提升。

---

### Level 4：Poisson MLE / 指数背景拟合

**模型**：
```
每个 bin t 的期望计数 λ(t) = signal_amp × IRF(t - d) + bg_amp × exp(-α×t) + bg_floor
参数：d（深度）, signal_amp, bg_amp, α, bg_floor
目标：最大化 Poisson 对数似然 Σ_t [spad(t) × log λ(t) - λ(t)]
```

**实现路径**：
1. 先用 Level 1 背景估计初始化 `bg_floor`
2. 用 Level 2 LMF 结果初始化 `d`
3. 用 scipy.optimize.minimize 做局部优化

**预期收益**：在单 pixel 上理论最优，但计算量 O(64×64×iters)，需要向量化或 GPU。

---

### Level 5（中长期）：ML 超分辨率 + 联合估计

参考 SPLiDER (2025)：
- 训练输入：`spad` (64×64×1024) + 若干 timestamp frames
- 训练目标：`bin` (GT depth) + `intensity`
- 网络输出：depth + reflectivity + confidence

适合 `research/ml_offline/` 路线，当前数据集 2091 样本偏少，建议配合数据增强（inject_fog, Poisson 重采样）扩充。

---

## 四、近期实施计划

### 当前已实现

- [x] `argmax_v0`：直接峰值检测
- [x] `spatial_argmax_3x3`：3×3 空间池化后 argmax
- [x] 数据集内置 argmax/LMF/ZNCC 读取（通过 dataset 字段）
- [x] metrics: RMSE、hit_rate、compute_all
- [x] viz: 2×3 可视化面板

### 下一步（推荐顺序）

```
Step 1  在 rates 字段上验证 argmax 实现 → 确认 hit_rate ≥ 30%
Step 2  实现尾部背景估计 + 减除，测试 spad 上的提升
Step 3  实现 LMF（高斯 IRF 近似），在 rates 上比对 est_range_bins_lmf
Step 4  在 spad 上比较：argmax vs bg_sub_argmax vs spatial vs LMF
Step 5  多样本聚合实验：hit_rate 随 K 的曲线
Step 6  inject_fog 实验：往 rates 上叠加不同浓度雾模型，测算法退化曲线
Step 7（可选）指数背景 MLE，向 M2R3D 靠拢
```

---

## 五、PF32 实机注意事项

本数据集算法迁移到 PF32 时需调整的关键点：

| 项目 | SimSPAD 数据集 | PF32 实机 |
|------|--------------|---------|
| bin 方向 | forward（bin大=远） | **reverse**（bin大=近） |
| bin 时间宽度 | 80 ps/bin | **55 ps/bin** |
| 分辨率 | 64×64 | **32×32** |
| 量程 | ~12 m | 取决于激光功率 |
| 积分方式 | 单次泊松采样（数据集） | 多脉冲硬件积分，直方图已是累积值 |
| 背景估计区域 | 末端高 bin | **低 bin 端**（reverse） |
| IRF 来源 | 数据集无，用高斯近似 | 可用近场反射板测量实际 IRF |

---

## 六、参考文献

| 论文 | 方法 | 本地路径 |
|------|------|---------|
| Tobin et al. 2021 (Scientific Reports) | M2R3D，指数背景 + 贝叶斯估计 | `refs/papers/robust_3D_imaging_obscurant_SP_LiDAR_2021.pdf` |
| Weerasooriya et al. 2025 (arXiv 2505.13250) | SPLiDER，联合深度+反射率 | `refs/papers/joint_depth_reflectivity_SP_LiDAR_2025.pdf` |
| Gutierrez et al. 2022 | SimSPADDataset | `research/datasets/` |
| docs/文献/ | 其余 27 篇文献汇总 | `docs/文献/` |
| 两篇论文中文总结 | — | `docs/文献/sp_lidar_fog_papers_summary.md` |
