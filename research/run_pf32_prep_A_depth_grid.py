"""
run_pf32_prep_A_depth_grid.py — Phase A 深度图横向对比 grid

功能
----
对 PF32 准备阶段 A 的 5 样本 × 9 算法跑一遍预测深度图，画成 5×10 grid：
  - 列 0：GT depth
  - 列 1..9：各算法预测 depth
  - 行：5 个不同场景样本
  - 每行共享色阶（取该样本 GT 的 vmin/vmax），行末附 colorbar
  - 每格底部小字注 hit@200mm

上游
----
- ``research/datasets/scene_group0/<scene>/spad_0011_p1.mat`` × 5
- ``research/datasets/PSF_64x64.mat``（lmf_real 用）

下游
----
- ``research/out/pf32_prep/A_depth_grid.png``

依赖
----
- numpy / matplotlib(Agg)
- ``sim_spad_loader / algorithms.* / eval.metrics``

备注
----
- 行内统一色阶最直观，跨样本 vmin/vmax 差异大不强制对齐
- 算法多时 figsize 会很宽（22×11 inch @150dpi），生成约 1MB PNG
- 与 ``A_baseline_grid.png``（统计对比）配套使用，前者出数字、本图出视觉
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sim_spad_loader import BINS, load_spad_mat
from algorithms.argmax import estimate as argmax_estimate
from algorithms.lmf import estimate as lmf_estimate, LMFConfig
from algorithms.bg_sub_argmax import estimate as spatial_estimate
from algorithms.tail_bg_argmax import estimate as tail_estimate
from algorithms.gaussian_fit import estimate as gauss_fit_estimate, GaussianFitConfig
from algorithms.poisson_mle import estimate as pmle_estimate, PoissonMLEConfig
from algorithms.rl_deconv import estimate as rl_estimate, RLDeconvConfig


SAMPLES = [
    "dining_room_0022/spad_0011_p1.mat",
    "dining_room_0003/spad_0011_p1.mat",
    "living_room_0008/spad_0011_p1.mat",
    "home_office_0006/spad_0011_p1.mat",
    "office_0002c/spad_0011_p1.mat",
]
DATA_ROOT = ROOT / "datasets"
PSF_PATH = str(DATA_ROOT / "PSF_64x64.mat")
OUT_PATH = ROOT / "out" / "pf32_prep" / "A_depth_grid_all.png"


def _ds_depth(sample, attr: str) -> np.ndarray | None:
    bins = getattr(sample, attr, None)
    if bins is None:
        return None
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0
    pred_bin = np.clip(bins.astype(np.int32), 0, BINS - 1)
    if sample.start_stop == "forward":
        return pred_bin.astype(np.float32) * bin_mm
    return (BINS - 1 - pred_bin).astype(np.float32) * bin_mm


def _hit200(pred: np.ndarray, gt: np.ndarray) -> float:
    mask = gt > 0
    if not mask.any():
        return float("nan")
    return float((np.abs(pred[mask] - gt[mask]) < 200).mean())


def _algos_for(sample):
    """Return ordered list of (name, depth_mm)."""
    _psf_ok = Path(PSF_PATH).exists()
    out = []
    out.append(("argmax_spad",   argmax_estimate(sample).depth_mm))
    out.append(("lmf_gauss",     lmf_estimate(sample, LMFConfig(irf_sigma_bins=2.5)).depth_mm))
    if _psf_ok:
        out.append(("lmf_real",    lmf_estimate(sample, LMFConfig(irf_path=PSF_PATH)).depth_mm))
        out.append(("lmf_real_pc", lmf_estimate(sample, LMFConfig(irf_path=PSF_PATH, per_column=True)).depth_mm))
    out.append(("spatial_3x3",   spatial_estimate(sample).depth_mm))
    out.append(("tail_bg",       tail_estimate(sample).depth_mm))
    out.append(("poisson_mle",   pmle_estimate(sample, PoissonMLEConfig()).depth_mm))
    out.append(("rl_deconv10",   rl_estimate(sample, RLDeconvConfig(n_iter=10)).depth_mm))
    for tag, attr in [
        ("ds_argmax", "est_argmax_bins"),
        ("ds_lmf",    "est_lmf_bins"),
        ("ds_zncc",   "est_zncc_bins"),
    ]:
        d = _ds_depth(sample, attr)
        if d is not None:
            out.append((tag, d))
    return out


def main() -> int:
    samples = []
    for rel in SAMPLES:
        p = DATA_ROOT / rel
        if not p.exists():
            print(f"SKIP (missing): {rel}", file=sys.stderr)
            continue
        s = load_spad_mat(p)
        samples.append((rel.split("/")[1], s))

    if not samples:
        print("No samples", file=sys.stderr)
        return 1

    # Determine algo order from first sample
    algo_names = [name for name, _ in _algos_for(samples[0][1])]
    n_algos = len(algo_names)
    n_samples = len(samples)
    n_cols = n_algos + 1  # +GT

    fig, axes = plt.subplots(
        n_samples, n_cols,
        figsize=(2.0 * n_cols + 1.0, 2.0 * n_samples + 0.5),
        squeeze=False,
    )

    cmap = "plasma"
    for r, (scene, sample) in enumerate(samples):
        gt = np.asarray(sample.depth_mm, dtype=np.float32)
        valid = gt > 0
        if valid.any():
            vmin, vmax = float(gt[valid].min()), float(gt[valid].max())
        else:
            vmin, vmax = 0.0, 1.0
        gt_plot = np.where(valid, gt, np.nan)

        # Col 0: GT
        ax = axes[r, 0]
        im = ax.imshow(gt_plot, cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_xticks([]); ax.set_yticks([])
        if r == 0:
            ax.set_title("GT", fontsize=10, fontweight="bold")
        ax.set_ylabel(scene[:14], fontsize=8, rotation=90, labelpad=2)

        # Cols 1..n: algorithms
        all_algos = _algos_for(sample)
        for c, (name, pred) in enumerate(all_algos, start=1):
            pred_plot = np.where(pred > 0, pred, np.nan)
            ax = axes[r, c]
            ax.imshow(pred_plot, cmap=cmap, vmin=vmin, vmax=vmax)
            ax.set_xticks([]); ax.set_yticks([])
            if r == 0:
                ax.set_title(name, fontsize=9)
            hit = _hit200(pred, gt)
            ax.text(
                0.5, -0.04, f"hit@200={hit:.2f}",
                ha="center", va="top", transform=ax.transAxes,
                fontsize=8, color="#333",
            )

        # Per-row colorbar on the right edge
        cbar = fig.colorbar(im, ax=axes[r, :].tolist(), fraction=0.012, pad=0.01)
        cbar.ax.tick_params(labelsize=7)
        cbar.set_label("mm", fontsize=7)

    fig.suptitle(
        "PF32 prep — Stage A: depth maps (rows=samples, cols=GT + 9 algorithms)",
        fontsize=12, y=0.995,
    )
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"PNG: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
