"""
algorithms/poisson_mle.py — Poisson 最大似然深度估计

功能
----
对每像素 TCSPC 直方图，在泊松噪声假设下计算各候选深度的对数似然，
取 argmax 得到深度估计。相比 LMF（隐含高斯噪声假设），Poisson MLE
在低光子数场景下理论上更优。

核心近似：将 log-likelihood 的主导项拆解为直方图与 log(IRF) 的互相关，
用 FFT 一次性算出所有候选深度的分数，避免逐深度循环，全程向量化。

上游
----
- 输入：``sim_spad_loader.SpadSample``（hist 形状 (H, W, BINS)）
- 配置：``PoissonMLEConfig(irf_sigma_bins, bg_percentile, min_counts, eps)``

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"poisson_mle"``
- 被 ``run_sanity / run_benchmark / run_accumulation / run_verify_baseline`` 调

依赖
----
- numpy（FFT 用 ``np.fft.rfft/irfft``）
- ``contracts.AlgoConfig``、``contracts.DepthEstimate``
- ``sim_spad_loader.BINS``

备注
----
- IRF 使用 Gaussian 近似（circular wrap），与 lmf.py 保持一致。
- log-likelihood 中的惩罚项 ``-Σ(A·IRF_shifted + bg)`` 对所有候选深度为常数，
  不影响 argmax，故被省略（见实现注释）。
- confidence 由各像素 log_L 的 max 值全局归一化得到，仅供排序/可视化用。
- 背景估计用 ``np.percentile``（轴2），低 SBR 下可适当降低 bg_percentile。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class PoissonMLEConfig(AlgoConfig):
    irf_sigma_bins: float = 2.5   # Gaussian IRF width (bins)
    bg_percentile: float = 10.0   # percentile for per-pixel background estimation
    min_counts: float = 1.0       # minimum peak photon count to declare valid
    eps: float = 1e-9             # numerical stability in log


def _gaussian_irf(n_bins: int, sigma: float) -> np.ndarray:
    """Unit-energy Gaussian IRF centred at bin 0, with circular wrap (float64)."""
    t = np.arange(n_bins, dtype=np.float64)
    g = np.exp(-0.5 * (t / sigma) ** 2) + np.exp(-0.5 * ((t - n_bins) / sigma) ** 2)
    return g / g.sum()


def estimate(sample, cfg: PoissonMLEConfig | None = None) -> DepthEstimate:
    """Poisson MLE depth estimate via FFT cross-correlation of hist with log(IRF)."""
    if cfg is None:
        cfg = PoissonMLEConfig()

    hist = sample.hist.astype(np.float64)  # (H, W, BINS)

    # --- Step 1: per-pixel background estimate (H, W, 1) ---
    bg = np.percentile(hist, cfg.bg_percentile, axis=2, keepdims=True)  # (H, W, 1)

    # --- Step 2: background-subtracted histogram, clipped to non-negative ---
    h_sub = np.clip(hist - bg, 0.0, None)  # (H, W, BINS)

    # --- Step 3: signal amplitude estimate (H, W, 1) ---
    # clip(min=1) avoids division-by-zero; will be masked out later via min_counts
    A = h_sub.sum(axis=2, keepdims=True).clip(min=1.0)  # (H, W, 1)

    # --- Step 4: Gaussian IRF centred at bin 0, circular-wrapped ---
    irf = _gaussian_irf(BINS, cfg.irf_sigma_bins)  # (BINS,)

    # --- Step 5: approximate log-likelihood via FFT cross-correlation ---
    #
    # Full Poisson log-likelihood per depth d:
    #   log L(d) = Σ_b [ h(b) * log(A * IRF_d(b) + bg + ε) - (A * IRF_d(b) + bg) ]
    #
    # Decompose into two terms:
    #   Term1 (dominant):
    #     Σ_b h(b) * log(A * IRF_d(b) + bg + ε)
    #     ≈ Σ_b h(b) * log(IRF_d(b) + ε)   when A >> bg   [const w.r.t. A absorbed]
    #     = cross-correlation of h_sub with log(irf + ε), computable via FFT
    #   Term2 (penalty):
    #     -Σ_b (A * IRF_d(b) + bg) = -A - bg * BINS
    #     → constant across all candidate depths d, does NOT affect argmax → omitted
    #
    # FFT cross-correlation:  log_L[..., d] = Σ_b h_sub[...,b] * log_irf[(b-d) % BINS]

    log_irf = np.log(irf + cfg.eps)                              # (BINS,)

    H_fft = np.fft.rfft(h_sub, axis=2)                          # (H, W, BINS//2+1)
    LOG_IRF_conj = np.conj(np.fft.rfft(log_irf))                # (BINS//2+1,)
    log_L = np.fft.irfft(H_fft * LOG_IRF_conj, n=BINS, axis=2)  # (H, W, BINS)

    # --- Step 6: argmax over candidate depths ---
    peak_bin = log_L.argmax(axis=2)   # (H, W)

    # --- Step 7: validity mask based on raw histogram peak ---
    peak_val = hist.max(axis=2).astype(np.float32)  # (H, W)
    valid = peak_val >= cfg.min_counts

    # --- Step 8: bin → depth_mm ---
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop!r}")

    depth_mm[~valid] = 0.0

    # --- Step 9: confidence from per-pixel log_L max, globally normalised to [0,1] ---
    log_L_max = log_L.max(axis=2).astype(np.float32)  # (H, W)
    l_min = float(log_L_max.min())
    l_ptp = float(log_L_max.max()) - l_min
    if l_ptp > cfg.eps:
        confidence = ((log_L_max - l_min) / l_ptp).astype(np.float32)
    else:
        confidence = np.zeros_like(log_L_max, dtype=np.float32)
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name="poisson_mle",
        extras={
            "peak_bin": peak_bin,
            "log_L_max": log_L_max,
            "bg_level": bg.squeeze(axis=2).astype(np.float32),
        },
    )
