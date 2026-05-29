# 算法研究态代码架构

> **范围**:`research/` 阶段 1-3 算法研究态。
> ⚠️ **路径说明**：本文原写于 `nezha/algorithm/`，2026-05-27/28 已整体迁移到 `research/`，
> 所有 `nezha/algorithm/` 路径请按 `research/` 理解。
> **配套**:
> - `docs/algorithm_test_plan.md` — 测试/实验方案("做什么实验,过什么阈值")
> - 本文 — 代码组织方案("代码怎么分层,接口长什么样")
> 工程化降级阶段(算法收敛后,迁入 `ml_offline/` + `nezha/ml_runtime/`)不在本文范围。

## 1. 整体分层

```
┌─────────────────────────────────────────────────────────────────┐
│ 入口层  run_sanity.py / run_fog_matrix.py / run_crossdata.py    │ 阶段流水入口
├─────────────────────────────────────────────────────────────────┤
│ 评估层  eval/{metrics, benchmark, plots, sanity}.py             │ 指标 + 出图
├─────────────────────────────────────────────────────────────────┤
│ 算法层  algorithms/{argmax, separate_v1..v4, ml/*}.py           │ 核心研究
├─────────────────────────────────────────────────────────────────┤
│ 预处理  inject_fog.py                                            │ 雾注入(已写)
├─────────────────────────────────────────────────────────────────┤
│ 数据层  sim_spad_loader / (后续)middlebury_loader / tof_sim_v2   │ 统一吐 SpadSample
├─────────────────────────────────────────────────────────────────┤
│ 契约层  SpadSample / DepthEstimate / Q_tuple (dataclass)         │ 跨层接口
└─────────────────────────────────────────────────────────────────┘
```

依赖**单向向下**。eval 不 import algorithms 内部细节(只通过统一接口),algorithms 不知道数据来源。

## 2. 数据流

```
[数据源]                      [雾]                [算法]              [评估]
loader.load_*  ──→ SpadSample ──┬──→ algorithm(sample, cfg) ──→ DepthEstimate ──→ metrics.compute(est, gt)
                                │                                                   → {RMSE, hit_rate, Q_tuple}
                                └──→ inject_fog(sample, model, level)
                                       → (SpadSample, fog_meta) ──→ algorithm ─────┘
                                                                                    ↓
                                                                              eval/runs/*.json
                                                                                    ↓
                                                                              plots.figure_A / B / C
```

**雾注入只动 `hist`,不动 `depth_mm` GT**。算法只看 hist;GT 留给评估端。

## 3. 接口契约(全局唯一)

**输入端**(已存在,见 `sim_spad_loader.py`)
```python
@dataclass
class SpadSample:
    hist: np.ndarray              # (H, W, BINS) float32
    depth_mm: np.ndarray          # (H, W) float32, 0=无效
    sbr / mean_signal_photons / mean_background_photons: float | None
    sample_id: str
    start_stop: 'forward' | 'reverse'   # 算法研究态默认 forward
```

**输出端**(待建,落 `contracts.py`)
```python
@dataclass
class DepthEstimate:
    depth_mm: np.ndarray          # (H, W) float32, 0=放弃
    confidence: np.ndarray        # (H, W) float32 [0,1]
    q_tuple: np.ndarray           # (H, W, 4) [SBR, FWHM_bins, skewness, residual_E]
    algo_name: str                # "separate_v2" 等,自带版本
    extras: dict                  # 算法独有调试量(可选)
```

**算法签名**(所有传统算法统一)
```python
def estimate(sample: SpadSample, cfg: AlgoConfig | None = None) -> DepthEstimate
```
- 配置走 **per-algorithm dataclass**(如 `SeparateV2Config`),不用全局字典
- 默认 cfg 即默认值,调用方 `dataclasses.replace(cfg, alpha=...)` 改

## 4. 文件清单与建立时机(分阶段)

### 现有 (留原地)
```
nezha/algorithm/
├── tof_sim.py           v1 物理仿真器
├── tof_process.py       v1 算法(depth_argmax / depth_separate),作 baseline
├── peak_detect.h        C 端等价
├── sim_spad_loader.py   ✅ 已重写:64×64/forward,SpadSample 契约
└── inject_fog.py        ✅ 已写:Gamma + 3 档 + Poisson + fog_meta
```

### 阶段 1 (基线打通) — 4 个新文件
```
nezha/algorithm/
├── contracts.py                    DepthEstimate / AlgoConfig 公共契约
├── algorithms/
│   ├── __init__.py
│   └── argmax.py                   v0 baseline(纯 argmax,新接口)
└── eval/
    ├── metrics.py                  RMSE / hit_rate / Q_tuple 计算
    └── sanity.py                   无雾 baseline sanity 入口
```

