"""
run_pf32_prep_B.py — 多帧累加曲线（PF32 准备工作 阶段 B）

功能
----
对 5 样本各自做 K∈[1,2,4,8,16,32,64] × N trials 的物理累加（复用 run_accumulation.py
里的 ``_simulate_k_shots``），统计 5 样本均值 ± std 曲线：
- 算法：argmax / lmf_gauss(σ=2.5) / spatial_3x3 / tail_bg_argmax
- 参考线：argmax_rates 上界(1.0) / ds_lmf 均值 / ds_argmax 均值

产出
----
- ``research/out/pf32_prep/B_accumulation.csv``  (algo × sample × K × trial × hit/rmse)
- ``research/out/pf32_prep/B_accumulation_curves.png``  (hit_rate vs K + RMSE vs K)

上游
----
- ``research/datasets/scene_group0/<scene>/spad_0011_p1.mat`` × 5
- ``run_accumulation._simulate_k_shots`` 物理累加

下游
----
- 计划文档 ``docs/algorithm_pf32_prep_plan.md`` 阶段 B 表

依赖
----
- numpy / matplotlib(Agg)
- ``sim_spad_loader / algorithms.{argmax, lmf, bg_sub_argmax, tail_bg_argmax}``
- ``eval.metrics.compute_all``

备注
----
- 物理累加：每 shot 独立 Poisson(msph) 信号 + Poisson(mbph/BINS) 背景；K shots 直方图相加
- 5 样本 × 7 K × 3 trials × 4 算法 ≈ 420 次 estimate，整体跑 < 1 分钟
- 跨样本均值是核心 takeaway；std 阴影显示场景间方差
- tail_bg 预期在无雾累加下与 argmax 完全重合（数学事实），保留作验证
"""
from __future__ import annotations

import csv
import dataclasses
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

from sim_spad_loader import BINS, load_spad_mat, bin_to_mm
from algorithms.argmax import estimate as argmax_estimate
from algorithms.lmf import estimate as lmf_estimate, LMFConfig
from algorithms.bg_sub_argmax import estimate as spatial_estimate
from algorithms.tail_bg_argmax import estimate as tail_estimate
from eval.metrics import compute_all, hit_rate as hit_rate_fn
from run_accumulation import _simulate_k_shots


SAMPLES = [
    "scene_group0/dining_room_0022/spad_0011_p1.mat",
    "scene_group0/dining_room_0003/spad_0011_p1.mat",
    "scene_group0/living_room_0008/spad_0011_p1.mat",
    "scene_group0/home_office_0006/spad_0011_p1.mat",
    "scene_group0/office_0002c/spad_0011_p1.mat",
]
K_VALUES = [1, 2, 4, 8, 16, 32, 64]
TRIALS = 3
IRF_SIGMA = 2.5
DATA_ROOT = ROOT / "datasets"
OUT_DIR = ROOT / "out" / "pf32_prep"


def _run_one_algo(name, sample_with_accum_hist):
    if name == "argmax":
        est = argmax_estimate(sample_with_accum_hist)
    elif name == "lmf_gauss":
        est = lmf_estimate(sample_with_accum_hist, LMFConfig(irf_sigma_bins=2.5))
    elif name == "spatial_3x3":
        est = spatial_estimate(sample_with_accum_hist)
    elif name == "tail_bg":
        est = tail_estimate(sample_with_accum_hist)
    else:
        raise ValueError(name)
    return compute_all(est, sample_with_accum_hist)


