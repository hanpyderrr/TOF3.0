# SP-LiDAR 深度与反射率联合估计 (SPLiDER)

> 原文: **Joint Depth and Reflectivity Estimation using Single-Photon LiDAR**
> Weerasooriya H. K., Chennuri P., Zhang W., Gyongy I., Chan S. H.
> arXiv:2505.13250 [cs.CV], 2025-05-19
> 单位: Purdue 大学（电子与计算机工程学院）+ Edinburgh 大学
> 资助: DARPA/SRC CogniSense JUMP 2.0, NSF IIS-2133032, ECCS-2030570
> 代码: 论文项目主页（原文给出 GitHub 链接）

---

## 1. 一句话定位

针对**高速动态场景**下单光子 LiDAR 数据：
- 不再先拼 3D 直方图立方再处理，而是**直接处理单帧时间戳（timestamp frames）**；
- 理论上首次用 **CRLB** 证明 “**深度与反射率信息互补**” 的成立条件；
- 工程上提出 **SPLiDER**（Single-Photon LiDAR joint Depth & Reflectivity）端到端深度网络，把这种互补性显式编码为 **跨模态特征共享**。

在仿真和真实 128×192 SPAD @1000fps 数据上，反射率 PSNR 23.03 / SSIM 0.69，深度 RMSE 0.0077，超过 SP-LiDAR 与视频复原两类基线。

---

## 2. 背景与动机

SP-LiDAR 单像元每个时间戳带两类信息：
- **深度**：脉冲飞行时间
- **反射率**：返回光子数

传统两类做法：

| 方案 | 数据形式 | 缺点 |
|------|----------|------|
| **3D 直方图立方** | 多周期累计成 (x, y, t-bin) cube | 时间窗长，运动模糊；动态场景失真 |
| **单帧时间戳** (Altmann 2020) | 每帧每像元只记第一光子的 timestamp | 每帧每像元 ≤1 个光子，信号极稀疏，算法难度高 |

现有联合估计的 SP-LiDAR 工作主要在 3D cube 上，且 depth/reflectivity 解码器分开（如 BPRNN）。SPLiDER 采取“时间戳 + 联合” 的组合。

## 3. 符号约定（Table I）

| 符号 | 含义 |
|------|------|
| $t_r$ | 脉冲重复周期 |
| $N_r$ | 一帧内重复次数 |
| $z$ | 真实深度 |
| $\tau = 2z/c$ | 真实时延 |
| $\alpha$ | 真实反射率 |
| $s(\cdot)$ | 脉冲形状（高斯，宽 $\sigma_t$） |
| $\lambda_b$ | 背景光速率 |
| $\eta$ | 量子效率 |
| $\lambda_d$ | 暗计数 |
| $S$ | 单脉冲能量 |
| $B = b_\lambda t_r$ | 单周期背景能量 |
| SBR | $\eta\alpha S / B$ |

光子到达视为非齐次 Poisson 过程：

$$ \lambda(t) = \eta\alpha\, s\!\left(t - \tfrac{2z}{c}\right) + b_\lambda \tag{1} $$

## 4. 理论：深度↔反射率信息互补（核心理论贡献）

### 4.1 联合密度（定理 1）

记一帧内观测到的时间戳为 $\mathbf{t}_M = \{t_k\}_{k=1}^M$。每帧 $M$ 由 $\text{Poisson}(N_r \Lambda(\alpha))$ 给出，其中 $\Lambda(\alpha) = \int_0^{t_r}\lambda(t)\,dt = \eta\alpha S + B$。则

$$ p[\mathbf{t}_M, M=m] = \frac{e^{-N_r \Lambda(\alpha)}}{m!}\prod_{k=1}^m N_r \lambda(t_k;\alpha,\tau) \tag{2} $$

### 4.2 联合 CML 估计

$$ (\hat\tau,\hat\alpha) = \arg\max_{0<\tau<t_r,\ \alpha\ge 0}\Bigl\{-N_r\eta S\alpha + \sum_{k=1}^m \log\!\bigl(\eta\alpha s(t_k-\tau) + b_\lambda\bigr)\Bigr\} \tag{3} $$

**关键观察**：只要 $b_\lambda > 0$，$\tau$ 与 $\alpha$ 在式 (3) 中**不可分**——它们通过 $\log$ 内部耦合。

### 4.3 推论 1：零背景时退化为可分

当 $b_\lambda = 0$：

$$ \hat\alpha = \frac{m}{N_r \eta S},\qquad \hat\tau = \frac{1}{m}\sum_k t_k \tag{4, 5} $$

→ 反射率= 光子计数估计；深度= 时间戳样本均值。两者独立，**互不帮助**。

### 4.4 推论 2 / 推论 3：CRLB

