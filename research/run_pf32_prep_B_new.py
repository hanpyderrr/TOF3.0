"""
run_pf32_prep_B_new.py — 新算法多帧累加曲线（gaussian_fit / poisson_mle / rl_deconv）

与 run_pf32_prep_B.py 结构相同，但只跑三个新算法，并叠加已知参考线
（argmax / lmf_gauss / spatial_3x3，从 B_accumulation.csv 读取均值）。

产出
----
- ``research/out/pf32_prep/B_new_accumulation.csv``
- ``research/out/pf32_prep/B_new_accumulation_curves.png``

备注
----
- gauss_fit 逐像素 curve_fit，64×64 帧约 0.5–3 s；5×7×3=105 次约 3–5 分钟。
- K 增大后拟合成功率上升，gauss_fit 曲线应与 lmf_gauss 逐渐接近。
"""
from __future__ import annotations

import csv
import dataclasses
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sim_spad_loader import BINS, load_spad_mat
from algorithms.gaussian_fit import estimate as gauss_fit_estimate, GaussianFitConfig
from algorithms.poisson_mle import estimate as pmle_estimate, PoissonMLEConfig
from algorithms.rl_deconv import estimate as rl_estimate, RLDeconvConfig
from eval.metrics import compute_all
from run_accumulation import _simulate_k_shots

SAMPLES = [
    "dining_room_0022/spad_0011_p1.mat",
    "dining_room_0003/spad_0011_p1.mat",
    "living_room_0008/spad_0011_p1.mat",
    "home_office_0006/spad_0011_p1.mat",
    "office_0002c/spad_0011_p1.mat",
]
K_VALUES = [1, 2, 4, 8, 16, 32, 64]
TRIALS = 3
IRF_SIGMA = 2.5
DATA_ROOT = ROOT / "datasets"
OUT_DIR = ROOT / "out" / "pf32_prep"

ALGO_CFG = {
    "poisson_mle": (pmle_estimate,  PoissonMLEConfig()),
    "rl_deconv10": (rl_estimate,    RLDeconvConfig(n_iter=10)),
    "rl_deconv20": (rl_estimate,    RLDeconvConfig(n_iter=20)),
}
# gauss_fit excluded: per-pixel scipy.optimize.curve_fit is ~37s/frame for 64×64;
# its single-frame result equals argmax (82.5% fallback in low SNR) and a full
# K-sweep would take >1 hour. Evaluate separately at high K if sub-bin precision needed.

# Reference mean lines from Phase B original (B_accumulation.csv); fallback to None if missing
REF_CSV = OUT_DIR / "B_accumulation.csv"


def _load_ref_means() -> dict[str, dict[int, float]]:
    """Return {algo: {K: mean_hit}} from B_accumulation.csv, or {} if not found."""
    if not REF_CSV.exists():
        return {}
    import csv as _csv
    rows: dict[str, dict[int, list]] = {}
    with REF_CSV.open() as fp:
        for r in _csv.DictReader(fp):
            a, K, h = r["algo"], int(r["K"]), float(r["hit_rate"])
            rows.setdefault(a, {}).setdefault(K, []).append(h)
    return {a: {K: float(np.mean(vs)) for K, vs in kd.items()} for a, kd in rows.items()}


