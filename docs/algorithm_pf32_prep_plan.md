# PF32 算法准备工作计划（基于 Gutierrez 数据集）

> 目的：在 PF32 实机到来前，把"算法 vs 雾 / 累加 / 分辨率 / 方向"四个维度
> 在公开数据集上量化测过，PF32 来的当天直接拿数据决策。
>
> 主要产出：**每阶段一张/几张图表**（PNG），数字辅助；少写 Markdown 长表。
> 图统一放 `research/out/pf32_prep/`，每张配 ≤200 字标题/解读，钉进本文档。
>
> 与 `algorithm_research_roadmap.md` 关系：roadmap 是算法层级展开（Level 0–5），
> 本计划是按"PF32 实机迁移最 ROI"挑出来的执行顺序。

---

## 总体顺序与产出

```
A baseline 补全 (0.5d)
  └─ research/out/pf32_prep/A_baseline_grid.png

B 多帧累加曲线 (0.5d)
  └─ research/out/pf32_prep/B_accumulation_curves.png

C reverse 方向回归 (0.5–1d)
  └─ research/out/pf32_prep/C_reverse_parity.png

D 32×32 binning 模拟 (1d)
  └─ research/out/pf32_prep/D_binning_compare.png

E 雾注入退化曲线 (1.5d，PF32 核心)
  └─ research/out/pf32_prep/E_fog_sweep.png

F 算法 spec + profile (0.5d，可选)
  └─ research/out/pf32_prep/F_runtime_profile.png + docs/algorithm_pf32_spec.md
```

每阶段独立，可单独跑、单独看图。

---

## 阶段 A — Phase A baseline 补全

**为什么先做**：所有后续阶段都要在"5 样本 × 8 算法"的全表上跟 baseline 对比，
当前 `verify_baseline.md` 只有 5 个算法（缺 lmf_spad/spatial_3x3/tail_bg），先补齐。

**步骤**：

- **A1** `algorithms/lmf.py` 支持加载真 IRF（`research/datasets/PSF_64x64.mat`），
  保留 Gaussian 近似 fallback。两种模式都跑。
- **A2** `run_sanity.py` / `run_verify_baseline.py` 加 `tail_bg_argmax` 列。
- **A3** 全表数据写入 CSV：`research/out/pf32_prep/A_baseline.csv`
  （5 样本 × 8 算法 × 4 容差 hit + RMSE）。
- **A4** 出图 `A_baseline_grid.png`：
  - 左：每算法在 5 样本上的 hit@200mm 散点 + 均值横线
  - 右：每算法 RMSE 箱形图
  - 颜色按"我们实现 vs 数据集自带"区分

**通过条件**：lmf_real_irf 应 ≥ Gaussian σ=2.5（差距 ≤2pp 就算高斯近似够用，
不必再 per-column IRF）；tail_bg_argmax 在 high-SBR 样本上 ≥ argmax_spad。

---

## 阶段 B — 多帧累加曲线（路线图 Step 5）

**给 PF32 的答案**：实机采集要积多少帧才能让 argmax 达到 X% 命中。

**步骤**：

- **B1** `run_accumulation.py` 5 样本 × K∈[1,2,4,8,16,32,64] × 3 trials × 8 算法。
- **B2** 写 CSV：`research/out/pf32_prep/B_accumulation.csv`。
- **B3** 出图 `B_accumulation_curves.png`：
  - 上：hit@200mm vs K（log2 x 轴），5 样本均值 + 阴影标 std；每算法一条线
  - 下：RMSE vs K
  - 横向参考线：argmax_rates 上界、ds_lmf 水平
- **B4** 写一段 ≤200 字结论钉到本文档（"K=N 时 argmax 达到 Y% 水平"）。

---

## 阶段 C — reverse 方向回归

**为什么必做**：PF32 是 reverse，`tail_bg_argmax` 当前取末端 100 bin，
在 reverse 下 = 雾峰最强处，必崩。

**步骤**：

- **C1** `algorithms/tail_bg_argmax.py` 加 `tail_side: "far"|"near"|"auto"`，
  auto 按 `sample.start_stop` 自动选末端（forward=尾、reverse=首）。
- **C2** 新增 `research/run_reverse_parity.py`：加载 5 样本，对每个：
  - 跑 forward 所有算法 → depth_mm_fwd
  - 人工翻 hist（`hist[..., ::-1]`）+ start_stop="reverse" → 跑算法 → depth_mm_rev
  - 期望两者深度图逐像素相等
- **C3** 写 CSV `C_reverse_parity.csv`（每算法 forward-vs-reverse 像素一致率）。
- **C4** 出图 `C_reverse_parity.png`：每算法 forward/reverse 一致率柱状图，
  100% 为绿、<100% 为红（红柱即 PF32 上会踩 bug 的算法）。

---

## 阶段 D — 32×32 binning 模拟（PF32 分辨率对齐）