- 无深度先验的反射率 CRLB：

  $$ \mathrm{Var}[\hat\alpha_c^*] \ge \frac{1+1/\text{SBR}}{N_r(\eta S/\alpha)} \tag{7} $$

- 有深度先验时的反射率 CRLB：

  $$ \mathrm{Var}[\hat\alpha_t^*] \ge \left[N_r\eta^2 \int_0^{t_r}\frac{s^2(t-\tau)}{\eta\alpha s(t-\tau) + b_\lambda}\,dt\right]^{-1} \tag{9} $$

### 4.5 定理 2：有深度的反射率 CRLB 严格优

$$ \mathrm{CRLB}(\hat\alpha\,|\,\tau\text{ known}) \le \mathrm{CRLB}(\hat\alpha\,|\,\text{photon counts only}) \tag{10} $$

等号当且仅当 $b_\lambda = 0$。证明用 Cauchy–Schwarz（详见 Appendix B）。

**结论（理论的结论框）**：

> 当 $b_\lambda > 0$（即存在背景），**深度帮助反射率**，且**反射率帮助深度**。

仿真 Fig.2 数值验证：低 SBR 下互助带来的 MSE 差距更大；高 SBR 下两条曲线靠拢。

### 4.6 鲁棒求解算法（Appendix IX）
- **深度 MLE**：式 (5) 的负对数似然有许多局部极小（低 SBR 下）。Algorithm 1 用 “从 $\tau_0$ 双向扩张括号 + 根查找” 找最接近真值的零点。
- **反射率 MLE**：式 (8) 的左端在 $\alpha \in [0,\infty)$ 单调递减；若 $\tfrac{d}{d\alpha}L_t(\alpha)\big|_{\alpha=0} \le 0$ 则 $\hat\alpha=0$，否则二分法 (Algorithm 2)。

### 4.7 特征空间的“共享”验证
设计两路 CNN 自编码器：一路重建反射率，一路重建深度，损失加上 **隐特征 MSE**：

$$ \mathcal{L}_{all} = \mathrm{MSE}(\mathcal{D}_{gt},\mathcal{D}_{rec}) + \mathrm{MSE}(\mathcal{R}_{gt},\mathcal{R}_{rec}) + \sigma\cdot\mathrm{MSE}(\mathcal{D}_{lsFeat},\mathcal{R}_{lsFeat}) \tag{11} $$

NYU V2 数据上 $\sigma=0.5$。PCA 投影显示深度 / 反射率 latent 有显著共定位部分，支撑“共享特征确实存在”的工程假设。

## 5. SPLiDER 网络（工程贡献）

输入：$K$ 个相邻时间戳帧 $\{\mathcal{T}_i\}$（含目标帧 $N$）；二值帧 $\{\mathcal{B}_i\}$ 由阈值化得到（有 timestamp 标 1，否则 0）。
输出：多尺度深度图 $\{\mathcal{D}^j\}$ 与反射率图 $\{\mathcal{R}^j\}$，$j\in\{1,2,4\}$ 为尺度。

四个模块（Fig.4 概览）：

### 5.1 Hybrid Feature Extraction (HFE, Fig.7)
- 两个并行去噪自编码器分别处理 timestamp 帧、binary 帧
- 同时保留 **noisy** 和 **denoised** 特征 → 既得粗结构又留细节
- 深度分支由 timestamp 提，反射率分支额外用 noisy binary（提细节）

### 5.2 Bidirectional Flow Estimation + Feature Alignment (IBFE + STAR, Fig.8)
- 用 denoised 反射率帧估 **双向光流**（鲁棒）
- **STAR**：Spatial-Temporal Alignment with Residual Refinement —— 把多尺度深度/反射率特征按光流 warp 到参考帧
- 多尺度：$j\in\{1,2,4\}$

### 5.3 Cross-Modal Information Fusion (CCAM, Fig.5/6) 【核心】
**CCAM = Convolutional Cross-Attention Module**，灵感来自 CBAM + cross-attention。

通道注意力 / 空间注意力：

$$ \phi_c(\mathcal{F}) = \sigma_s\bigl(\mathrm{MLP}(\mathcal{F}_c^{avg} + \mathcal{F}_c^{max})\bigr),\quad \phi_s(\mathcal{F}) = \sigma_s\bigl(\mathrm{Conv}([\mathcal{F}_s^{avg};\mathcal{F}_s^{max}])\bigr) \tag{12, 13} $$

跨模态 multi-head attention：

$$ \mathrm{head}_c^n = \mathrm{Attention}(Q_c^d W^Q_{n,c},\, K_c^r W^K_{n,c},\, V_c^r W^V_{n,c}),\quad \mathrm{MHA}_c^d(\cdot) = \mathrm{Concat}(\mathrm{head}_c^1, \ldots, \mathrm{head}_c^P)W_o^P \tag{14} $$

