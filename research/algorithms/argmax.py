"""Argmax baseline for SPAD histograms."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class ArgmaxConfig(AlgoConfig):
    min_counts: float = 1.0


def estimate(sample, cfg: ArgmaxConfig | None = None) -> DepthEstimate:
    """Estimate depth by selecting the peak histogram bin per pixel."""

    if cfg is None:
        cfg = ArgmaxConfig()

    hist = sample.hist
    peak_bin = hist.argmax(axis=2)
    peak_val = hist.max(axis=2).astype(np.float32, copy=False)
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop}")

    valid = peak_val >= cfg.min_counts
    depth_mm = depth_mm.astype(np.float32, copy=False)
    depth_mm[~valid] = 0.0

    max_peak = float(peak_val.max()) if peak_val.size else 0.0
    if max_peak > 0:
        confidence = (peak_val / max_peak).astype(np.float32, copy=False)
    else:
        confidence = np.zeros_like(peak_val, dtype=np.float32)
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name="argmax_v0",
        extras={"peak_bin": peak_bin, "peak_val": peak_val},
    )