**给 PF32 的答案**：分辨率减半 + 光子 ×4 净效果到底是赚是亏。

**步骤**：

- **D1** `sim_spad_loader.py` 加 `SpadSample.bin_spatial(k=2)` 方法
  （H/W 各 2×2 求和，depth_mm/intensity 同步降采样取中心或均值）。
- **D2** 新增 `research/run_binning_compare.py`：5 样本 × 8 算法 × {64×64, 32×32}。
- **D3** 写 CSV `D_binning.csv`。
- **D4** 出图 `D_binning_compare.png`：
  - 左：8 算法在 64×64 vs 32×32 binning 上的 hit@200mm 配对图
  - 右：深度图视觉对比（选 1 样本，64×64 / 32×32 binning / GT 三栏）

**通过条件**：得到明确答案——argmax/spatial 在 32×32 上是否值得替换主算法。

---

## 阶段 E — 雾注入退化曲线（路线图 Step 6，PF32 核心）

**步骤**：

- **E1** 移植 `tof_process.depth_separate` 到 `algorithms/sep_argmax.py`：
  - 统一 `estimate(sample, cfg)` 接口
  - 向量化（去掉双重 for 循环；32×32 OK 但 64×64 慢）
  - 雾参数（暗本底分位数 / 中值滤波窗 / find_peaks prominence）放 dataclass cfg
- **E2** 新增 `research/run_fog_sweep.py`：
  5 样本 × 雾档 {clear, light, medium, dense} × 9 算法 × {K=1, K=16 累加}。
- **E3** 写 CSV `E_fog_sweep.csv`。
- **E4** 出图 `E_fog_sweep.png`：
  - 4 个子图（每个雾档一个），x=算法、y=hit@200mm 均值 + 个样本散点
  - 子图标题写该雾档的 Koschmieder 能见度
- **E5** 写结论钉本文档（"中雾下 sep_argmax 优于 lmf X%，浓雾下全员崩盘"）。

---

## 阶段 F — 算法 spec + profile（可选）

依赖 A–E 全部完成。

- **F1** `research/run_profile.py`：每算法 64×64 单帧执行时间，3 次平均。
- **F2** 出图 `F_runtime_profile.png`：横轴算法、纵轴 ms，2fps 线（500ms）标红。
- **F3** 写 `docs/algorithm_pf32_spec.md`：根据 A–E 数据选 2–3 个保留算法，
  写明输入输出契约、参数默认值、典型实测数字——为 C 端移植做准备。

---

## 共用约定

### 图表风格

- matplotlib，`MPLBACKEND=Agg`，DPI 150
- 中文用 `plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "sans-serif"]`，
  装不到中文字体就用英文（图标题/轴标都给一份英文版备份）
- 颜色：我们实现的算法用蓝色系，数据集自带（ds_*）用灰色系，上界（rates）用红虚线
- 5 样本散点 + 均值横线是标配——单点数字不可推广（roadmap §二.4 教训）

### 输出位置

- 图：`research/out/pf32_prep/<阶段>_<名称>.png`
- 数据 CSV：`research/out/pf32_prep/<阶段>_<名称>.csv`
- 入口脚本：`research/run_<阶段名>.py`（不已存在则新建）

### 数据规模

- 5 样本是钉锚点的最小集；要做"全集 SBR 分层"用现有 `run_benchmark.py`
- 单样本 64×64 LMF 约几十 ms；5 样本 × 8 算法 × 4 雾档 × K∈[1..64] 总跑约 5–10 min，可接受

---

## 进度跟踪（实时更新）

| 阶段 | 状态 | 完成时间 | 图表链接 |
|------|------|----------|----------|
| A baseline 补全 | ✅ | 2026-05-28 | `A_baseline_grid.png`（统计）+ `A_depth_grid.png`（深度图视觉对比） |
| B 多帧累加 | ✅ | 2026-05-28 | `B_accumulation_curves.png`（hit/RMSE vs K 曲线） |
| C reverse 回归 | ⬜ | — | — |
| D 32×32 binning | ⬜ | — | — |
| E 雾注入退化 | ⬜ | — | — |
| F profile + spec | ⬜ | — | — |

### A 阶段实测结论（2026-05-28，5 样本均值）

| 算法 | hit@12 | hit@24 | hit@60 | hit@200 | RMSE |
|------|--------|--------|--------|---------|------|
| argmax_spad     | 0.317 | 0.477 | 0.568 | 0.579 | 1816 |
| lmf_gauss σ=2.5 | 0.490 | 0.590 | 0.626 | 0.637 | 2236 |
| lmf_real        | 0.420 | 0.575 | 0.626 | 0.636 | 2186 |
| lmf_real_pc     | 0.414 | 0.570 | 0.626 | 0.636 | 2188 |
| **spatial_3x3** | 0.351 | 0.499 | 0.624 | **0.719** | **1379** |
| tail_bg_argmax  | 0.317 | 0.477 | 0.568 | 0.579 | 1816 |
| ds_argmax       | 0.408 | 0.522 | 0.568 | 0.580 | 1815 |
| ds_lmf          | 0.417 | 0.550 | 0.618 | 0.633 | 2359 |
| ds_zncc         | 0.415 | 0.546 | 0.616 | 0.631 | 2383 |

