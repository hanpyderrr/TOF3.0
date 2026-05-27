"""Evaluation metrics for depth estimates."""
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
