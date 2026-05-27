"""Spatial-pooling argmax: aggregate neighbor histograms before peak detection.

Summing K×K neighbor histograms multiplies effective photon counts by K²,
raising SNR enough for argmax to find the true signal peak even at low SBR.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class SpatialArgmaxConfig(AlgoConfig):
    kernel: int = 3       # spatial pooling window (must be odd)
    min_counts: float = 1.0


def estimate(sample, cfg: SpatialArgmaxConfig | None = None) -> DepthEstimate:
    """Pool histograms over a K×K spatial window, then take argmax.

    Summing K² neighbors boosts effective signal photons by K², making
    the signal peak distinguishable from background noise at low SBR.
    """
    if cfg is None:
        cfg = SpatialArgmaxConfig()

    try:
        from scipy.ndimage import uniform_filter
    except ImportError as e:
        raise RuntimeError("scipy is required") from e

    hist = sample.hist  # (H, W, BINS) float32
    k = cfg.kernel

    # spatial sum over K×K window via uniform_filter (mode='reflect' pads edges)
    hist_pooled = uniform_filter(hist, size=(k, k, 1), mode="reflect") * (k * k)
    hist_pooled = hist_pooled.astype(np.float32)

    peak_bin = hist_pooled.argmax(axis=2)
    peak_val = hist_pooled.max(axis=2).astype(np.float32)

    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop}")

    valid = peak_val >= cfg.min_counts
    depth_mm[~valid] = 0.0

    max_peak = float(peak_val.max()) if peak_val.size else 0.0
    confidence = (peak_val / max_peak).astype(np.float32) if max_peak > 0 else np.zeros_like(peak_val)
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name=f"spatial_argmax_{k}x{k}",
        extras={"peak_bin": peak_bin, "kernel": k},
    )
