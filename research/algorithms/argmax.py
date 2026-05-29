"""
algorithms/argmax.py — 朴素峰值检测 baseline

功能
----
对每像素 SPAD 直方图取 ``argmax(hist, axis=2)``，按 ``start_stop`` 方向
把 bin 索引换算成毫米深度。零参数、O(B)。

上游
----
- 输入：``sim_spad_loader.SpadSample``（hist 形状 (H, W, BINS)）
- 配置：``ArgmaxConfig(min_counts=1.0)``——峰值低于该阈值的像素置为无效

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"argmax_v0"``
- 被 ``run_sanity / run_benchmark / run_accumulation / run_verify_baseline`` 调

依赖
----
- numpy
- ``sim_spad_loader.BINS`` 仅用于 reverse 方向的 bin 翻转

备注
----
- 与 Gutierrez 数据集 ``est_range_bins_argmax`` **算法等价**；修好 loader 的
  F-order bug 后，5 样本均值 hit@200mm 实测 0.579 ≈ ds_argmax 0.580。
- 不做任何背景扣除——低 SBR 下被噪声峰带飞是预期行为；要改善去看
  ``tail_bg_argmax`` / ``lmf`` / ``bg_sub_argmax``（空间池化）。
- 输出 confidence = peak_val / max_peak（全图归一），不是绝对置信度，
  仅供画图排序用。
"""
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