### 阶段 2 (雾注入对比) — 4 个新文件
```
nezha/algorithm/
├── algorithms/
│   ├── separate_v1.py              tof_process.depth_separate 包装(adapter)
│   └── separate_v2.py              Gamma 拟合 + DBSCAN + Gaussian(核心新算法)
├── eval/
│   ├── benchmark.py                算法 × 雾档矩阵 runner
│   └── plots.py                    图 A / B / C 出图(matplotlib)
└── run_fog_matrix.py               入口脚本
```

### 阶段 2 后期 / 阶段 3
```
nezha/algorithm/
├── algorithms/
│   ├── separate_v3.py              v2 + 邻域加权
│   ├── separate_v4.py              v3 + Skewed Gaussian
│   └── ml/                         ML 算法独立子树(数据增强复用 inject_fog)
│       ├── models/
│       ├── train.py
│       └── infer.py
├── loaders/
│   ├── middlebury_loader.py
│   └── adaptive_gating_loader.py
└── tof_sim_v2.py                   自造数据升级版
```

**不建空目录**:每个目录在第一个文件落地时再建,避免 stub 满天飞。

## 5. 关键设计待确认

> 以下五项标 [PENDING] 未与用户确认;我倾向意见见每节末尾。落代码前需确认。

### Q1. 算法接口形态:函数 vs 类 [PENDING]

- **A. 函数式**:`def estimate(sample, cfg) -> DepthEstimate`,无状态;参数走 dataclass cfg。与现有 `tof_process.depth_argmax` 风格一致。
- **B. 类式**:`SeparateV2(cfg).estimate(sample)`。利于 ML(模型状态),但传统算法多余。

**我倾向 A + B 折衷**:传统算法走 A,ML 走 B(继承 `Estimator` ABC)。两侧都简洁。

### Q2. 现有 `tof_process.py` v1 怎么处理 [PENDING]

- **A. 留原地不动,新算法另起文件** — baseline 永远跑得通,新接口不破坏旧调用方
- **B. 改造 v1 也接 DepthEstimate 契约** — 统一干净但要改 `qt_app/` 调用方
- **C. `algorithms/separate_v1.py` 里包 adapter** — tof_process 不动,新接口通过 adapter 调它

**我倾向 A + 阶段 2 时 C**:阶段 1 不做包装,阶段 2 实际对比 v1 vs v2 时再加 adapter。

### Q3. ML 路线进 `nezha/algorithm/algorithms/ml/` 还是 `ml_offline/` [PENDING]

- `ml_offline/` 是**工程化降级阶段**才用(ONNX 导出/shadow/policy),与训练强绑定
- 算法研究态 ML 应该在 `nezha/algorithm/algorithms/ml/`,PyTorch + 训练脚本,**不出 ONNX**
- 收敛后再"搬"到 `ml_offline/` 做工程化降级

### Q4. 输出/缓存目录约定 [PENDING]

```
nezha/algorithm/
├── datasets/      公开数据缓存 (.gitignore 已加)
├── runs/          每次评测 JSON/CSV (新,需 .gitignore)
└── out/           图片产物 (.gitignore 已加)
```
- **A. `runs/` 全 .gitignore**
- **B. `runs/*/` 内层 ignore,保留索引文件 latest.json**

我倾向 A(简单);需要复现时按 `sample_id + algo_name + fog_meta` 一致即可复跑。

### Q5. 配置如何管 [PENDING]

- **A. per-algorithm dataclass 写死在算法文件里**,默认 cfg 即默认值
- **B. YAML 集中配置 + 加载到 dataclass**,便于实验批跑

**阶段 1 显然 A 够用,阶段 2 benchmark 批量跑(算法 × 雾档 = 4×3=12 实验)时考虑 B**。

## 6. 与项目其他部分的边界

| 路径 | 现阶段动?| 说明 |
|------|---------|------|
| `research/` | ✅ **唯一活跃区域** | 算法研究全在此（原 `nezha/algorithm/`，已迁移） |
| `nezha/acquisition/` | ❌ 不动 | PF32 工程化降级阶段 |
| `nezha/qt_app/` | ❌ 不动 | 算法收敛后再对接 |
| `ml_offline/` | ❌ 不动 | 工程化降级阶段才用 |
| `rk3568/` | ❌ 不动 | — |
| `cloud/` | ❌ 不动 | — |

## 7. 与文档体系的关系

| 文档 | 职责 |
|------|------|
| `docs/algorithm_test_plan.md` | 测试方案:四阶段/数据源/雾模型/算法版本/通过条件 |
| **本文** | 代码方案:分层/契约/文件清单/接口形态 |
| `nezha/algorithm/README.md` | 算法本身(Python 原型)使用说明 — 阶段 1 末尾更新 |
| `ml_offline/README.md` | 工程化降级阶段才用,本期不动 |
