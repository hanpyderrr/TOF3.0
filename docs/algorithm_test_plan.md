# 算法测试方案

> **范围:算法研究态**。不依赖 PF32 硬件,不为工程时延/INT8/32×32 让步。
> 先在公开数据上把"目标—雾分离"研究到底,收敛后再做**工程化降级**对接 PF32 系统(见末尾 §工程化降级)。
> **配套文档:** 代码组织/接口契约见 `docs/algorithm_code_architecture.md`。

## 四阶段路径

```
阶段 1 (1-2 周)  基线管道打通  ──► Gutierrez 无雾 + 现有 tof_process 跑 sanity
阶段 2 (2-3 周)  雾注入对比    ──► 多雾模型 × 多算法版本,出"算法被骗"曲线
阶段 3 (1-2 周)  跨数据集泛化  ──► Adaptive Gating Leaf / Middlebury / 自造场景
阶段 4 (周期长)  真雾 hold-out ──► 写邮件申请 Heriot-Watt Buller 雾数据,平行启动
```

阶段 1-3 全部本机仿真/公开数据,**完全不依赖 PF32 到位**。

## 代码位置

> ⚠️ **路径说明**：算法研究已于 2026-05-27/28 从 `nezha/algorithm/` 整体迁移到 `research/`。

算法研究统一放 `research/`（原 `nezha/algorithm/`，PF32 工程化对接相关不在本期范围）。

```
research/
├── tof_sim.py          v1 原型 (留原地,作 baseline)
├── tof_process.py      v1 处理 (留原地)
├── sim_spad_loader.py  Gutierrez 数据加载器
├── inject_fog.py       跨雾模型注入工具
├── datasets/           公开数据本地缓存 (.gitignore)
└── eval/               [新] 算法对比 + 出图
```

---

## 阶段 1 — 基线管道打通

### 1.1 数据来源

| 来源 | 类型 | 维度 | 雾 | 获取 | 用途 |
|------|------|------|-----|------|------|
| **Gutierrez ICCV 2023 SimSPADDataset** | NYUv2 仿真 | 64×64×1024 @ 55/60/80ps | ❌(自注) | Google Drive(需代理) | **主力** |
| Adaptive Gating "Leaf" (CMU) | 真实 SPAD,1 场景 | 不明 | ❌ | Dropbox | 真实噪声 sanity |
| Lindell 2018 "additional data" | NYUv2 仿真 | 可配 | ❌ | Google Drive | 仿真器源头对照 |
| PF32 厂家 samples (`refs/pf32/samples/`) | **仅代码示例,无真实 .tch** | — | — | 仓库自带 | 仅 API 参考 |
| Heriot-Watt Buller 真雾 | 真实 32×32 InGaAs + 油雾 | 32×32×? | ✅ | ⚠️ 邮件申请 | 阶段 4 hold-out |

### 1.2 关键约定(本期算法研究态)

- **维度保留 Gutierrez 原始 64×64×1024**——不 downsample 到 PF32 32×32
- **Start-stop 用 Gutierrez 原向(正向)**——bin 越大 = 距离越远;不为 PF32 反向 flip
- **算法 loader 内部加 `start_stop='forward'|'reverse'` 参数**,默认 forward;工程化降级阶段切 reverse
- 距离公式:`depth_mm = bin_index × 55ps × c/2 ≈ bin × 8.243mm`(正向)
- dtype 用 float32(`spad` 字段,稀疏计数),不为 PF32 uint16 让步

### 1.3 通过条件

无雾基线跑 `tof_process.depth_argmax`:
- depth RMSE < 50mm
- hit_rate(|err|<200mm) > 95%
- (Gutierrez 含 Poisson 噪声/有限 SBR,不强求 99%)

跑不到 = loader 有 bug(transpose 错 / bin 方向错),debug。

### 1.4 落地脚本

| 文件 | 状态 |
|------|------|
| `nezha/algorithm/sim_spad_loader.py` | 加载 .mat → (64,64,1024) float32 + depth_gt + metadata |
| `nezha/algorithm/eval/baseline_sanity.py` | 跑无雾 argmax,出 RMSE/hit_rate |

---

## 阶段 2 — 雾注入对比

### 2.1 雾注入工具 `nezha/algorithm/inject_fog.py`

| model | 数学形式 | 用途 |
|-------|----------|------|
| `gamma` | Γ 分布散射剖面 `β · r^(k-1) · exp(-α·r)` | **训练用**(文献 10 火箭军) |
| `lognormal` | `β · exp(-(ln r - μ)²/2σ²)/r` | 测试用(文献 07,算法不知) |
| `exponential` | `β · exp(-2α·r) / (r² + r₀²)` | 你现 `tof_sim.py` 的简化模型 |
| `mie_lite` | Mie 近似 + 目标峰展宽/拖尾 | 测试用(文献 16) |

每 model 三档:`light` / `medium` / `dense`(能见度 5m / 3m / 1m 级)。
注雾后保留 metadata `(fog_model, fog_level, α, β, peak_bin)`,评估时关联。

### 2.2 算法对照矩阵

