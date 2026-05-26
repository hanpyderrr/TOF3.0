"""
sim_spad_loader.py — Gutierrez-Barragan ICCV 2023 SimSPADDataset 加载器

数据源: felipegb94/learned-compressive-spad-histograms-iccv2023
        下载: scripts/download_nyuv2_simulated_spad_data.py (Google Drive)
        本地缓存目录: nezha/algorithm/datasets/SimSPADDataset_min/  (.gitignore)

**算法研究态契约**(见 docs/algorithm_test_plan.md §阶段 1.2):
    hist:     (H, W, BINS) float32, counts(未归一化), H/W=64 维持原分辨率
    depth_mm: (H, W) float32, **forward start-stop**(bin 越大=越远),0=无效

工程化降级阶段(算法收敛后)再:
    - 切 start_stop='reverse' 适配 PF32 反向
    - 2:1 spatial pool 到 32×32 适配 PF32 阵列
此处都不做。

关键踩坑:
1. 张量排列: Gutierrez `[1, n_bins, nr, nc]` -> `(nr, nc, n_bins)`,要 transpose。
2. **bin 方向**: Gutierrez 沿用 Lindell 2018 = forward(bin 0=零距离, bin 大=远)。
   loader 默认 forward,直接对应 `depth_mm = bin * BIN_MM`。
   start_stop='reverse' 才 flip bin 轴(留给工程化阶段)。
3. `bins` 字段是 normalized [0,1],去归一化乘 n_bins 拿到 bin index。

依赖: scipy (loadmat), numpy
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

import numpy as np

# ── 物理常量(与 PF32 同时序参数,55ps/bin)───────────────────────────────────
BINS = 1024
BIN_PS = 55.0
C_MM_PS = 0.299792458
BIN_MM = BIN_PS * C_MM_PS / 2.0  # ≈ 8.243 mm/bin

StartStop = Literal["forward", "reverse"]


@dataclass
class SpadSample:
    """Gutierrez 单 .mat 样本,算法研究态契约。"""
    hist: np.ndarray         # (H, W, BINS) float32, counts
    depth_mm: np.ndarray     # (H, W) float32, 按 start_stop 方向, 0=无效
    sbr: float | None        # signal-to-background ratio (若 .mat 含)
    mean_signal_photons: float | None
    mean_background_photons: float | None
    sample_id: str           # 原文件名 stem
    start_stop: StartStop    # 当前 sample 的方向(forward / reverse)

    def __post_init__(self):
        h, w, b = self.hist.shape
        assert b == BINS, f"hist bins {b} != {BINS}"
        assert self.depth_mm.shape == (h, w), \
            f"depth shape {self.depth_mm.shape} mismatch hist {(h, w)}"


def bin_to_mm(bin_idx: np.ndarray | float, start_stop: StartStop = "forward") -> np.ndarray | float:
    """bin 索引 → mm,按 start_stop 方向。

    forward (Gutierrez/Lindell): bin 0=0mm,bin 越大越远
    reverse (PF32):              bin BINS-1=0mm,bin 越小越远
    """
    arr = np.asarray(bin_idx, dtype=float)
    if start_stop == "forward":
        return arr * BIN_MM
    return (BINS - 1 - arr) * BIN_MM


def _depth_from_bins_field(bins_field: np.ndarray, start_stop: StartStop) -> np.ndarray:
    """
    Gutierrez `bins` 字段 = normalized [0,1] bin index, shape [1, 1, nr, nc] 或 [nr, nc]。
    去归一化 -> bin index, 再按 start_stop 方向转 mm。
    """
    arr = np.asarray(bins_field, dtype=np.float32).squeeze()  # (nr, nc)
    assert arr.ndim == 2, f"unexpected bins shape after squeeze: {arr.shape}"
    bin_idx = np.clip(arr * BINS, 0, BINS - 1)
    depth_mm = np.asarray(bin_to_mm(bin_idx, start_stop), dtype=np.float32)
    # bins=0 通常是仿真器无目标标记(对 forward 也是 0mm,无歧义;但实践当无效)
    depth_mm[arr <= 0] = 0.0
    return depth_mm


def load_spad_mat(
    mat_path: str | Path,
    *,
    use_field: str = "spad",
    start_stop: StartStop = "forward",
) -> SpadSample:
    """
    加载一个 Gutierrez .mat 样本。

    use_field='spad'  : 稀疏计数(更接近真实测量,**推荐**)
    use_field='rates' : 归一化直方图(sum≈1, 物理量纲不同, 仅特殊调试用)

    start_stop='forward' : Gutierrez 原向,bin 越大越远(算法研究态默认)
    start_stop='reverse' : PF32 反向,bin 轴 flip,留给工程化降级阶段
    """
    try:
        from scipy.io import loadmat
    except ImportError as e:
        raise RuntimeError("scipy is required: pip install scipy") from e

    mat_path = Path(mat_path)
    raw = loadmat(str(mat_path), squeeze_me=False)

    if use_field not in raw:
        raise KeyError(f"{mat_path.name}: field '{use_field}' not in {list(raw.keys())}")

    spad = np.asarray(raw[use_field])  # expected [1, n_bins, nr, nc] or [n_bins, nr, nc]
    if spad.ndim == 4 and spad.shape[0] == 1:
        spad = spad[0]
    assert spad.ndim == 3, f"unexpected spad shape: {spad.shape}"

    n_bins, nr, nc = spad.shape
    assert n_bins == BINS, f"bin count {n_bins} != {BINS}; try a different tres variant"

    # [n_bins, nr, nc] -> [nr, nc, n_bins]
    hist_hw_b = np.transpose(spad, (1, 2, 0)).astype(np.float32, copy=False)

    if start_stop == "reverse":
        hist_hw_b = hist_hw_b[:, :, ::-1].copy()

    # 深度 GT
    if "bins" in raw:
        depth_mm = _depth_from_bins_field(raw["bins"], start_stop=start_stop)
        if depth_mm.shape != (nr, nc):
            raise ValueError(
                f"GT depth shape {depth_mm.shape} != hist spatial {(nr, nc)}"
            )
    else:
        depth_mm = np.zeros((nr, nc), dtype=np.float32)

    def _scalar(name: str) -> float | None:
        if name not in raw:
            return None
        v = np.asarray(raw[name]).squeeze()
        return float(v) if v.size == 1 else None

    return SpadSample(
        hist=hist_hw_b,
        depth_mm=depth_mm,
        sbr=_scalar("SBR"),
        mean_signal_photons=_scalar("mean_signal_photons"),
        mean_background_photons=_scalar("mean_background_photons"),
        sample_id=mat_path.stem,
        start_stop=start_stop,
    )


def iter_dataset(
    root: str | Path,
    *,
    pattern: str = "*.mat",
    limit: int | None = None,
    **load_kwargs,
) -> Iterator[SpadSample]:
    """遍历目录下的 .mat,逐个 yield SpadSample。"""
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(
            f"{root} not found. 见 docs/algorithm_test_plan.md §阶段 1.1 下载步骤。"
        )
    files = sorted(root.rglob(pattern))
    if limit is not None:
        files = files[:limit]
    for f in files:
        yield load_spad_mat(f, **load_kwargs)


# ── sanity ───────────────────────────────────────────────────────────────────
def sanity_check(sample: SpadSample) -> dict:
    """无雾室内场景, argmax 应该 hit_rate > 95%(Gutierrez 含 Poisson 噪声)。
    失败 = 方向或 transpose 反了。
    """
    hist = sample.hist
    gt = sample.depth_mm
    argmax_bin = hist.argmax(axis=2)
    pred_mm = np.asarray(bin_to_mm(argmax_bin, sample.start_stop), dtype=np.float32)
    valid = gt > 0
    err = np.abs(pred_mm - gt)[valid]
    hit = float((err < 200).mean()) if err.size else float("nan")
    rmse = float(np.sqrt(np.mean(err ** 2))) if err.size else float("nan")
    return {
        "sample_id": sample.sample_id,
        "shape": tuple(hist.shape),
        "start_stop": sample.start_stop,
        "valid_px": int(valid.sum()),
        "argmax_hit_rate": hit,
        "argmax_rmse_mm": rmse,
        "sbr": sample.sbr,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python sim_spad_loader.py <path/to/sample.mat or dir>")
        sys.exit(0)
    target = Path(sys.argv[1])
    samples = (
        [load_spad_mat(target)] if target.is_file() else
        list(iter_dataset(target, limit=5))
    )
    for s in samples:
        print(sanity_check(s))
