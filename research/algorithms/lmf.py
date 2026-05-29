"""
algorithms/lmf.py — 匹配滤波（Matched Filter）深度估计

功能
----
把每像素直方图与 IRF 模板做循环互相关（FFT 实现），取相关结果的 argmax 作为深度。
理论上对均匀白噪背景最优。IRF 支持两种来源：
  1. **Gaussian 近似**（``irf_sigma_bins``）——零配置 fallback
  2. **真 IRF**（``irf_path`` 指向 ``PSF_64x64.mat``）——加载 16-bin per-column IRF，
     可选 ``per_column=True`` 用每列像素自己的 IRF；否则用全局均值 IRF（单核）。

上游
----
- 输入：``sim_spad_loader.SpadSample``
- 配置：``LMFConfig(irf_sigma_bins=2.5, irf_path=None, per_column=False, min_corr=0.0)``
  - 默认 σ=2.5 bin（80 ps/bin 下约 200 ps，约等于系统真实 IRF 宽度）
  - 给 ``irf_path`` 启用真 IRF；与 ``irf_sigma_bins`` 互斥（真 IRF 优先）

下游
----
- 返回 ``contracts.DepthEstimate``：
  - algo_name=``"lmf_s{σ}"`` 高斯模式
  - algo_name=``"lmf_real"`` 真 IRF 单核模式
  - algo_name=``"lmf_real_pc"`` 真 IRF per-column 模式
- 被 ``run_sanity / run_benchmark / run_accumulation / run_verify_baseline`` 调

依赖
----
- numpy（FFT 用 ``np.fft.rfft/irfft`` 走 SIMD）
- scipy.io.loadmat（仅在加载真 IRF 时）
- ``sim_spad_loader.BINS``

备注
----
- **真 IRF 形状（``PSF_64x64.mat``）**：``psf`` (16, 64)，64 列各是一条 16-bin IRF；
  ``PSF_img[i,j,:] == psf[:,j]``——同列像素共享 IRF（沿 W 轴变化、沿 H 轴不变）。
  全局均值 IRF 等效高斯 σ ≈ 2.15 bins，与 σ=2.5 默认值非常接近。
- 循环互相关 = ``ifft(fft(hist) × conj(fft(irf)))``；IRF 已 padding 到 BINS 且循环包裹。
- 在 rates 上跑（lmf_rates）实测 RMSE 8.6 mm < 1 bin，可证 LMF 具备**亚 bin 精度**——
  本实现 argmax 只取整 bin，未来做亚 bin 精修可用抛物线拟合。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from contracts import AlgoConfig, DepthEstimate
from sim_spad_loader import BINS


@dataclass
class LMFConfig(AlgoConfig):
    irf_sigma_bins: float = 2.5      # Gaussian IRF width (bins), used when irf_path is None
    irf_path: str | None = None       # path to PSF_64x64.mat for real IRF; overrides Gaussian
    per_column: bool = False          # use per-column real IRF (PF32-style varying IRF)
    min_corr: float = 0.0             # minimum correlation peak to declare valid


def _gaussian_irf(n_bins: int, sigma: float) -> np.ndarray:
    """Unit-energy Gaussian IRF for circular cross-correlation (zero-centred)."""
    t = np.arange(n_bins, dtype=np.float64)
    # Primary lobe at t=0, wrap-around lobe for circular FFT
    g = np.exp(-0.5 * (t / sigma) ** 2) + np.exp(-0.5 * ((t - n_bins) / sigma) ** 2)
    return (g / g.sum()).astype(np.float64)


@lru_cache(maxsize=4)
def _load_real_irf(irf_path: str) -> np.ndarray:
    """Load PSF_64x64.mat and return ``psf`` (P, W) — P bins (e.g. 16), W columns (e.g. 64).

    Cached so repeated loads in run_sanity / run_verify_baseline are free.
    """
    from scipy.io import loadmat

    mat = loadmat(str(Path(irf_path)))
    psf = np.asarray(mat["psf"], dtype=np.float64)   # (16, 64) for Gutierrez dataset
    # Normalise each column to unit energy (matches Gutierrez convention; already ≈1.0)
    psf = psf / psf.sum(axis=0, keepdims=True)
    return psf


def _pad_irf_to_bins(short_irf: np.ndarray, n_bins: int) -> np.ndarray:
    """Place a short IRF (e.g. 16 bins) at the start of a length-n_bins array, peak at bin 0.

    The match-filter via circular cross-correlation expects the IRF centred at t=0, so
    we roll the short IRF so its argmax sits at index 0 (with the rest wrapped to the tail).
    Energy is preserved.
    """
    P = short_irf.shape[0]
    full = np.zeros(n_bins, dtype=np.float64)
    full[:P] = short_irf
    shift = int(np.argmax(short_irf))
    full = np.roll(full, -shift)
    return full


def estimate(sample, cfg: LMFConfig | None = None) -> DepthEstimate:
    """Matched-filter depth estimate via FFT cross-correlation."""
    if cfg is None:
        cfg = LMFConfig()

    hist = sample.hist.astype(np.float64)  # (H, W, BINS)
    H, W, B = hist.shape

    if cfg.irf_path is not None:
        psf = _load_real_irf(cfg.irf_path)            # (P, W_psf)
        if cfg.per_column:
            if psf.shape[1] != W:
                raise ValueError(
                    f"per_column IRF requires PSF cols ({psf.shape[1]}) == sample W ({W})"
                )
            # Build per-column padded IRF: (W, B)
            irfs = np.stack(
                [_pad_irf_to_bins(psf[:, j], B) for j in range(W)],
                axis=0,
            )                                          # (W, B)
            IRF_conj = np.conj(np.fft.rfft(irfs, axis=1))[None, :, :]  # (1, W, B//2+1)
            algo_tag = "lmf_real_pc"
        else:
            # Use global-mean IRF as a single kernel (cheap, often within ~1pp of per-column)
            mean_short = psf.mean(axis=1)
            irf = _pad_irf_to_bins(mean_short, B)
            IRF_conj = np.conj(np.fft.rfft(irf))
            algo_tag = "lmf_real"
    else:
        irf = _gaussian_irf(B, cfg.irf_sigma_bins)
        IRF_conj = np.conj(np.fft.rfft(irf))
        algo_tag = f"lmf_s{cfg.irf_sigma_bins:.1f}"

    HIST = np.fft.rfft(hist, axis=2)                  # (H, W, B//2+1)
    corr = np.fft.irfft(HIST * IRF_conj, n=B, axis=2) # (H, W, B)
    corr = corr.astype(np.float32)

    peak_bin = corr.argmax(axis=2)                    # (H, W)
    peak_val = corr.max(axis=2).astype(np.float32)

    bin_mm = sample.bin_size_ps * 0.299792458 / 2.0

    if sample.start_stop == "forward":
        depth_mm = peak_bin.astype(np.float32) * bin_mm
    elif sample.start_stop == "reverse":
        depth_mm = (BINS - 1 - peak_bin).astype(np.float32) * bin_mm
    else:
        raise ValueError(f"unknown start_stop: {sample.start_stop!r}")

    valid = peak_val > cfg.min_corr
    depth_mm[~valid] = 0.0

    max_val = float(peak_val.max()) if peak_val.size else 0.0
    confidence = (
        (peak_val / max_val).astype(np.float32) if max_val > 0
        else np.zeros_like(peak_val)
    )
    confidence[~valid] = 0.0

    return DepthEstimate(
        depth_mm=depth_mm,
        confidence=confidence,
        algo_name=algo_tag,
        extras={
            "peak_bin": peak_bin,
            "irf_mode": "real_pc" if (cfg.irf_path and cfg.per_column)
                        else "real" if cfg.irf_path
                        else f"gauss_s{cfg.irf_sigma_bins}",
        },
    )
