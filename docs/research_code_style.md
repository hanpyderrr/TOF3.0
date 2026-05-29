# research/ 代码风格规范

> 适用范围：`research/` 下所有 Python 模块（算法、loader、评估、可视、入口脚本）。
> `nezha/` / `rk3568/` / `cloud/` 等工程化目录走自己的工程规范，不强制此约定。

---

## 一、为什么有这个文档

`research/` 是**算法研究区**——很多脚本之间互相 import、又随时被改写。
没有清晰头注释时，每个文件都得点开看 30 行才知道：
- "它做什么"
- "谁喂它数据"
- "它出什么"
- "改它会影响谁"

为了让算法迭代不至于互相打架（典型例子：loader 的 F-order bug 一度让所有
"在 spad 上"的算法数字假摔 3 倍才被发现），约定**每个模块文件开头必须有
中文五段式头注释**。

## 二、五段式模板

```python
"""
<文件路径相对 research/>:<模块名> — <一行中文简介>

功能
----
<2-3 句话说清楚做什么。能让人不打开函数就大致知道行为>

上游
----
- <数据/调用方/上游模块>
- <若有命令行参数，列出关键的>

下游
----
- <调谁 / 写什么文件 / 控制台输出>
- <返回值的形态（dataclass / dict / np.ndarray shape）>

依赖
----
- <重要的外部库（scipy.io / matplotlib / scipy.sparse）>
- <自有模块>

备注
----
- <易踩坑 / 关键约定 / 当前状态（早期原型？路线分歧？未完成？）>
- <已知 bug 或限制>
- <相关 issue / commit / 路线图 step 编号>
"""
```

### 段落说明

| 段 | 必要 | 内容 |
|---|---|---|
| 一行简介 | ✅ | 单行 ≤60 字，文件名首行，给目录扫一眼用 |
| 功能 | ✅ | 描述行为，不描述实现；含"输入是什么、输出是什么"的高层信息 |
| 上游 | ✅ | 数据来源 + 调用方 + 命令行参数（如有） |
| 下游 | ✅ | 调谁 + 写什么 + 返回值结构 |
| 依赖 | ✅ | 关键三方库 + 自有模块；不列 stdlib（os/sys/pathlib 等） |
| 备注 | ✅ | 踩坑点、状态、TODO、参考文献。**这一段是头注释里最值钱的**——把那些"
口口相传"的禁忌写进来 |

## 三、风格细则

- **中文**：除非引用文献或 API 名字，全段中文；中英混排时英文前后留半角空格
- **段标题**：用 `----` 下划线（reStructuredText 风格），不要用 `##` 也不要用裸冒号
- **保留信息**：原有英文 docstring 里有用的事实（参数默认值、物理常数、算法引用）
  必须迁过来，不要直接覆盖丢失
- **路径/符号**：用反引号引：`SpadSample`、`research/algorithms/argmax.py`
- **数字**：实测数字直接写进备注，最有价值：`实测 lmf_spad 38.3% ≈ ds_lmf 37.5%`
- **链接**：相关文件用相对路径 + 反引号，相关 commit 用短 sha 或日期
- **不要写**：版权声明、作者署名、年份、license（重复 + 易过时）
- **更新责任**：改文件主功能时**必须**同步更新头注释；只改实现细节不必

## 四、何时算"必须"

| 文件类型 | 头注释 | 函数 docstring |
|---|---|---|
| 算法模块 (`research/algorithms/*.py`) | ✅ 五段式 | ✅ 关键函数 |
| 数据/契约 (`contracts.py / sim_spad_loader.py / inject_fog.py`) | ✅ 五段式 | ✅ 公开 API |
| 评估 (`eval/*.py`) | ✅ 五段式 | ✅ 公开 API |
| 入口脚本 (`run_*.py`) | ✅ 五段式 | 不强制 |
| 测试 (`tests/test_*.py`) | ✅ 简版（功能/上游/下游/备注） | 不强制 |
| `__init__.py`（包） | ✅ 简短包注释（不必五段） | — |
| 早期原型 / 路线分歧文件 | ✅ **+ 顶部警示横幅** | 视情况 |

## 五、当前已沉淀文件清单（2026-05-28）

| 路径 | 状态 |
|------|------|
| `research/contracts.py` | ✅ |
| `research/sim_spad_loader.py` | ✅ 含 F-order bug 备忘 |
| `research/inject_fog.py` | ✅ |
| `research/tof_sim.py` | ✅ + 路线分歧警示 |
| `research/tof_process.py` | ✅ + 路线分歧警示 |
| `research/run_demo.py` | ⬜ 简版 docstring（PF32 reverse 路线早期原型，未升级五段式；下次动它再补） |
| `research/algorithms/__init__.py` | ✅ 包注释 |
| `research/algorithms/argmax.py` | ✅ |
| `research/algorithms/lmf.py` | ✅ |
| `research/algorithms/bg_sub_argmax.py` | ✅ + 命名误导警示 |
| `research/algorithms/tail_bg_argmax.py` | ✅ |
| `research/eval/__init__.py` | ✅ 包注释 |
| `research/eval/metrics.py` | ✅ |
| `research/eval/viz.py` | ✅ axvline → 顶部倒三角（不挡 bar） |
| `research/run_sanity.py` | ✅ |
| `research/run_benchmark.py` | ✅ |
| `research/run_accumulation.py` | ✅ |
| `research/run_verify_baseline.py` | ✅ |
| `research/tests/test_phase_a.py` | ✅ 简版 + F-order 测试构造修复备忘 |

> **不纳入此规范的文件**：`research/README.md`、`research/datasets/`、`research/out/`、
> `research/ml_offline/` 下的子项目。Markdown 文档按 `docs/` 通用风格写，
> 与本文档无关。

## 六、典型示例（节选 `algorithms/lmf.py`）

```python
"""
algorithms/lmf.py — 匹配滤波（Matched Filter）深度估计

功能
----
把每像素直方图与高斯 IRF 模板做循环互相关（FFT 实现），取相关结果的 argmax
作为深度。理论上对均匀白噪背景最优，SNR 提升 ≈ √(IRF 宽度) ≈ 4×（σ=2.5 时）。

上游
----
- 输入：``sim_spad_loader.SpadSample``
- 配置：``LMFConfig(irf_sigma_bins=2.5, min_corr=0.0)``

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"lmf_s{σ}"``
- 被 ``run_sanity / run_benchmark / run_accumulation`` 调

依赖
----
- numpy（FFT 用 ``np.fft.rfft/irfft`` 走 SIMD）
- ``sim_spad_loader.BINS``

备注
----
- **当前用高斯近似 IRF**，没用数据集 ``research/datasets/PSF_64x64.mat`` 里的真 IRF；
  实测 lmf_spad 38.3% 与 ds_lmf 37.5% 相当，证明高斯近似在此数据集够用。
- 在 rates 上跑实测 RMSE 8.6 mm < 1 bin，可证 LMF 具备**亚 bin 精度**。
"""
```

## 七、维护

- 新增 `research/` 下 `.py` 文件 → 必须含五段式头注释才能合并
- 改一个文件的核心行为（输入/输出/算法本质）→ 必须同步更新头注释
- 发现实测数字 / 踩坑点 → 写进对应文件**备注**段；不要只写在 commit message
- 本文档由这次（2026-05-28）的"现状梳理"沉淀；后续新规约写下面追加

---

*最后更新：2026-05-28，由"research/ 代码风格统一"工作整理*
