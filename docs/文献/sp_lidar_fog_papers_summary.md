# Single-Photon LiDAR 透雾与低 SBR 重建论文总结

本文总结两篇与本项目 PF32 32x32 SPAD ToF 系统相关的重点文献。技术术语保留英文，便于后续算法实现时对应原文。

## 1. Robust real-time 3D imaging of moving scenes through atmospheric obscurant using single-photon LiDAR

### 基本信息

- 标题：Robust real-time 3D imaging of moving scenes through atmospheric obscurant using single-photon LiDAR
- 作者：Rachael Tobin, Abderrahim Halimi, Aongus McCarthy, Philip J. Soan, Gerald S. Buller
- 发表年份：2021
- 期刊/会议：Scientific Reports, 11, 11236
- DOI：https://doi.org/10.1038/s41598-021-90587-8

### 核心问题

论文解决的是在雾、烟、油雾等 atmospheric obscurant 中，Single-Photon LiDAR 的回波直方图会被强 backscatter 和非均匀 background 严重污染，传统 matched filter / cross-correlation 容易把雾峰或背景当成目标峰，且很多高质量重建算法运行时间较长，难以用于 moving scenes 的实时 3D 成像。

### 方法概述

- 使用 32x32 InGaAs/InP SPAD array 和 1550 nm pulsed fibre laser，在 50 m 和 150 m stand-off range 下采集 TCSPC histogram cube；1550 nm 属于 SWIR，在该油雾环境下比可见光衰减更低，同时眼安全功率余量更大。
- 建立 obscurant-aware observation model：每个 pixel 的 histogram 被建模为 Poisson 分布，包含目标回波 `r * IRF(t - d)` 与随 time-of-flight 变化的非均匀 background。background 近似为 exponential tail 加 constant floor，用于描述雾/烟 backscatter。
- 提出 M2R3D（Median-based Multi-scale Restoration of 3D images）算法：先估计并扣除 background 参数，再用 hierarchical Bayesian / MAP 框架联合估计 depth 与 reflectivity/intensity。
- M2R3D 同时利用 multiscale spatial correlation 和 multi-temporal information；核心优化交替执行 robust non-linear parameter estimation（weighted median）和 filtering（generalised soft-thresholding）。
- 算法输出 depth 的同时给出 uncertainty estimate，可定位高雾密度、物体边缘等不可靠区域；还提供可选 super-resolution，把 32x32 数据恢复为 128x128 depth profile。

### 关键结论

- 在 50 m indoor 场景中，M2R3D 可在 4.5 attenuation lengths 下完整重建 3D panel target，在 5.0 和 5.5 attenuation lengths 下仍可部分重建；传统 cross-correlation 即使加入 histogram/background correction，效果也明显较弱。
- 对 5.0 attenuation lengths 的 50 m 数据，depth absolute error 阈值 5.6 cm 下的 true positive percentage：无修正 cross-correlation 为 1%，仅 histogram correction 为 0%，加入 exponential background 的 cross-correlation 为 35%，M2R3D 为 75%。
- 在 150 m outdoor daylight 场景中，系统可在约 4.5 attenuation lengths 下对固定板和 moving actor 做 depth/intensity profiling。
- M2R3D Matlab 实现约 90 ms/frame，已达到接近实时；论文认为通过 GPU/parallel processing 可进一步压到数毫秒级。
- 论文明确指出 obscurant 场景的关键不是简单提高 photon count，而是正确建模非均匀 background，并在低 SBR 下利用空间、时间和统计先验提高稳健性。

### 与本项目的关联

- 本项目同样是 32x32 SPAD ToF，并且目标是低 SBR 透雾/遮挡场景；该论文的硬件规模与本项目 PF32 非常接近，算法假设和工程约束有直接参考价值。
- PF32 为 55 ps/bin，时间分辨率高于论文系统的 250 ps/bin；这有利于更精细地区分目标峰和雾 backscatter，但也意味着 histogram bin 数更多、噪声分布更稀疏，算法上更需要 background model 和 robust peak selection。
- 本项目已记录 PF32 reverse start-stop：雾峰在高 bin 端，目标峰在低 bin 端。M2R3D 的 exponential tail background 思路可迁移，但实现时要按 PF32 bin 方向重写 background profile，而不能直接照搬原论文的 time axis。
- 可优先借鉴三点：一是先估计 background，再做目标峰估计；二是输出 uncertainty/confidence，供后续 RK3568 显示和闭环控制过滤低可信像素；三是利用 multi-temporal 信息，在实时帧间平滑中保持 moving target 边缘。
- 对当前 P9 算法管道，M2R3D 可作为传统物理基线的高质量目标：先实现 exponential/Gamma background subtraction + robust weighted median peak，再逐步加入 spatial/multitemporal regularization。

## 2. Joint Depth and Reflectivity Estimation using Single-Photon LiDAR

### 基本信息

- 标题：Joint Depth and Reflectivity Estimation using Single-Photon LiDAR
- 作者：Hashan K. Weerasooriya, Prateek Chennuri, Weijian Zhang, Istvan Gyongy, Stanley H. Chan
- 发表年份：2025
- 期刊/会议：arXiv:2505.13250
- 版本日期：2025-05-19

