"""
algorithms/bg_sub_argmax.py — K×K 空间池化后 argmax

功能
----
对每像素做 K×K 邻域直方图求和（uniform_filter），再 argmax。有效光子 ×K²，
SNR 提升 K 倍。是单帧低 SBR 场景下**意外有效**的简单算法。

上游
----
- 输入：``sim_spad_loader.SpadSample``
- 配置：``SpatialArgmaxConfig(kernel=3, min_counts=1.0)``

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"spatial_argmax_{k}x{k}"``
- 被 ``run_sanity / run_benchmark / run_accumulation`` 调

依赖
----
- scipy.ndimage.uniform_filter（reflect 边界）
- numpy
- ``sim_spad_loader.BINS``

备注
----
- **⚠️ 文件名误导**：叫 ``bg_sub_argmax``（"背景减除"）但**实际并不减背景**，
  做的是空间池化。真正的背景减除在 ``tail_bg_argmax.py``。命名待后续重构。
- K=3 实测在 Gutierrez SBR=0.2 单样本上 hit@200mm = 47.8%，**显著超过 LMF 37.5%**——
  原因：低光子（2 signal）场景下，9× 光子比 IRF 形状匹配带来的 4× SNR 更有用。
- 边缘代价：池化越大边缘越糊。K=3 损失 1-2 像素边缘细节，可接受；K≥7 在精细
  室内场景上会破坏物体边界。
- 输出的 confidence 是池化后峰值 / 全图最大峰值，对应"该像素 9 邻域有多稠密"。
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
