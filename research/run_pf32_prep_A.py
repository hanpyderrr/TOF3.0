"""
run_pf32_prep_A.py — Phase A baseline 补全（PF32 准备工作 阶段 A）

功能
----
5 样本 × 8 算法 × 4 容差档全表跑分，落 CSV + PNG：
- argmax_spad / lmf_gauss(σ=2.5) / lmf_real / lmf_real_pc / spatial_3x3 /
  tail_bg_argmax / ds_argmax / ds_lmf / ds_zncc
- 图：左 hit@200mm 各算法散点+均值横线；右 RMSE 箱形图
- 数据：``research/out/pf32_prep/A_baseline.csv``
- 图：``research/out/pf32_prep/A_baseline_grid.png``

上游
----
- ``research/datasets/scene_group0/<scene>/spad_0011_p1.mat`` × 5
- ``research/datasets/PSF_64x64.mat``（真 IRF）

下游
----
- 控制台 5 样本均值表
- CSV + PNG

依赖
----
- numpy / matplotlib (Agg) / scipy.io
- ``sim_spad_loader / contracts / algorithms.* / eval.metrics``

备注
----
- 与 ``run_verify_baseline.py`` 同源但扩到 8 算法；前者 5 算法表保留不动
- 实测 5 样本均值：lmf_gauss ≈ lmf_real ≈ ds_lmf @hit_200，但 lmf_gauss @hit_12 反超 7pp
- PF32 上线建议直接用 lmf_gauss σ≈2.5（real IRF 没有显著增益）
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sim_spad_loader import BINS, load_spad_mat
from algorithms.argmax import estimate as argmax_estimate, ArgmaxConfig
from algorithms.lmf import estimate as lmf_estimate, LMFConfig
from algorithms.bg_sub_argmax import estimate as spatial_estimate
from algorithms.tail_bg_argmax import estimate as tail_estimate


SAMPLES = [
    "scene_group0/dining_room_0022/spad_0011_p1.mat",
    "scene_group0/dining_room_0003/spad_0011_p1.mat",
    "scene_group0/living_room_0008/spad_0011_p1.mat",
    "scene_group0/home_office_0006/spad_0011_p1.mat",
    "scene_group0/office_0002c/spad_0011_p1.mat",
]
TOLS_MM = [12, 24, 60, 200]
DATA_ROOT = ROOT / "datasets"
PSF_PATH = str(DATA_ROOT / "PSF_64x64.mat")
OUT_DIR = ROOT / "out" / "pf32_prep"


def _metrics(pred_mm: np.ndarray, gt_mm: np.ndarray, tols: list[int]) -> dict:
    mask = gt_mm > 0
    if not mask.any():
        return {f"hit_{t}": float("nan") for t in tols} | {"rmse": float("nan")}
    err = np.abs(pred_mm[mask] - gt_mm[mask])
    out = {f"hit_{t}": float((err < t).mean()) for t in tols}
    out["rmse"] = float(np.sqrt((err**2).mean()))
    return out


def _ds_estimate(sample, attr: str) -> np.ndarray | None:
    bins = getattr(sample, attr, None)
    if bins is None:
        return None
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0
    pred_bin = np.clip(bins.astype(np.int32), 0, BINS - 1)
    if sample.start_stop == "forward":
        return pred_bin.astype(np.float64) * bin_mm
    return (BINS - 1 - pred_bin).astype(np.float64) * bin_mm


def run() -> dict:
    """Return {algo: [(sample_id, metrics_dict), ...]}."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    algos = [
        ("argmax_spad",   lambda s: argmax_estimate(s).depth_mm),
        ("lmf_gauss_2.5", lambda s: lmf_estimate(s, LMFConfig(irf_sigma_bins=2.5)).depth_mm),
        ("lmf_real",      lambda s: lmf_estimate(s, LMFConfig(irf_path=PSF_PATH)).depth_mm),
        ("lmf_real_pc",   lambda s: lmf_estimate(s, LMFConfig(irf_path=PSF_PATH, per_column=True)).depth_mm),
        ("spatial_3x3",   lambda s: spatial_estimate(s).depth_mm),
        ("tail_bg_argmax",lambda s: tail_estimate(s).depth_mm),
    ]
    ds_algos = [
        ("ds_argmax", "est_argmax_bins"),
        ("ds_lmf",    "est_lmf_bins"),
        ("ds_zncc",   "est_zncc_bins"),
    ]

    results: dict[str, list[tuple[str, dict]]] = {}
    for rel in SAMPLES:
        path = DATA_ROOT / rel
        if not path.exists():
            print(f"SKIP (missing): {rel}", file=sys.stderr)
            continue
        sample = load_spad_mat(path)
        gt = sample.depth_mm
        scene = rel.split("/")[1]
        for name, fn in algos:
            pred = fn(sample)
            m = _metrics(pred, gt, TOLS_MM)
            results.setdefault(name, []).append((scene, m))
        for name, attr in ds_algos:
            pred = _ds_estimate(sample, attr)
            if pred is None:
                continue
            m = _metrics(pred, gt, TOLS_MM)
            results.setdefault(name, []).append((scene, m))
    return results


