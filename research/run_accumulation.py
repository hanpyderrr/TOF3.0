"""
run_accumulation.py — 多帧累加（K-shot integration）实验

功能
----
按物理一致方式合成 K 次曝光累加直方图（不是直接采样 rates，避免信号被烘焙）：
  - signal: 每像素 Poisson(msph) 个光子，按高斯 IRF 投到 GT 深度附近的 bins
  - background: 每像素 Poisson(mbph) 个光子，均匀分布在所有 BINS
K 从 1 到 64 扫，每个 K 取多次 trial 平均。

上游
----
- 命令行：``[mat_file]`` ``--trials 5`` ``--irf-sigma 2.5`` ``--save``
- ``sim_spad_loader.load_spad_mat`` 拿 GT depth / msph / sbr / IRF 配置
- ``algorithms/{argmax, lmf, bg_sub_argmax}`` 在累加后的 hist 上跑

下游
----
- 控制台 "K × algo × hit_rate" 表
- ``--save`` 写 ``research/out/<sample_id>_accumulation.png``（双面板：hit/RMSE vs K，
  含 ds_argmax / ds_lmf / real-spad-K=1 水平参考线）

依赖
----
- matplotlib（Agg 后端，--save 时）
- numpy

备注
----
- K_VALUES 默认 [1,2,4,8,16,32,64]——log2 等距
- mbph 由 msph / SBR 算得；每帧背景率 = mbph / BINS
- **物理上限**：当 K·msph >> 1 后信号峰已远超背景方差，hit_rate 趋近 100%
- 真实 spad 字段对应 K=1（但只有一次抽样，方差大）；本脚本提供多 trial 统计
- 是 Step 3"工程上要做多长积分时间"的标准答案
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import dataclasses

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms import argmax, bg_sub_argmax, lmf
from eval.metrics import compute_all, hit_rate as hit_rate_fn
from sim_spad_loader import load_spad_mat, SpadSample, BINS, bin_to_mm

K_VALUES  = [1, 2, 4, 8, 16, 32, 64]
TRIALS    = 5
IRF_SIGMA = 2.5   # bins — Gaussian approximation of system IRF


def _find_first_mat() -> Path:
    for mat in sorted((ROOT / "datasets").rglob("*.mat")):
        return mat
    raise FileNotFoundError("no .mat files under datasets/")


def _simulate_k_shots(sample: SpadSample, K: int, irf_sigma: float,
                      rng: np.random.Generator) -> np.ndarray:
    """Physically correct K-shot accumulation.

    Returns accumulated histogram (H, W, BINS) float32.
    """
    H, W = sample.depth_mm.shape
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    msph = sample.mean_signal_photons or 2.0
    sbr  = sample.sbr or 0.2
    mbph = msph / sbr          # background photons per pixel per shot

    # GT bin for each pixel (used to place signal photons)
    gt_bin = np.round(sample.depth_mm / bin_mm).astype(np.int32)
    gt_bin = np.clip(gt_bin, 0, BINS - 1)
    valid  = sample.depth_mm > 0

    # Precompute signal probability distribution: Gaussian IRF around each GT bin
    t = np.arange(BINS, dtype=np.float32)
    dt = t[None, None, :] - gt_bin[:, :, None].astype(np.float32)
    sig_prob = np.exp(-0.5 * (dt / irf_sigma) ** 2)
    sig_prob[~valid] = 0.0
    prob_sum = sig_prob.sum(axis=2, keepdims=True)
    sig_prob = np.where(prob_sum > 0, sig_prob / prob_sum, 0.0)

    # Accumulate K shots
    accum = np.zeros((H, W, BINS), dtype=np.float32)
    bg_rate_per_bin = mbph / BINS

    for _ in range(K):
        # Background: Poisson(bg_rate_per_bin) per bin
        bg = rng.poisson(bg_rate_per_bin, size=(H, W, BINS)).astype(np.float32)

        # Signal: draw total signal photons per pixel, distribute via sig_prob
        sig_total = rng.poisson(msph, size=(H, W))
        sig_hist = rng.poisson(
            sig_total[:, :, None].astype(np.float32) * sig_prob
        ).astype(np.float32)

        accum += bg + sig_hist

    return accum


def _run_algos(hist: np.ndarray, sample_ref: SpadSample) -> dict[str, dict]:
    s = dataclasses.replace(sample_ref, hist=hist)
    return {
        "argmax":      compute_all(argmax.estimate(s), s),
        "lmf":         compute_all(lmf.estimate(s), s),
        "spatial_3x3": compute_all(bg_sub_argmax.estimate(s), s),
    }


def _ds_hit(sample: SpadSample, attr: str) -> float:
    bins = getattr(sample, attr, None)
    if bins is None:
        return float("nan")
    pred_mm = np.asarray(
        bin_to_mm(bins.astype(np.float32), sample.start_stop, sample.bin_size_ps)
    )
    return hit_rate_fn(pred_mm, sample.depth_mm)


def _actual_spad_hit(sample: SpadSample) -> float:
    m = compute_all(argmax.estimate(sample), sample)
    return m["hit_rate"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mat_file", nargs="?")
    parser.add_argument("--trials",    type=int,   default=TRIALS)
    parser.add_argument("--irf-sigma", type=float, default=IRF_SIGMA)
    parser.add_argument("--save",      action="store_true")
    args = parser.parse_args(argv)

    mat_path = Path(args.mat_file) if args.mat_file else _find_first_mat()
    sample   = load_spad_mat(mat_path, start_stop="forward")

    msph = sample.mean_signal_photons or 2.0
    sbr  = sample.sbr or 0.2
    mbph = msph / sbr

    print(f"\n[accum] {sample.sample_id}")
    print(f"  SBR={sbr}  msph={msph}  mbph={mbph:.1f}")
    print(f"  P(0 signal per pixel per shot) = exp(-msph) = {np.exp(-msph) * 100:.1f}%")
    print(f"  IRF sigma = {args.irf_sigma} bins\n")

    rng = np.random.default_rng(seed=42)
    algo_names = ["argmax", "lmf", "spatial_3x3"]

    col = 13
    print(f"{'K':>6}  {'trials':>6}", end="")
    for a in algo_names:
        print(f"  {a:>{col}}", end="")
    print()
    print("-" * (6 + 8 + len(algo_names) * (col + 2)))

    rows = []
    for K in K_VALUES:
        hit_acc  = {a: [] for a in algo_names}
        rmse_acc = {a: [] for a in algo_names}

        for _ in range(args.trials):
            hist_k = _simulate_k_shots(sample, K, args.irf_sigma, rng)
            m = _run_algos(hist_k, sample)
            for a in algo_names:
                hit_acc[a].append(m[a]["hit_rate"])
                rmse_acc[a].append(m[a]["rmse_mm"])

        row = {"K": K}
        print(f"{K:>6}  {args.trials:>6}", end="")
        for a in algo_names:
            mh = float(np.mean(hit_acc[a]))
            row[f"{a}_hit"]  = mh
            row[f"{a}_rmse"] = float(np.mean(rmse_acc[a]))
            print(f"  {mh * 100:>{col}.1f}%", end="")
        print()
        rows.append(row)

    print()
    real_hit = _actual_spad_hit(sample)
    print(f"  real spad argmax (K=1): {real_hit * 100:.1f}%")
    print(f"  ds_argmax reference:    {_ds_hit(sample, 'est_argmax_bins') * 100:.1f}%")
    print(f"  ds_lmf    reference:    {_ds_hit(sample, 'est_lmf_bins') * 100:.1f}%")
    print(f"  ds_zncc   reference:    {_ds_hit(sample, 'est_zncc_bins') * 100:.1f}%")

    if args.save:
        _save_plot(rows, algo_names, sample, args)

    return 0


def _save_plot(rows: list[dict], algo_names: list[str],
               sample: SpadSample, args) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ks = [r["K"] for r in rows]
    colors = {"argmax": "tab:blue", "lmf": "tab:orange", "spatial_3x3": "tab:green"}

    for a in algo_names:
        ax1.plot(ks, [r[f"{a}_hit"]  * 100 for r in rows], marker="o",
                 label=a, color=colors.get(a))
        ax2.plot(ks, [r[f"{a}_rmse"] for r in rows], marker="o",
                 label=a, color=colors.get(a))

    da = _ds_hit(sample, "est_argmax_bins")
    dl = _ds_hit(sample, "est_lmf_bins")
    ax1.axhline(da * 100, ls="--", color="gray",  alpha=0.8,
                label=f"ds_argmax ({da * 100:.0f}%)")
    ax1.axhline(dl * 100, ls=":",  color="black", alpha=0.8,
                label=f"ds_lmf ({dl * 100:.0f}%)")
    ax1.axhline(_actual_spad_hit(sample) * 100, ls="-.", color="red", alpha=0.6,
                label=f"real spad K=1 ({_actual_spad_hit(sample) * 100:.0f}%)")

    for ax in (ax1, ax2):
        ax.set_xscale("log", base=2)
        ax.set_xlabel("K (shots accumulated)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    ax1.set_ylabel("hit_rate (%)")
    ax2.set_ylabel("RMSE (mm)")
    title = (f"{sample.sample_id}  SBR={sample.sbr}  "
             f"msph={sample.mean_signal_photons}  IRF σ={args.irf_sigma}b")
    ax1.set_title(f"hit_rate vs K  [{title}]")
    ax2.set_title(f"RMSE vs K  [{title}]")
    plt.tight_layout()

    out = ROOT / "out" / f"{sample.sample_id}_accumulation.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"\n[accum] saved: {out}")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