def _ds_hit(sample, attr):
    bins = getattr(sample, attr, None)
    if bins is None:
        return float("nan")
    pred_mm = np.asarray(bin_to_mm(bins.astype(np.float32),
                                   sample.start_stop, sample.bin_size_ps))
    return hit_rate_fn(pred_mm, sample.depth_mm)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    algo_names = ["argmax", "lmf_gauss", "spatial_3x3", "tail_bg"]

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

    # Reference lines (5-sample mean) for ds_argmax / ds_lmf
    ds_argmax_mean = float(np.mean([_ds_hit(s, "est_argmax_bins") for _, s in samples]))
    ds_lmf_mean    = float(np.mean([_ds_hit(s, "est_lmf_bins")    for _, s in samples]))

    # Run grid: (algo, sample, K, trial) -> (hit, rmse)
    rng_master = np.random.default_rng(seed=42)
    rows = []   # list of dicts for CSV
    # in-memory: results[algo][K] = list of per-sample-per-trial hit/rmse
    results = {a: {K: {"hit": [], "rmse": []} for K in K_VALUES} for a in algo_names}

    for scene, sample in samples:
        for K in K_VALUES:
            for t in range(TRIALS):
                trial_rng = np.random.default_rng(rng_master.integers(0, 2**31))
                hist_k = _simulate_k_shots(sample, K, IRF_SIGMA, trial_rng)
                s_k = dataclasses.replace(sample, hist=hist_k)
                for a in algo_names:
                    m = _run_one_algo(a, s_k)
                    h = float(m["hit_rate"])
                    r = float(m["rmse_mm"])
                    results[a][K]["hit"].append(h)
                    results[a][K]["rmse"].append(r)
                    rows.append({
                        "algo": a, "scene": scene, "K": K, "trial": t,
                        "hit_rate": h, "rmse_mm": r,
                    })

    # ---- Write CSV ----
    csv_path = OUT_DIR / "B_accumulation.csv"
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
    print(f"\nref lines:  argmax_rates upper bound = 100%")
    print(f"            ds_argmax (5 sample mean) = {ds_argmax_mean * 100:.1f}%")
    print(f"            ds_lmf    (5 sample mean) = {ds_lmf_mean    * 100:.1f}%")

    # ---- Plot ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    colors = {
        "argmax":     "#1f77b4",
        "lmf_gauss":  "#ff7f0e",
        "spatial_3x3":"#2ca02c",
        "tail_bg":    "#d62728",
    }
    ks = np.array(K_VALUES, dtype=float)

    for a in algo_names:
        hits = np.array([results[a][K]["hit"] for K in K_VALUES])    # (n_K, n_samples*n_trials)
        rmses = np.array([results[a][K]["rmse"] for K in K_VALUES])
        m_hit, s_hit = hits.mean(axis=1), hits.std(axis=1)
        m_rmse, s_rmse = rmses.mean(axis=1), rmses.std(axis=1)
        c = colors[a]
        ax1.plot(ks, m_hit * 100, marker="o", color=c, label=a, lw=1.8)
        ax1.fill_between(ks, (m_hit - s_hit) * 100, (m_hit + s_hit) * 100,
                         color=c, alpha=0.15)
        ax2.plot(ks, m_rmse, marker="o", color=c, label=a, lw=1.8)
        ax2.fill_between(ks, m_rmse - s_rmse, m_rmse + s_rmse, color=c, alpha=0.15)

    # reference lines (hit panel)
    ax1.axhline(100, ls="--", color="#777", alpha=0.6,
                label="argmax_rates upper bound (100%)")
    ax1.axhline(ds_lmf_mean * 100, ls=":", color="black", alpha=0.7,
                label=f"ds_lmf 5-sample mean ({ds_lmf_mean * 100:.1f}%)")
    ax1.axhline(ds_argmax_mean * 100, ls="-.", color="#444", alpha=0.5,
                label=f"ds_argmax 5-sample mean ({ds_argmax_mean * 100:.1f}%)")

    for ax in (ax1, ax2):
        ax.set_xscale("log", base=2)
        ax.set_xticks(K_VALUES)
        ax.set_xticklabels(K_VALUES)
        ax.set_xlabel("K (shots accumulated)")
        ax.grid(True, alpha=0.3)
    ax1.set_ylabel("hit_rate @ 200mm  (%)")
    ax1.set_ylim(0, 105)
    ax1.set_title("hit_rate vs accumulated shots (5 samples × 3 trials, shaded = ±1 σ)")
    ax1.legend(fontsize=8, loc="lower right")
    ax2.set_ylabel("RMSE (mm)")
    ax2.set_title("RMSE vs accumulated shots")
    ax2.legend(fontsize=8, loc="upper right")

    fig.suptitle(
        f"PF32 prep — Stage B: K-shot accumulation curves "
        f"(Gutierrez 64×64, SBR≈0.2, msph≈2, IRF σ={IRF_SIGMA})",
        fontsize=12,
    )
    fig.tight_layout()
    png_path = OUT_DIR / "B_accumulation_curves.png"
    fig.savefig(png_path, dpi=150)
    print(f"\nCSV: {csv_path}")
    print(f"PNG: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