def write_csv(results: dict) -> Path:
    out = OUT_DIR / "A_baseline.csv"
    with out.open("w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["algo", "scene"] + [f"hit_{t}mm" for t in TOLS_MM] + ["rmse_mm"])
        for algo, rows in results.items():
            for scene, m in rows:
                w.writerow(
                    [algo, scene]
                    + [f"{m[f'hit_{t}']:.4f}" for t in TOLS_MM]
                    + [f"{m['rmse']:.2f}"]
                )
    return out


def write_summary(results: dict) -> None:
    print(f"\n=== 5-sample mean (hit@tol_mm / RMSE_mm) ===")
    print(f"{'algo':<16}" + "".join(f"{f'hit_{t}':>9}" for t in TOLS_MM) + f"{'rmse':>10}")
    print("-" * (16 + 9 * len(TOLS_MM) + 10))
    for algo, rows in results.items():
        means = {
            k: np.mean([r[k] for _, r in rows])
            for k in (list(f"hit_{t}" for t in TOLS_MM) + ["rmse"])
        }
        print(
            f"{algo:<16}"
            + "".join(f"{means[f'hit_{t}']:>9.3f}" for t in TOLS_MM)
            + f"{means['rmse']:>10.1f}"
        )


def plot(results: dict, png_path: Path) -> Path:
    import os
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    # algo display order (ours first then ds_*)
    order = [
        "argmax_spad", "lmf_gauss_2.5", "lmf_real", "lmf_real_pc",
        "spatial_3x3", "tail_bg_argmax",
        "ds_argmax", "ds_lmf", "ds_zncc",
    ]
    algos = [a for a in order if a in results]
    is_ds = ["ds_" in a for a in algos]
    colors = ["#1f77b4" if not d else "#888888" for d in is_ds]

    hit200 = [[r["hit_200"] for _, r in results[a]] for a in algos]
    rmses = [[r["rmse"] for _, r in results[a]] for a in algos]
    means_hit = [float(np.mean(h)) for h in hit200]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    ax = axes[0]
    xs = np.arange(len(algos))
    for i, ys in enumerate(hit200):
        ax.scatter([i] * len(ys), ys, color=colors[i], alpha=0.55, s=42, zorder=3)
    ax.scatter(xs, means_hit, marker="_", color="#d62728", s=600,
               linewidths=3, zorder=4, label="mean")
    ax.set_xticks(xs)
    ax.set_xticklabels(algos, rotation=30, ha="right")
    ax.set_ylabel("hit_rate @ 200mm")
    ax.set_title("Phase A baseline — hit@200mm (5 samples, dots) + mean (red bar)")
    ax.set_ylim(0, 1.0)
    ax.axhline(1.0, ls="--", color="#d62728", lw=0.8, alpha=0.5)
    ax.text(len(algos) - 0.5, 1.005, "rates upper bound", color="#d62728",
            fontsize=8, ha="right", va="bottom")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="lower right")

    ax = axes[1]
    bp = ax.boxplot(rmses, positions=xs, widths=0.6, patch_artist=True,
                    medianprops={"color": "#d62728"})
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    ax.set_xticks(xs)
    ax.set_xticklabels(algos, rotation=30, ha="right")
    ax.set_ylabel("RMSE (mm)")
    ax.set_title("Phase A baseline — RMSE box across 5 samples")
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("PF32 prep — Stage A: baseline grid (Gutierrez 64×64, SBR≈0.2)", fontsize=12)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    return png_path


def main() -> int:
    results = run()
    if not results:
        print("No samples processed.", file=sys.stderr)
        return 1
    csv_path = write_csv(results)
    write_summary(results)
    png_path = plot(results, OUT_DIR / "A_baseline_grid.png")
    print(f"\nCSV: {csv_path}")
    print(f"PNG: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
