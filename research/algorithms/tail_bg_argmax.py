"""
algorithms/tail_bg_argmax.py — 尾部背景估计 + argmax

功能
----
取直方图末端 N 个 bin（远距区，假设无目标）的均值作为均匀背景估计，
逐 bin 减去后再 argmax。不依赖 IRF，对均匀背景天然有效。

上游
----
- 输入：``sim_spad_loader.SpadSample``
- 配置：``TailBgArgmaxConfig(tail_bins=100, min_counts=0.0)``
  - ``tail_bins`` 太小 → 背景估计噪声；太大 → 把目标也包进去

下游
----
- 返回 ``contracts.DepthEstimate``，algo_name=``"tail_bg_argmax_t{N}"``
- 通过 ``extras["bg_level"]`` 暴露背景估计（(H,W) 数组）供下游用

依赖
----
- numpy
- ``sim_spad_loader.BINS``

备注
----
- 注意 ``start_stop`` 方向：loader 在 reverse 模式下会把 hist 翻转，所以**这里统一
  取末尾 100 bin**——对 forward 数据是远距大 bin，对 reverse 数据已被 loader 翻成远距。
- 与 ``bg_sub_argmax`` 是**互补**的：一个抑制时序背景，一个增加空间光子；理论上可叠加。
- **未接入 run_sanity**，待补；下一步 Step 2 该跑一遍 5 样本均值。
- 雾天指数背景（近距强尾巴）不能用 tail 估计——尾部 bin 在 reverse 下反而是雾峰
  最强处。雾天版应改成"近距尾"或用指数模型拟合（参考 M2R3D / Tobin 2021）。
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
