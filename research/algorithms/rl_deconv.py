"""
algorithms/rl_deconv.py — Richardson-Lucy 反卷积深度估计

功能
----
对每像素 TCSPC 直方图执行 Richardson-Lucy（RL）迭代反卷积：用高斯 IRF
去除系统响应函数展宽，得到更尖锐的光子分布估计，再对反卷积结果做
argmax 得到峰值 bin，最终换算为毫米深度。

上游
----
- 输入：``sim_spad_loader.SpadSample``（hist 形状 (H, W, BINS)）
- 配置：``RLDeconvConfig``（IRF 宽度、迭代次数、防除零 eps、有效性阈值）

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"rl_deconv_i<n_iter>"``
- 被 ``run_sanity / run_benchmark / run_accumulation / run_verify_baseline`` 调

依赖
----
- numpy（FFT 向量化，全帧并行，无像素循环）
- ``contracts.AlgoConfig``, ``contracts.DepthEstimate``
- ``sim_spad_loader.BINS`` 用于 reverse 方向 bin 翻转

备注
----
- IRF 建模为零中心高斯，用循环 padding（exp 双峰叠加）保证 FFT 循环卷积
  正确；单位能量归一化。
- RL 迭代基于 FFT 循环卷积（irfft 需显式指定 n=BINS），避免每步对 H×W
  像素独立做 1D 卷积。
- 有效性判断用原始 hist 的 max（peak_val），而非反卷积后的 est；
  confidence 为全图 peak_val 相对最大值的归一化，仅供排序/画图用。
- algo_name 包含迭代次数，便于对比不同 n_iter 的精度-速度权衡。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class RLDeconvConfig(AlgoConfig):
    irf_sigma_bins: float = 2.5   # Gaussian IRF 宽度（bins）
    n_iter: int = 10              # 迭代次数（10-20 通常够）
    eps: float = 1e-9             # 防除零
    min_counts: float = 1.0      # argmax 有效性阈值（原始 hist 峰值）


def _gaussian_irf(n_bins: int, sigma: float) -> np.ndarray:
    """Zero-centred Gaussian IRF with circular padding, unit energy.

    Uses double-Gaussian trick so the tail wraps correctly for FFT
    circular convolution: exp(-0.5*(t/sigma)^2) + exp(-0.5*((t-n_bins)/sigma)^2).
    """
    t = np.arange(n_bins, dtype=np.float64)
    g = np.exp(-0.5 * (t / sigma) ** 2) + np.exp(-0.5 * ((t - n_bins) / sigma) ** 2)
    return (g / g.sum()).astype(np.float64)


def estimate(sample, cfg: RLDeconvConfig | None = None) -> DepthEstimate:
    """Estimate depth via Richardson-Lucy deconvolution of per-pixel histograms."""

    if cfg is None:
        cfg = RLDeconvConfig()

    hist = sample.hist.astype(np.float64)   # (H, W, BINS)
    H, W, B = hist.shape

    irf = _gaussian_irf(B, cfg.irf_sigma_bins)          # (BINS,)
    IRF_fft = np.fft.rfft(irf)                          # (BINS//2+1,)
    IRF_flip_fft = np.fft.rfft(irf[::-1])               # (BINS//2+1,)

    est = hist.copy()

    for _ in range(cfg.n_iter):
        # Full-frame FFT along bin axis — (H, W, BINS//2+1)
        EST_fft = np.fft.rfft(est, axis=2)
        conv = np.fft.irfft(EST_fft * IRF_fft, n=B, axis=2)   # (H, W, BINS)

        ratio = hist / np.clip(conv, cfg.eps, None)             # (H, W, BINS)

        R_fft = np.fft.rfft(ratio, axis=2)
        correction = np.fft.irfft(R_fft * IRF_flip_fft, n=B, axis=2)

        est = np.clip(est * correction, 0, None)

    # argmax on deconvolved estimate; validity from original hist
    peak_bin = est.argmax(axis=2)                               # (H, W) int
    peak_val = sample.hist.max(axis=2).astype(np.float32)      # (H, W) float32

    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0
    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop!r}")

    valid = peak_val >= cfg.min_counts
    depth_mm[~valid] = 0.0

    max_peak = float(peak_val.max()) if peak_val.size else 0.0
    if max_peak > 0:
        confidence = (peak_val / max_peak).astype(np.float32)
    else:
        confidence = np.zeros_like(peak_val, dtype=np.float32)
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name=f"rl_deconv_i{cfg.n_iter}",
        extras={"peak_bin": peak_bin, "n_iter": cfg.n_iter},
    )
