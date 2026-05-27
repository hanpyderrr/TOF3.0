"""Visualization helpers for SPAD algorithm sanity checks."""
from __future__ import annotations

import numpy as np

from sim_spad_loader import BINS, bin_to_mm


def _select_pixel(gt: np.ndarray) -> tuple[int, int]:
    valid = gt > 0
    if not np.any(valid):
        return gt.shape[0] // 2, gt.shape[1] // 2
    median = np.median(gt[valid])
    score = np.where(valid, np.abs(gt - median), np.inf)
    flat = int(np.argmin(score))
    return np.unravel_index(flat, gt.shape)


def _mark(ax, pixel_yx, color: str) -> None:
    y, x = pixel_yx
    ax.plot(x, y, marker="+", color=color, markersize=12, markeredgewidth=2)


def plot_sanity_panel(sample, estimate, metrics, pixel_yx=None, title=""):
    """Build a 2x3 matplotlib sanity panel and return the Figure."""

    import matplotlib.pyplot as plt

    gt = np.asarray(sample.depth_mm, dtype=np.float32)
    pred = np.asarray(estimate.depth_mm, dtype=np.float32)
    if pixel_yx is None:
        pixel_yx = _select_pixel(gt)
    y, x = pixel_yx

    gt_plot = np.where(gt > 0, gt, np.nan)
    pred_plot = np.where(pred > 0, pred, np.nan)
    valid_gt = gt > 0
    vmin = float(np.nanmin(gt_plot)) if np.any(valid_gt) else 0.0
    vmax = float(np.nanmax(gt_plot)) if np.any(valid_gt) else 1.0

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    if title:
        fig.suptitle(title)

    ax = axes[0, 0]
    if sample.intensity is None:
        ax.text(0.5, 0.5, "No intensity", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        ax.imshow(sample.intensity, cmap="gray")
        _mark(ax, pixel_yx, "red")
        ax.set_title("Intensity")

    ax = axes[0, 1]
    im_gt = ax.imshow(gt_plot, cmap="plasma", vmin=vmin, vmax=vmax)
    _mark(ax, pixel_yx, "white")
    ax.set_title("GT depth (mm)")
    fig.colorbar(im_gt, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[0, 2]
    im_pred = ax.imshow(pred_plot, cmap="plasma", vmin=vmin, vmax=vmax)
    _mark(ax, pixel_yx, "white")
    ax.set_title("Pred depth (mm)")
    fig.colorbar(im_pred, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[1, 0]
    hist = sample.hist[y, x]
    bins_m = bin_to_mm(np.arange(BINS), sample.start_stop, sample.bin_size_ps) / 1000.0
    width = abs(float(bins_m[1] - bins_m[0])) if BINS > 1 else 0.001
    ax.bar(bins_m, hist, width=width, color="#4f6f9f")
    gt_m = gt[y, x] / 1000.0
    pred_m = pred[y, x] / 1000.0
    ax.axvline(gt_m, color="green", linestyle="--", label=f"GT {gt_m:.2f}m")
    ax.axvline(pred_m, color="red", linestyle="-", label=f"Pred {pred_m:.2f}m")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Counts")
    ax.set_title(f"Histogram ({y}, {x})")
    ax.legend()

    ax = axes[1, 1]
    err = np.where(valid_gt, np.abs(pred - gt), np.nan)
    im_err = ax.imshow(err, cmap="hot_r", vmin=0, vmax=500)
    ax.set_title("Absolute error (mm)")
    fig.colorbar(im_err, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[1, 2]
    ax.set_axis_off()
    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0
    lines = [
        f"algo: {estimate.algo_name}",
        f"RMSE: {metrics.get('rmse_mm', float('nan')):.1f} mm",
        f"hit_rate: {metrics.get('hit_rate', float('nan')) * 100:.1f}%",
        f"valid_pred_ratio: {metrics.get('valid_pred_ratio', float('nan')):.3f}",
        f"valid_gt_ratio: {metrics.get('valid_gt_ratio', float('nan')):.3f}",
        f"SBR: {sample.sbr}",
        f"bin_size_ps: {sample.bin_size_ps:.3f}",
        f"BIN_MM: {bin_mm:.3f}",
        f"sample_id: {sample.sample_id}",
    ]
    ax.text(
        0.02,
        0.98,
        "\n".join(lines),
        ha="left",
        va="top",
        family="monospace",
        transform=ax.transAxes,
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "0.75"},
    )

    fig.tight_layout()
    return fig
