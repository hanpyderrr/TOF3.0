"""
run_reverse_parity.py — Phase C: reverse start-stop 方向一致性验证

功能
----
对 5 个样本，每个算法分别以 forward 和 reverse 两种方向加载并运行，
比较输出深度图的逐像素一致性。100% 一致 = 算法正确处理方向；<100% = PF32 上会有 bug。

原理
----
- forward 加载：hist 保持原样，depth = peak_bin * bin_mm
- reverse 加载：loader 翻转 hist（index 0=远端），depth = (BINS-1-peak_bin) * bin_mm
- 同一物理距离，两种加载方式的算法输出应完全相同（容差 < 0.5mm，仅允许浮点误差）

产出
----
- research/out/pf32_prep/C_reverse_parity.csv
- research/out/pf32_prep/C_reverse_parity.png
"""
from __future__ import annotations

import csv
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

from sim_spad_loader import load_spad_mat
from algorithms.argmax import estimate as argmax_est
from algorithms.lmf import estimate as lmf_est, LMFConfig
from algorithms.bg_sub_argmax import estimate as spatial_est
from algorithms.tail_bg_argmax import estimate as tail_est, TailBgArgmaxConfig
from algorithms.poisson_mle import estimate as pmle_est, PoissonMLEConfig
from algorithms.rl_deconv import estimate as rl_est, RLDeconvConfig

SAMPLES = [
    "dining_room_0022/spad_0011_p1.mat",
    "dining_room_0003/spad_0011_p1.mat",
    "living_room_0008/spad_0011_p1.mat",
    "home_office_0006/spad_0011_p1.mat",
    "office_0002c/spad_0011_p1.mat",
]
DATA_ROOT = ROOT / "datasets"
OUT_DIR = ROOT / "out" / "pf32_prep"

ALGOS = [
    ("argmax",       lambda s: argmax_est(s)),
    ("lmf_gauss",    lambda s: lmf_est(s, LMFConfig(irf_sigma_bins=2.5))),
    ("spatial_3x3",  lambda s: spatial_est(s)),
    ("tail_bg",      lambda s: tail_est(s, TailBgArgmaxConfig(tail_side="far"))),
    ("poisson_mle",  lambda s: pmle_est(s, PoissonMLEConfig())),
    ("rl_deconv10",  lambda s: rl_est(s, RLDeconvConfig(n_iter=10))),
]

# 一致性容差（mm），仅允许浮点误差
ATOL_MM = 0.5


def consistency(d_fwd: np.ndarray, d_rev: np.ndarray, gt: np.ndarray) -> float:
    """GT-valid 像素中，|fwd-rev| < ATOL_MM 的比例。"""
    mask = gt > 0
    if not mask.any():
        return float("nan")
    return float(np.isclose(d_fwd[mask], d_rev[mask], atol=ATOL_MM).mean())


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    samples_fwd, samples_rev = [], []
    for rel in SAMPLES:
        p = DATA_ROOT / rel
        if not p.exists():
            print(f"SKIP (missing): {rel}", file=sys.stderr)
            continue
        name = rel.split("/")[0]
        samples_fwd.append((name, load_spad_mat(p, start_stop="forward")))
        samples_rev.append((name, load_spad_mat(p, start_stop="reverse")))

    if not samples_fwd:
        print("No samples found", file=sys.stderr)
        return 1

    algo_names = [a for a, _ in ALGOS]
    rows = []
    # results[algo][sample] = consistency
    results: dict[str, list[float]] = {a: [] for a in algo_names}

    for (name, s_fwd), (_, s_rev) in zip(samples_fwd, samples_rev):
        gt = np.asarray(s_fwd.depth_mm, dtype=np.float32)
        for algo_name, fn in ALGOS:
            d_fwd = fn(s_fwd).depth_mm
            d_rev = fn(s_rev).depth_mm
            c = consistency(d_fwd, d_rev, gt)
            results[algo_name].append(c)
            rows.append({"algo": algo_name, "scene": name, "consistency": c})
            status = "OK" if c >= 0.999 else f"BUG {c:.3f}"
            print(f"  {algo_name:15s} | {name[:20]:20s} | {status}")

    # ---- CSV ----
    csv_path = OUT_DIR / "C_reverse_parity.csv"
    with csv_path.open("w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=["algo", "scene", "consistency"])
        w.writeheader()
        w.writerows(rows)

    # ---- Console summary ----
    print("\n=== 5-sample mean consistency (forward vs reverse) ===")
    for a in algo_names:
        mean_c = np.nanmean(results[a])
        flag = "OK" if mean_c >= 0.999 else "BUG"
        print(f"  {a:15s}: {mean_c:.4f}  {flag}")

    # ---- Plot ----
    means = [np.nanmean(results[a]) * 100 for a in algo_names]
    colors = ["#2ca02c" if m >= 99.9 else "#d62728" for m in means]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(algo_names, means, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(100, color="#333", lw=0.8, ls="--", alpha=0.5)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Forward/Reverse consistency (%)")
    ax.set_title(
        "Phase C — Reverse parity: forward vs reverse start-stop consistency\n"
        "(green=100% ✓, red=<100% → bug on PF32)",
        fontsize=11,
    )
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, min(val + 0.5, 103),
                f"{val:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()

    png_path = OUT_DIR / "C_reverse_parity.png"
    fig.savefig(png_path, dpi=150)
    print(f"\nCSV: {csv_path}")
    print(f"PNG: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
