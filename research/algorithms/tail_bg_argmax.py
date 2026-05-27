"""Tail-background-subtracted argmax.

Estimates the uniform background level from the far-range tail bins
(where no target signal is expected), subtracts it from every bin,
then applies argmax on the residual.

This works because true target photons cluster into a narrow peak while
background photons are spread uniformly — subtracting the tail mean
improves peak-to-background ratio without requiring an IRF.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class TailBgArgmaxConfig(AlgoConfig):
    tail_bins: int = 100    # tail bins used to estimate background level
    min_counts: float = 0.0 # minimum residual peak to declare valid


def estimate(sample, cfg: TailBgArgmaxConfig | None = None) -> DepthEstimate:
    """Subtract tail-estimated background, then argmax the residual."""
    if cfg is None:
        cfg = TailBgArgmaxConfig()

    hist = sample.hist  # (H, W, BINS) float32, already flipped for reverse start_stop

    # Tail = last `tail_bins` columns (far range, no signal expected in either direction
    # because loader already flips reverse histograms so index 0 = nearest, BINS-1 = farthest)
    tail = hist[:, :, -cfg.tail_bins:]          # (H, W, tail_bins)
    bg = tail.mean(axis=2, keepdims=True)        # (H, W, 1) uniform background estimate

    hist_sub = np.maximum(hist - bg, 0.0).astype(np.float32)

    peak_bin = hist_sub.argmax(axis=2)
    peak_val = hist_sub.max(axis=2).astype(np.float32)
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop!r}")

    valid = peak_val > cfg.min_counts
    depth_mm[~valid] = 0.0

    max_peak = float(peak_val.max()) if peak_val.size else 0.0
    confidence = (
        (peak_val / max_peak).astype(np.float32) if max_peak > 0
        else np.zeros_like(peak_val)
    )
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name=f"tail_bg_argmax_t{cfg.tail_bins}",
        extras={"bg_level": bg.squeeze(axis=2), "peak_bin": peak_bin},
    )