| 算法 | 描述 | 状态 |
|------|------|------|
| `depth_argmax` | baseline | 现有 |
| `depth_separate` v1 | 中值雾包络扣除 + matched filter | 现有 `tof_process.py` |
| `depth_separate` v2 | Gamma 拟合扣雾 + DBSCAN 残差 + Gaussian | 待写 |
| `depth_separate` v3 | v2 + Level 1 邻域加权累加 | 待写 |
| `depth_separate` v4 | v3 + Skewed Gaussian 目标峰拟合 | 待写 |

算法实现**充分可微**(若走 ML 路线),不为 INT8 量化让步。

### 2.3 出图

- **图 A**:命中率 vs 距离,分雾浓度(3×4 网格:雾档 × 算法)
- **图 B**:训练用雾模型 × 测试用雾模型矩阵,看跨模型掉分(过拟合 vs 真鲁棒)
- **图 C**:Q 四元组分布,分算法

### 2.4 通过条件

- v2 在中雾 medium 距离 4-5m 命中率 > 95%(对标火箭军论文 96%)
- v3 在 dense 雾边界距离 > v2 命中率 ≥ 5 pp
- 跨雾模型(训练 gamma,测试 lognormal/mie)掉分 < 15 pp

---

## 阶段 3 — 跨数据集泛化

追加:

| 来源 | 类型 |
|------|------|
| Adaptive Gating Leaf (CMU) | 真实 SPAD 单场景 |
| Middlebury 2014 + 自仿真 | 室外/复杂几何,深度 GT |
| 升级版 `tof_sim` 自造 | 球+墙+步骤+棋盘,已知 GT 边界 case |

跨数据集 RMSE 矩阵:训练源 × 测试源 4×4。对角线最好,非对角看泛化。

---

## 阶段 4 — 真雾数据 hold-out

**邮件已起草、即时发送**(回复周期 2-8 周,跟代码并行)。
候选收件人:
- Prof. Gerald S. Buller — `G.S.Buller@hw.ac.uk`(Heriot-Watt 单光子组)
- Dr. Abderrahim Halimi — `A.Halimi@hw.ac.uk`(算法主作)

回复来后跑阶段 2 算法对它,**真实雾 RMSE 是论文最有说服力的一行**。

---

## 评估指标体系

```python
# per-pixel (事后评估,不当 ML loss)
depth_RMSE_mm
hit_rate                          # |depth - GT| < 200mm
Q_tuple = (SBR, peak_FWHM_bins, peak_skewness, residual_energy)

# per-frame
valid_pixel_ratio
depth_smoothness

# per-dataset
hit_rate vs distance × fog_level (2D 网格)
cross-fog-model 矩阵
```

**Q 仅作评估**——ML 训练 loss 任算法选(L1+SSIM / 对数似然 / EM 似然 / GAN discriminator 都行),不强求与 Q 一致。
"Q 一致"是**工程化降级**阶段才需要的对齐(闭环 reward 要用 Q)。

---

## MVP — 这一阶段先做的

1. 装 `gdown`(Clash 7890 代理),从 Google Drive 下 `SimSPADDataset_min`(轻量)→ `nezha/algorithm/datasets/`
2. `sim_spad_loader.py` 写好,跑通 sanity:无雾 argmax hit_rate > 95%
3. `inject_fog.py` 实现 Gamma 一种,跨雾档跑现有 v1 看掉到多少
4. 邮件发出(申请真雾)
5. v2 算法实现(Gamma+DBSCAN+Skewed),跨雾模型测试

不在 MVP 范围内的:
- `start_session.sh`/`raw_recorder`/`ml_runtime` 等工程化对接 → 阶段 4 之后
- 32×32 适配、INT8 量化、ONNX 导出、C 移植 → 工程化降级阶段

---

## 工程化降级(算法收敛后,本期不做)

算法 paper-grade 收敛后(v3/v4 命中率达标),挑一版做工程化降级:

```
[算法研究形态]                      [工程化形态]
PyTorch GPU / 64×64 / fp32   ──►   ONNX CPU / 32×32 / INT8
任意模型大小                  ──►   <10MB,<50ms/帧
任意 loss                     ──►   Q 四元组对齐 reward
正向 start-stop               ──►   反向 (PF32 适配)
公开数据集为主                ──►   PF32 真实采集为主
```

降级步骤:
1. 算法层加 `start_stop='reverse'` 适配 PF32
2. spatial 适应 32×32(`spatial_pool=2`)
3. 关键算子用 numpy/C 重实现,保留 PyTorch 版作对照
4. ONNX 导出 + INT8 量化 + ORT CPU benchmark
5. 接入 `nezha/ml_runtime/`(届时再建),走 `ml_offline/` 的训练→部署→影子模式

这个阶段才需要 `ml_offline/` 那套工程化文档/policy/schema。

---

## 与项目其他文档的关系

- `nezha/algorithm/README.md`:算法本身(Python 原型)
- `ml_offline/README.md`:**工程化降级阶段**才用的训练→ONNX→部署流水线
- 本文件:**算法研究方案**,跨上述两个之间,但本期只走研究态
