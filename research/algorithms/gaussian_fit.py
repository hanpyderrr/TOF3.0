"""
algorithms/gaussian_fit.py — Gaussian 子 bin 拟合深度估计

功能
----
在 argmax 整数 bin 附近对每像素直方图做四参数 Gaussian 拟合（含背景偏置），
提取连续峰位 μ，将量化误差从 ±1 bin（±8.25 mm）降至亚 bin 水平。
拟合失败时可选 fallback 到整数 argmax，也可直接标无效。

上游
----
- 输入：``sim_spad_loader.SpadSample``（hist 形状 (H, W, BINS)）
- 配置：``GaussianFitConfig(half_win=4, min_counts=3.0, fallback_to_argmax=True)``
  - half_win      : 拟合窗口半径（bin），共 2*half_win+1 个采样点
  - min_counts    : 峰值光子数最低阈值，低于此的像素直接标无效
  - fallback_to_argmax : 拟合失败时是否回退到整数 argmax（否则标无效）

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"gauss_fit"``
- 可被 ``run_sanity / run_benchmark / run_accumulation / run_verify_baseline`` 调

依赖
----
- numpy
- scipy.optimize.curve_fit
- ``sim_spad_loader.BINS`` 用于 reverse 方向的 bin 翻转

备注
----
- 全帧 argmax 向量化；拟合部分逐像素（scipy.optimize.curve_fit 不支持批量）。
  对 64×64 帧（~3000 有效像素）单帧拟合时间约 0.5–2 s，适合离线评估。
- 拟合模型：f(x) = A * exp(-(x-mu)^2 / (2*sig^2)) + bg
  初始值：A=h_win.max(), mu=pk（整数 bin）, sig=1.5, bg=h_win.min()
  bounds：A>0, mu 在 [pk-half_win, pk+half_win], sig∈[0.5,5], bg≥0
- 拟合失败条件：scipy 抛出 RuntimeError（达到迭代上限）或协方差含 inf。
- confidence 基于整数 argmax 的峰高全图归一化（与 argmax_v0 可比）。
- 窗口靠近 bin=0 或 bin=BINS-1 时自动 clip，但窗口过窄（<3 点）时强制标无效。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class GaussianFitConfig(AlgoConfig):
    half_win: int = 4            # fit window: [peak-half_win, peak+half_win], 2*half_win+1 bins
    min_counts: float = 1.0      # minimum peak photon count; below this pixel is invalid
    fallback_to_argmax: bool = True  # use integer argmax when curve_fit fails


def _gauss_bg(x: np.ndarray, A: float, mu: float, sig: float, bg: float) -> np.ndarray:
    """Four-parameter Gaussian with constant background."""
    return A * np.exp(-0.5 * ((x - mu) / sig) ** 2) + bg


def estimate(sample, cfg: GaussianFitConfig | None = None) -> DepthEstimate:
    """Estimate depth with sub-bin precision via per-pixel Gaussian fitting."""

    if cfg is None:
        cfg = GaussianFitConfig()

    hist = sample.hist          # (H, W, BINS), float32
    H, W, B = hist.shape

    # --- Step 1: vectorised argmax and peak value over entire frame ---
    peak_bin = hist.argmax(axis=2)                       # (H, W), int
    peak_val = hist.max(axis=2).astype(np.float32)       # (H, W)

    # --- Step 2: validity mask based on min_counts threshold ---
    valid = peak_val >= cfg.min_counts                   # (H, W), bool

    # mu_subbin holds the continuous peak position (float bin index)
    mu_subbin = peak_bin.astype(np.float32).copy()       # initialise with integer argmax

    half = cfg.half_win

    # --- Step 3: per-pixel Gaussian fit ---
    ys, xs = np.where(valid)
    for y, x in zip(ys, xs):
        pk = int(peak_bin[y, x])

        # Clipped window bounds
        lo = max(0, pk - half)
        hi = min(B - 1, pk + half)

        # x-axis in bin units (float), window values
        x_win = np.arange(lo, hi + 1, dtype=np.float64)
        h_win = hist[y, x, lo:hi + 1].astype(np.float64)

        n_pts = len(x_win)
        if n_pts < 3:
            # Window too narrow to fit; fallback handled below
            if not cfg.fallback_to_argmax:
                valid[y, x] = False
            # mu_subbin already holds integer peak_bin — keep as-is for fallback
            continue

        # Initial parameter guess
        A0 = float(h_win.max())
        mu0 = float(pk)
        sig0 = 1.5
        bg0 = float(h_win.min())

        # Bounds: A>0, mu within window, sig in [0.5,5], bg>=0
        lower = [0.0,   float(lo),   0.5,  0.0]
        upper = [np.inf, float(hi),  5.0,  np.inf]

        fit_ok = False
        try:
            popt, pcov = curve_fit(
                _gauss_bg,
                x_win,
                h_win,
                p0=[A0, mu0, sig0, bg0],
                bounds=(lower, upper),
                maxfev=400,
            )
            # Reject if covariance is degenerate
            if np.all(np.isfinite(pcov)):
                mu_subbin[y, x] = np.float32(popt[1])
                fit_ok = True
        except RuntimeError:
            pass  # curve_fit did not converge

        if not fit_ok:
            if not cfg.fallback_to_argmax:
                valid[y, x] = False
            # mu_subbin already holds integer peak_bin — keep for fallback

    # --- Step 4: convert sub-bin position to depth_mm ---
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = mu_subbin * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - mu_subbin) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop!r}")

    depth_mm = depth_mm.astype(np.float32, copy=False)
    depth_mm[~valid] = 0.0

    # --- Step 5: confidence from raw argmax peak height, full-frame normalised ---
    max_peak = float(peak_val.max()) if peak_val.size else 0.0
    if max_peak > 0:
        confidence = (peak_val / max_peak).astype(np.float32)
    else:
        confidence = np.zeros_like(peak_val, dtype=np.float32)
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name="gauss_fit",
        extras={
            "peak_bin": peak_bin,
            "peak_val": peak_val,
            "mu_subbin": mu_subbin,
        },
    )
