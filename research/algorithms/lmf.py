"""Matched Filter depth estimation with Gaussian IRF approximation.

Cross-correlates each pixel's TCSPC histogram with a Gaussian model of the
system IRF (laser pulse + detector jitter), then picks the peak lag as the
depth estimate.  This is equivalent to a matched filter and maximises SNR
against a flat background, making it significantly more robust than argmax
at low SBR.

The IRF sigma controls the effective filter bandwidth:
  - too narrow → noisy (overfit to noise spikes)
  - too wide  → biased toward background humps
A sigma of 2–3 bins (≈160–240 ps for 80 ps/bin) is a reasonable default.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class LMFConfig(AlgoConfig):
    irf_sigma_bins: float = 2.5   # Gaussian IRF width (bins)
    min_corr: float = 0.0         # minimum correlation peak to declare valid


def _gaussian_irf(n_bins: int, sigma: float) -> np.ndarray:
    """Unit-energy Gaussian IRF for circular cross-correlation (zero-centred)."""
    t = np.arange(n_bins, dtype=np.float64)
    # Primary lobe at t=0, wrap-around lobe for circular FFT
    g = np.exp(-0.5 * (t / sigma) ** 2) + np.exp(-0.5 * ((t - n_bins) / sigma) ** 2)
    return (g / g.sum()).astype(np.float64)


def estimate(sample, cfg: LMFConfig | None = None) -> DepthEstimate:
    """Gaussian matched-filter depth estimate via FFT cross-correlation."""
    if cfg is None:
        cfg = LMFConfig()

    hist = sample.hist.astype(np.float64)  # (H, W, BINS)
    H, W, B = hist.shape

    irf = _gaussian_irf(B, cfg.irf_sigma_bins)           # (B,)
    IRF_conj = np.conj(np.fft.rfft(irf))                 # (B//2+1,)

    # Batch FFT across all pixels, correlate, IFFT
    HIST = np.fft.rfft(hist, axis=2)                     # (H, W, B//2+1)
    corr = np.fft.irfft(HIST * IRF_conj, n=B, axis=2)   # (H, W, B)
    corr = corr.astype(np.float32)

    peak_bin = corr.argmax(axis=2)                       # (H, W)
    peak_val = corr.max(axis=2).astype(np.float32)

    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop!r}")

    valid = peak_val > cfg.min_corr
    depth_mm[~valid] = 0.0

    max_val = float(peak_val.max()) if peak_val.size else 0.0
    confidence = (
        (peak_val / max_val).astype(np.float32) if max_val > 0
        else np.zeros_like(peak_val)
    )
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name=f"lmf_s{cfg.irf_sigma_bins:.1f}",
        extras={"peak_bin": peak_bin, "irf_sigma_bins": cfg.irf_sigma_bins},
    )