def _run_algo(name, fn, cfg, sample):
    est = fn(sample, cfg)
    return compute_all(est, sample)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    algo_names = list(ALGO_CFG.keys())

    samples = []
    for rel in SAMPLES:
        p = DATA_ROOT / rel
        if not p.exists():
            print(f"SKIP (missing): {rel}", file=sys.stderr)
            continue
        s = load_spad_mat(p, start_stop="forward")
        samples.append((rel.split("/")[1], s))

    if not samples:
        print("No samples", file=sys.stderr)
        return 1

    rng_master = np.random.default_rng(seed=42)
    rows = []
    results = {a: {K: {"hit": [], "rmse": []} for K in K_VALUES} for a in algo_names}

    total = len(samples) * len(K_VALUES) * TRIALS
    done = 0
    t0 = time.time()

    for scene, sample in samples:
        for K in K_VALUES:
            for t in range(TRIALS):
                trial_rng = np.random.default_rng(rng_master.integers(0, 2**31))
                hist_k = _simulate_k_shots(sample, K, IRF_SIGMA, trial_rng)
                s_k = dataclasses.replace(sample, hist=hist_k)
                for a, (fn, cfg) in ALGO_CFG.items():
                    m = _run_algo(a, fn, cfg, s_k)
                    h, r = float(m["hit_rate"]), float(m["rmse_mm"])
                    results[a][K]["hit"].append(h)
                    results[a][K]["rmse"].append(r)
                    rows.append({"algo": a, "scene": scene, "K": K, "trial": t,
                                 "hit_rate": h, "rmse_mm": r})
                done += 1
                elapsed = time.time() - t0
                eta = elapsed / done * (total - done)
                print(f"  [{done}/{total}] scene={scene} K={K} trial={t}  "
                      f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s", end="\r", flush=True)

    print()

    # ---- CSV ----
    csv_path = OUT_DIR / "B_new_accumulation.csv"
    with csv_path.open("w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["algo", "scene", "K", "trial", "hit_rate", "rmse_mm"])
        for r in rows:
            w.writerow([r["algo"], r["scene"], r["K"], r["trial"],
                        f"{r['hit_rate']:.4f}", f"{r['rmse_mm']:.2f}"])

    # ---- Console summary ----
    print("\n=== 5-sample × 3-trial mean (hit@200mm, %) ===")
    print(f"{'K':>4}" + "".join(f"{a:>14}" for a in algo_names))
    for K in K_VALUES:
        line = f"{K:>4}"
        for a in algo_names:
            mh = 100.0 * float(np.mean(results[a][K]["hit"]))
            line += f"{mh:>13.1f}%"
        print(line)

    # ---- Plot ----
    ref_means = _load_ref_means()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    new_colors = {
        "gauss_fit":   "#9467bd",
        "poisson_mle": "#8c564b",
        "rl_deconv10": "#e377c2",
        "rl_deconv20": "#17becf",
    }
    ref_colors = {
        "argmax":     "#1f77b4",
        "lmf_gauss":  "#ff7f0e",
        "spatial_3x3":"#2ca02c",
    }
    ks = np.array(K_VALUES, dtype=float)

    # Reference lines from B_accumulation.csv
    for ref_name, rc in ref_colors.items():
        if ref_name in ref_means:
            ref_hits = [ref_means[ref_name].get(K, float("nan")) for K in K_VALUES]
            ax1.plot(ks, np.array(ref_hits) * 100, ls="--", color=rc,
                     alpha=0.6, label=f"{ref_name} (Phase B ref)", lw=1.5)

    # New algorithm curves with std bands
    for a in algo_names:
        hits  = np.array([results[a][K]["hit"]  for K in K_VALUES])
        rmses = np.array([results[a][K]["rmse"] for K in K_VALUES])
        m_hit,  s_hit  = hits.mean(axis=1),  hits.std(axis=1)
        m_rmse, s_rmse = rmses.mean(axis=1), rmses.std(axis=1)
        c = new_colors[a]
        ax1.plot(ks, m_hit * 100, marker="o", color=c, label=a, lw=2.0)
        ax1.fill_between(ks, (m_hit - s_hit) * 100, (m_hit + s_hit) * 100,
                         color=c, alpha=0.15)
        ax2.plot(ks, m_rmse, marker="o", color=c, label=a, lw=2.0)
        ax2.fill_between(ks, m_rmse - s_rmse, m_rmse + s_rmse, color=c, alpha=0.15)

    # RMSE reference lines
    for ref_name, rc in ref_colors.items():
        if ref_name in ref_means:
            pass  # rmse not stored in ref CSV — skip

    for ax in (ax1, ax2):
        ax.set_xscale("log", base=2)
        ax.set_xticks(K_VALUES)
        ax.set_xticklabels(K_VALUES)
        ax.set_xlabel("K (shots accumulated)")
        ax.grid(True, alpha=0.3)

    ax1.set_ylabel("hit_rate @ 200mm  (%)")
    ax1.set_ylim(0, 105)
    ax1.set_title("hit_rate vs K — new algorithms (solid) vs Phase B refs (dashed)")
    ax1.legend(fontsize=8, loc="lower right")
    ax2.set_ylabel("RMSE (mm)")
    ax2.set_title("RMSE vs K — new algorithms")
    ax2.legend(fontsize=8, loc="upper right")

    fig.suptitle(
        f"PF32 prep — Stage B (new algos): K-shot accumulation "
        f"(Gutierrez 64×64, SBR≈0.2, IRF σ={IRF_SIGMA})",
        fontsize=12,
    )
    fig.tight_layout()
    png_path = OUT_DIR / "B_new_accumulation_curves.png"
    fig.savefig(png_path, dpi=150)
    print(f"\nCSV: {csv_path}")
    print(f"PNG: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