其中 $Q_c^d = \phi_c(\mathcal{F}_d^w)$, $K_c^r=V_c^r=\phi_c(\mathcal{F}_r^w)$。
反射率→深度的信息注入：

$$ \mathcal{F}_{d\to r}^w = \sigma(\mathcal{F}_{s,d\to r}^w + \mathcal{F}_{c,d\to r}^w),\qquad \mathcal{F}_{r\to d}^w = \sigma(\mathcal{F}_{s,r\to d}^w + \mathcal{F}_{c,r\to d}^w) \tag{15, 16} $$

由于 timestamp 帧是唯一输入，作者预期**深度→反射率方向**信息流更多（实验印证：仅 2.5%-3.5% 的 metric 提升）。

### 5.4 Progressive Multi-Scale Reconstruction (Fig.9)
- 从最小尺度 $j=4$ 开始：fused 特征 + warped 特征 → 残差网络融合
- **Local Cross-Window Attention** 出当前尺度结果
- 上采样→下一尺度，重复至原分辨率

### 5.5 损失函数

$$ \mathcal{L}_\mathcal{H} = \lambda_1^\mathcal{H} \mathcal{L}(\mathcal{D}^1, \mathcal{H}_{den}^1) + \lambda_2^\mathcal{H} \mathcal{L}(\mathcal{H}_{gt}^1, \mathcal{H}^1) + \lambda_3^\mathcal{H} \mathcal{L}(\mathcal{H}_{gt}^2, \mathcal{H}^2) + \lambda_4^\mathcal{H} \mathcal{L}(\mathcal{H}_{gt}^4, \mathcal{H}^4) + \lambda_5^\mathcal{H} \mathcal{P}(\mathcal{H}_{gt}^1, \mathcal{H}^1) \tag{17} $$

其中 $\mathcal{L}(A,B) = \|A-B\|_1 + \|\nabla_x A - \nabla_x B\|_1 + \|\nabla_y A - \nabla_y B\|_1$；$\mathcal{P}$ 为 LPIPS。

权重：$\lambda^\mathcal{H} = (0.2, 0.85, 0.1, 0.05, 0)$；反射率额外加 $\lambda_5^\mathcal{R}=0.05$。
Adam, lr=1e-4，plateau 衰减 0.5。NVIDIA A100。

## 6. 仿真管线（Section X / Fig.19-21）

| 参数 | 值 |
|------|----|
| Dark counts $C^{dc}$ | 126 Hz |
| 波长 $\lambda$ | 671 nm |
| 大气衰减 $\alpha_{atm}$ | 0.7 dB/km |
| 反射率范围 | [0.0, 1.0] |
| 像元宽/高 | 9.2 μm |
| 暴露时间 | 1000 μs |
| 抖动 $\sigma_j$ | 220 ps |
| 距离 $R$ | 30 m |
| 脉宽 $\sigma_t$ | 1 ns |
| 单脉冲能量 $E_0$ | 1.219 nJ |
| 背景辐照 $W^{bck}$ | 0.0002 W |
| 重复率 $1/t_r$ | 2.25 MHz |
| 深度变化 $z_{i,j}$ | [2 m, 60 m] |
| 量子效率 $\eta$ | 0.18 |

数据来源：
- **I2-2000FPS** 高速 RGB 视频集 (280 段) 提供运动
- **Depth-Anything V2** 单目深度网络生成 ground-truth 深度
- 反射率：RGB 灰度
- 按 SP-LiDAR first-photon 模型 (式 25-31) Monte Carlo 采样 timestamp

训练 / 测试 = 249 / 31。

## 7. 实验结果

### 7.1 仿真定量（Table II，越大越好 / 越小越好已标）

| 方法 | Reflectivity PSNR↑ | SSIM↑ | Depth RMSE↓ |
|------|---:|---:|---:|
| FPAMU [12]   | 9.26 | 0.069 | 0.0346 |
| PEINN [14]   | – | – | 0.0121 |
| SPDSF [15]   | – | – | 0.0136 / 0.0141 |
| BPRNN [16]   | 15.68 | 0.417 | 0.0147 |
| QUIVER [42]  | 22.12 | 0.670 | – |
| RVRT  [69]   | 21.87 | 0.544 | – |
| FloRNN [70]  | 20.11 | 0.567 | – |
| MemDeblur [67] | 19.81 | 0.477 | – |
| Spk2ImgNet [68] | 20.15 | 0.572 | – |
| **SPLiDER**  | **23.03** | **0.6895** | **0.0077** |

