"""
algorithms/tail_bg_argmax.py — 尾部背景估计 + argmax

功能
----
取直方图远端 N 个 bin（假设无目标信号）的均值作为均匀背景估计，
逐 bin 减去后再 argmax。不依赖 IRF，对均匀背景天然有效。

上游
----
- 输入：``sim_spad_loader.SpadSample``
- 配置：``TailBgArgmaxConfig(tail_bins=100, min_counts=0.0, tail_side="auto")``
  - ``tail_bins`` 太小 → 背景估计噪声；太大 → 把目标也包进去
  - ``tail_side`` 控制从哪端取背景（详见备注）

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
loader 对 reverse start_stop 已翻转 hist，翻转后：
  index 0 = 远端（原 bin BINS-1），index BINS-1 = 近端（原 bin 0）

tail_side 选项：
  "far"（推荐）：始终取远端 N bin 做背景估计
    forward → 取末尾 N bin（index BINS-N .. BINS-1 = 远端）
    reverse → 取首部 N bin（index 0 .. N-1 = 远端，因翻转后远端在最前）
  "near"：始终取近端 N bin（雾天近端散射强，不适合做背景，仅对比用）
  "auto"：等同 "far"

雾天正确用法：``tail_side="far"``（默认）。
若 ``tail_side="last"``（历史默认行为），reverse 时取的是近端强散射区，背景高估
会把目标峰也减掉，雾天 reverse 数据必崩。

与 ``bg_sub_argmax`` 互补：一个抑制时序背景，一个增加空间光子；理论上可叠加。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class TailBgArgmaxConfig(AlgoConfig):
    tail_bins: int = 100
    min_counts: float = 0.0
    tail_side: Literal["far", "near", "auto"] = "far"


def estimate(sample, cfg: TailBgArgmaxConfig | None = None) -> DepthEstimate:
    """Subtract far-range background estimate, then argmax the residual."""
    if cfg is None:
        cfg = TailBgArgmaxConfig()

    hist = sample.hist  # (H, W, BINS), loader已对reverse翻转：index0=远端, BINS-1=近端

    side = cfg.tail_side
    if side == "auto":
        side = "far"

    # loader翻转后：index 0=远端，index BINS-1=近端
    # far  → forward取末尾（远端），reverse取首部（远端）
    # near → forward取首部（近端），reverse取末尾（近端）
    if side == "far":
        if sample.start_stop == "reverse":
            tail = hist[:, :, :cfg.tail_bins]   # 首部 = 远端
        else:
            tail = hist[:, :, -cfg.tail_bins:]  # 末尾 = 远端
    else:  # "near"
        if sample.start_stop == "reverse":
            tail = hist[:, :, -cfg.tail_bins:]  # 末尾 = 近端
        else:
            tail = hist[:, :, :cfg.tail_bins]   # 首部 = 近端

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