**核心发现**：

- **PF32 用 LMF 直接选 Gaussian σ=2.5 即可**：lmf_real / lmf_real_pc 与 lmf_gauss 在 hit@200mm 上差异
  ≤ 0.1pp，且 lmf_gauss 在严格容差（hit@12）反胜 7pp。原因：Gutierrez 真 IRF 全局均值等效
  σ≈2.15 bins，跟 σ=2.5 高斯近重合；per-column 各列 IRF 在峰 bin 6 ± 1 共享，差异都在 tail bins。
- **spatial_3x3 是当前最强单帧算法**：hit@200mm = 0.719 > lmf 0.637 > argmax 0.579。低 SBR
  低光子下 9 邻域光子聚合（SNR ×3）比 IRF 匹配（SNR ×~4 但在 N≈2 时容易拟合噪声）更有效。
- **tail_bg_argmax 与 argmax 数学等价（在无雾数据上）**：减均匀常数不改 argmax 位置。其价值
  必须到阶段 E 雾注入（非均匀背景）才能验证。
- **我们的 LMF 实现是干净的**：lmf_real hit@200 0.636 ≈ ds_lmf 0.633；hit@12 0.420 > ds_lmf 0.417
  （没有 ds_lmf 已知的循环 padding bug "max bin 可达 1031"）。

**视觉对比图 `A_depth_grid.png` 的额外发现**（深度图直接看比数字更直观）：
- **spatial_3x3 视觉优势远大于数字**：是 9 列里唯一保留空间连续性的算法，其他算法（含 LMF）满是
  椒盐噪声，视觉上像噪点图。干净深度图对后续中值/双边滤波 / 后处理友好。
- 最难场景 `home_office_0006`（远距 + 低 SBR）：所有算法都崩，**仅 spatial_3x3 还能看出大致结构**
- 最易场景 `office_0002c`（近距人物）：人形轮廓所有算法都识别得出（hit@200 全员 ≥ 0.95）

**对 PF32 算法选型的初步影响**：
- 候选保留：argmax（C 端基线）+ lmf_gauss + spatial_3x3
- 候选淘汰：lmf_real / lmf_real_pc（无显著增益，部署多带一个 PSF 文件）、tail_bg_argmax（在无雾无收益，待 E 复测）

### B 阶段实测结论（2026-05-28，5 样本 × 3 trials 物理累加）

| K | argmax | lmf_gauss | spatial_3x3 | tail_bg |
|---|---|---|---|---|
| 1 | 60.5% | 73.7% | **87.0%** | 60.5% |
| 2 | 73.9% | 85.0% | **93.2%** | 73.9% |
| 4 | 85.9% | 94.0% | **95.8%** | 85.9% |
| 8 | 94.1% | **99.0%** | 96.5% | 94.1% |
| 16 | 99.1% | **100%** | 96.7% | 99.1% |
| 32 | 100% | 100% | 96.7% (卡顶) | 100% |
| 64 | 100% | 100% | 96.7% (卡顶) | 100% |

**核心发现**：

- **spatial_3x3 是 K≤4 之王，K≥8 被 lmf 反超且卡顶 96.7%**——空间池化牺牲的边缘像素
  分辨率永久不可恢复，无论累加多少都救不回那 3.3% 边缘
- **lmf_gauss 在 K≥8 全员 ≥99%**——累加足够时匹配滤波是最优解
- **tail_bg 全段与 argmax 重合**（数学等价已验证）
- **物理累加 K=1 比真实 spad K=1 偏乐观 +3..+15pp**（合成模型用的 Gaussian IRF 比真实窄；
  绝对数字看 A 的真实 spad 结果，趋势看 B 的合成曲线）

**PF32 工程"积多少"的直接答案**（PF32 假定 2fps）：

| 目标 hit@200mm | spatial_3x3 | lmf_gauss | argmax |
|---|---|---|---|
| 90% | K=2 (~1 秒) | K=4 (~2 秒) | K=8 (~4 秒) |
| 95% | K=4 (~2 秒) | K=4 (~2 秒) | K=16 (~8 秒) |
| 99% | 达不到（卡 96.7%） | K=8 (~4 秒) | K=16 (~8 秒) |

**PF32 算法选型更新**：
- 实时性最高时（1-2 帧）→ spatial_3x3
- 准确性最高时（≥8 帧）→ lmf_gauss
- 两个都需保留（互补）；argmax 作为基线参考