### 核心问题

论文解决的是动态场景下 SP-LiDAR 传统 3D histogram cube 需要较长 integration time，容易因物体运动产生 blur；同时已有方法通常把 depth 和 reflectivity 分开估计，忽略 timestamp 同时编码飞行时间和反射强度这一事实。论文希望直接从 individual timestamp frames 中联合恢复 depth 与 reflectivity，在低 photon count 和 fast-moving scenes 下提升重建质量。

### 方法概述

- 先从理论上分析 depth 与 reflectivity 的互补关系：在 Poisson photon arrival model 下推导 joint MLE 和 CRLB，说明有 reflectivity 先验可帮助 depth estimation，有 depth 信息也可降低 reflectivity estimator 方差，尤其在低 SBR 时收益更明显。
- 提出 SPLiDER（Single Photon LiDAR joint Depth and Reflectivity），直接处理多个 individual timestamp frames，而不是先长时间累积成 3D histogram cube。
- 网络采用双分支结构分别提取 depth features 与 reflectivity features，并通过 CCAM（Convolutional Cross-Attention Module）做 cross-modal feature sharing。
- 为处理动态场景，SPLiDER 使用 optical flow 对相邻 timestamp frame 的特征进行 bidirectional alignment，避免简单累积带来的运动模糊。
- 网络包含 hybrid feature extraction、bidirectional flow estimation + feature alignment、cross-modal information fusion、progressive multi-scale reconstruction，最终同时输出 depth 和 reflectivity。

### 关键结论

- 合成数据上，SPLiDER 在 reflectivity 和 depth 两类指标上都优于多种 SP-LiDAR baseline 与 video reconstruction baseline；论文表格中 SPLiDER 达到 reflectivity PSNR 23.0260、SSIM 0.6895、depth RMSE 0.0077。
- 与 BPRNN 等基于 3D histogram cube 的方法相比，SPLiDER 对低 photon level 下的 spurious depth estimation 更稳健，且不会因长 integration time 明显牺牲动态场景清晰度。
- 真实数据使用 128x192 SPAD sensor、1000 fps timestamp frames、670 nm picosecond pulsed laser；结果显示 SPLiDER 在低 photon count 场景下能减少错误深度点，并恢复更细的 reflectivity detail。
- Ablation study 表明 optical flow alignment 和 CCAM 都有贡献；二者同时使用时效果最好：reflectivity PSNR/SSIM 从 21.6954/0.6610 提升到 23.0260/0.6895，depth RMSE 从 0.0092 降到 0.0077。

### 与本项目的关联

- 本项目当前数据链路已经实时输出 32x32 depth frame，但原始 TCSPC histogram 只在哪吒本地保存。该论文提示：若后续要做动态场景和 ML 重建，不应只依赖长时间累积 histogram，也应保留按短 exposure/帧组织的 timestamp 或 histogram slice。
- 对 PF32 32x32、55 ps/bin、低 SBR 场景，joint depth/reflectivity 是有价值的：reflectivity 可作为目标回波可信度、材质/反射强度和雾背景区分的辅助通道，depth 也能反过来约束 reflectivity，避免仅按 photon count 把背景雾散射误判为目标反射。
- SPLiDER 是深度学习方法，直接部署到哪吒 N97 或 RK3568 并不现实，适合作为 `ml_offline/` 训练方向；在线侧可先借鉴其思想，设计轻量的 dual-output estimator，同时输出 depth、intensity/reflectivity、confidence。
- 论文的 individual timestamp frame 思路与本项目“实时显示即弃、raw TCSPC 本地存档”的架构需要进一步衔接：建议在 `.tch` 或后续 session manifest 中记录 exposure/frame grouping、bin direction、laser repetition 等元数据，避免离线训练时只能得到大窗口累计直方图。
- 对透雾算法而言，SPLiDER 没有专门建模 fog backscatter；它更适合补充 M2R3D：M2R3D 提供 obscurant-aware physical/statistical model，SPLiDER 提供动态场景下 timestamp-level joint reconstruction 和 depth/reflectivity feature sharing 思路。

## 综合启发

- 传统基线优先级：先做 obscurant-aware background estimation，再做 peak/depth estimation；不要把 argmax 或 matched filter 作为低 SBR 透雾场景的最终方案。
- 输出不应只有 depth：建议算法层统一输出 depth、reflectivity/intensity、valid/confidence/uncertainty，供显示、录制、闭环控制和后续 ML 训练共用。
- 对 PF32 reverse start-stop 要特别小心：所有 background profile、fog peak、target peak、bin-to-distance 公式都必须显式带 `bin_direction`，否则很容易把雾峰和目标峰方向写反。
- 短期可实现路线：`background subtraction -> robust peak/weighted median -> spatial/multitemporal regularization -> confidence map`；中长期 ML 路线再引入 timestamp-frame feature sharing 和 joint depth/reflectivity reconstruction。
- 真实数据采集时应同步保存 raw TCSPC、depth frame、reflectivity/intensity、系统 IRF、bin size、gate window、laser power、fog/scene metadata；这些字段会直接决定 M2R3D 类物理方法和 SPLiDER 类 ML 方法能否复现。
