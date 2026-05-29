"""
eval/metrics.py — 深度估计评估指标

功能
----
对一对 (pred, gt) 深度图算 RMSE 和 hit_rate。只在 ``gt > 0`` 的像素上计入。

上游
----
- ``contracts.DepthEstimate.depth_mm`` 作为 pred
- ``sim_spad_loader.SpadSample.depth_mm`` 作为 gt
- 入口脚本：``run_sanity / run_benchmark / run_accumulation / run_verify_baseline``

下游
----
- 控制台表格 / verify_baseline.md / benchmark_results.csv

依赖
----
- numpy

备注
----
- ``hit_rate`` 默认容差 ``tol_mm=200``（约 17 bin @80 ps/bin）；亚 bin 评估请显式传 12 或 24
- ``rmse`` 是有效像素上的平方误差均方根，对离群点敏感；hit_rate 更鲁棒
- ``valid_pred_ratio`` 与 ``valid_gt_ratio`` 用于诊断"是否大量像素被算法判无效"
- 不做距离条件分箱（远 vs 近表现）——那个在 run_benchmark / 后续 ROI 分层中做
"""
from __future__ import annotations

import numpy as np


def _mask(pred_mm, gt_mm, valid_mask=None) -> np.ndarray:
    gt = np.asarray(gt_mm)
    mask = gt > 0
    if valid_mask is not None:
        mask &= np.asarray(valid_mask, dtype=bool)
    return mask


def rmse(pred_mm, gt_mm, valid_mask=None) -> float:
    """RMSE over pixels with valid GT depth."""

    pred = np.asarray(pred_mm, dtype=np.float64)
    gt = np.asarray(gt_mm, dtype=np.float64)
    mask = _mask(pred, gt, valid_mask)
    if not np.any(mask):
        return float("nan")
    err = pred[mask] - gt[mask]
    return float(np.sqrt(np.mean(err**2)))


def hit_rate(pred_mm, gt_mm, tol_mm=200.0, valid_mask=None) -> float:
    """Fraction of valid-GT pixels within an absolute depth tolerance."""

    pred = np.asarray(pred_mm, dtype=np.float64)
    gt = np.asarray(gt_mm, dtype=np.float64)
    mask = _mask(pred, gt, valid_mask)
    if not np.any(mask):
        return float("nan")
    return float((np.abs(pred[mask] - gt[mask]) < tol_mm).mean())


def compute_all(estimate, sample, tol_mm=200.0) -> dict:
    """Compute standard per-frame metrics."""

    pred = np.asarray(estimate.depth_mm, dtype=np.float32)
    gt = np.asarray(sample.depth_mm, dtype=np.float32)
    return {
        "algo": estimate.algo_name,
        "rmse_mm": rmse(pred, gt),
        "hit_rate": hit_rate(pred, gt, tol_mm=tol_mm),
        "tol_mm": float(tol_mm),
        "valid_pred_ratio": float((pred > 0).mean()) if pred.size else float("nan"),
        "valid_gt_ratio": float((gt > 0).mean()) if gt.size else float("nan"),
    }