定性（Fig.10, 12）：SPLiDER 在低光子像元不出虚假深度，反射率细节最清晰；BPRNN 反射率过度平滑；其他视频复原算法在低 SBR 下细节丢失。

### 7.2 真实数据
- 传感器：128×192 SPAD @1000 fps（参考文献 [63] Henderson 2019 *192×128 TCSPC SPAD in 40-nm CMOS*）
- 光源：Picoquant LDH 670 nm 皮秒激光，1 nJ/脉冲，25 MHz，有效脉宽 ≈ 1 ns
- TDC 分辨率 ≈ 35 ps
- 场景：白色背景的室内动态目标（旋转扇 / 挥手），白板雕像
- 结果（Fig.13）：现有 3D 重建因低光子计数产生虚假深度，SPLiDER 抑制；反射率细节比 video-only 方法更锐利

### 7.3 消融（Table III）
| Optical-Flow | CCAM | Reflec PSNR | SSIM | Depth RMSE |
|:---:|:---:|---:|---:|---:|
| ✗ | ✗ | 21.69 | 0.6610 | 0.0092 |
| ✗ | ✓ | 22.24 | 0.6715 | 0.0084 |
| ✓ | ✗ | 22.01 | 0.6698 | 0.0079 |
| **✓** | **✓** | **23.03** | **0.6895** | **0.0077** |

- CCAM 单独引入：约 +0.5 dB；
- 光流单独引入：约 +0.3 dB；
- 两者联合：+1.3 dB —— 表明跨模态共享与时序对齐是**互补**的，不是冗余的。

## 8. 与 [robust_3D_imaging_obscurant_SP_LiDAR_2021_中文整理] 的对照

| 维度 | M2R3D (Tobin 2021) | SPLiDER (Weerasooriya 2025) |
|------|------|------|
| 场景 | 雾霾 / SWIR 远距 | 高速运动 / 普通可见光 |
| 输入 | 3D 直方图立方 + 多帧 | **单帧 timestamp 序列** |
| 方法基础 | 分层贝叶斯 + 多尺度 | 深度学习 + 跨模态注意力 |
| 联合 | 同时估深度+反射率 | 同时估深度+反射率 |
| 时序 | 多帧先验 | 双向光流 + STAR |
| 不确定度 | 给后验 std | 不提供 |
| 实时性 | ~10 fps Matlab CPU | A100 GPU |
| 关键贡献 | 工程 + 鲁棒模型 | **理论 (CRLB) + 网络架构** |

## 9. 对 TOF3.0 项目的可借鉴点

1. **理论层面**：在自家算法（如 M2R3D 改进或 Nezha 雾天版）里，**联合估计深度和反射率比分开估计更优**（前提：背景 $b_\lambda > 0$）。这给现有“先估深度再估反射”的流水线一个明确的理论替代方案。
2. **数据组织层面**：跳过 3D histogram 直接处理 timestamp 帧，能避免运动模糊——对 RK3568 端的实时帧率（车载/动态场景）非常重要。
3. **网络架构层面**：CCAM 是 CBAM + cross-attention 的简洁组合，**两个分支共享通道+空间注意力，仅 1 个 attention head 即够用**。可以放进 ml_offline 的 baseline 对比。
4. **仿真数据策略**：用 `I2-2000FPS` + `Depth-Anything V2` 合成高速 SP-LiDAR 时间戳数据，是个低成本扩充训练集的思路（research/sim_spad_loader.py 可以扩展）。
5. **CRLB 当作算法天花板**：式 (7)(9)(10) 直接可用——给 TOF3.0 现有算法做评估时，可以画 “MSE vs SBR” 与 CRLB 比较，作为研究路线图的客观指标。
6. **鲁棒求解的两个算法**（Alg.1 双向括号 + Alg.2 二分法）是低复杂度、可写进嵌入式 C 代码的 estimator，无需深度学习即可在 RK3568 上跑。
7. **运动场景实时性结论**：单帧每像元 ≤1 光子时，深度/反射率必须靠多帧时序融合 + 跨模态共享才能撑住；这与 M2R3D 多时序的思路殊途同归。

## 10. 主要参数 (Sim Tab.V) 速查

```
λ = 671 nm    σ_t = 1 ns   σ_j = 220 ps   t_exp = 1000 μs
1/t_r = 2.25 MHz   N_r·Λ ≈ 10 photons/frame
SBR ∈ {0.5, 1, 2, 5, 10}   反射率 α ∈ [0, 1]
深度 z ∈ [2, 60] m   暗计数 126 Hz   η = 0.18
```

---

*中文整理：聚焦理论（CRLB）、网络（CCAM/STAR）与对 TOF3.0 的可迁移点；公式编号对齐原文；arXiv 预印本，研究/学习用途；所有定量数字来自原文 Table II/III。*
