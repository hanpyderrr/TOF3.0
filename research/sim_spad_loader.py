"""
sim_spad_loader.py — Gutierrez SimSPADDataset .mat 加载器

功能
----
读取 Felipe Gutierrez-Barragan (ICCV 2023) 的 SimSPADDataset .mat 样本，
把内部字段统一组装成 ``SpadSample`` 对象（``contracts`` 那套契约的输入端）。
提供 ``bin_to_mm`` 转换工具，以及反归一化 rates 的方法。

上游
----
- 物理数据：research/datasets/scene_group0/<scene>/spad_XXXX_p1.mat
- MATLAB 数据集制作脚本（felipegb94 仓库 data_gener/）

下游
----
- ``research/algorithms/*.py``：通过 ``SpadSample.hist`` 拿到 (H, W, BINS) 直方图
- ``research/eval/viz.py``：从 ``SpadSample`` 取 intensity / depth_mm / hist 出图
- ``research/run_*.py``：所有入口都靠这个 loader

依赖
----
- scipy.io.loadmat 读 .mat
- scipy.sparse 处理稀疏 spad（4096×1024 → 64×64×1024）
- numpy

备注
----
- **MATLAB column-major 陷阱**：``spad`` 字段是 ``sparse(reshape(detections, nr*nc, []))``，
  反解时**必须用** ``reshape(side, side, BINS, order="F")``，否则像素行列被转置，
  所有"在 spad 上"的算法结果都错乱（曾导致 argmax_spad 从 32% 假摔成 8.6%）。
- ``rates`` 字段是**归一化的** [0,1]，要拿期望直方图必须用
  ``SpadSample.denormalized_rates()``，按 ``rates_norm_params`` 反算。
- ``bin`` 字段是 MATLAB 1-indexed bin 索引；本 loader 转 mm 时按原数字算
  （结果差 1 个 bin / 12 mm，hit_rate 容差 200 mm 时可忽略，亚 bin 评估时要小心）。
- ``start_stop="reverse"`` 仅供 PF32 工程化降级用，算法研究默认 ``"forward"``。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

import numpy as np

BINS = 1024
BIN_PS = 55.0
C_MM_PS = 0.299792458
BIN_MM = BIN_PS * C_MM_PS / 2.0

StartStop = Literal["forward", "reverse"]


@dataclass
class SpadSample:
    """Single SPAD histogram sample used by algorithm prototypes."""

    hist: np.ndarray
    depth_mm: np.ndarray
    sbr: float | None
    mean_signal_photons: float | None
    mean_background_photons: float | None
    sample_id: str
    start_stop: StartStop
    bin_size_ps: float = BIN_PS
    intensity: np.ndarray | None = None
    est_argmax_bins: np.ndarray | None = None
    est_lmf_bins: np.ndarray | None = None
    est_zncc_bins: np.ndarray | None = None
    rates: np.ndarray | None = None
    rates_offset: np.ndarray | None = None
    rates_scaling: np.ndarray | None = None

    def __post_init__(self) -> None:
        h, w, b = self.hist.shape
        assert b == BINS, f"hist bins {b} != {BINS}"
        assert self.depth_mm.shape == (h, w), (
            f"depth shape {self.depth_mm.shape} mismatch hist {(h, w)}"
        )
        for name in (
            "intensity",
            "est_argmax_bins",
            "est_lmf_bins",
            "est_zncc_bins",
            "rates_offset",
            "rates_scaling",
        ):
            arr = getattr(self, name)
            if arr is not None:
                assert arr.shape == (h, w), f"{name} shape {arr.shape} mismatch hist {(h, w)}"
        if self.rates is not None:
            assert self.rates.shape == (h, w, b), (
                f"rates shape {self.rates.shape} mismatch hist {(h, w, b)}"
            )

    def denormalized_rates(self, formula: str = "scale_then_offset") -> np.ndarray | None:
        """Reconstruct dense expected histogram from normalized rates + per-pixel params.

        Two candidate formulas (the dataset readme does not pin one down; pick by
        comparing argmax(rates) vs GT bin):
          - "scale_then_offset": rates * scaling[..., None] + offset[..., None]
          - "offset_then_scale": (rates + offset[..., None]) * scaling[..., None]
        Returns None if any of rates / rates_offset / rates_scaling is missing.
        """

        if self.rates is None or self.rates_offset is None or self.rates_scaling is None:
            return None
        scaling = self.rates_scaling[..., None]
        offset = self.rates_offset[..., None]
        if formula == "scale_then_offset":
            return self.rates * scaling + offset
        if formula == "offset_then_scale":
            return (self.rates + offset) * scaling
        raise ValueError(f"unknown formula: {formula}")


def bin_to_mm(
    bin_idx: np.ndarray | float,
    start_stop: StartStop = "forward",
    bin_size_ps: float = BIN_PS,
) -> np.ndarray | float:
    """Convert bin index to millimeters."""

    arr = np.asarray(bin_idx, dtype=float)
    bin_mm = bin_size_ps * C_MM_PS / 2.0
    if start_stop == "forward":
        return arr * bin_mm
    return (BINS - 1 - arr) * bin_mm


def _scalar(raw: dict, name: str) -> float | None:
    if name not in raw:
        return None
    value = np.asarray(raw[name]).squeeze()
    return float(value) if value.size == 1 else None


def _depth_from_bin_field(
    bin_field: np.ndarray,
    start_stop: StartStop,
    bin_size_ps: float,
) -> np.ndarray:
    bin_idx = np.asarray(bin_field).squeeze()
    assert bin_idx.ndim == 2, f"unexpected bin shape after squeeze: {bin_idx.shape}"
    depth_mm = np.asarray(bin_to_mm(bin_idx, start_stop, bin_size_ps), dtype=np.float32)
    depth_mm[bin_idx <= 0] = 0.0
    return depth_mm


def _depth_from_bins_field(
    bins_field: np.ndarray,
    start_stop: StartStop,
    bin_size_ps: float,
) -> np.ndarray:
    arr = np.asarray(bins_field, dtype=np.float32).squeeze()
    assert arr.ndim == 2, f"unexpected bins shape after squeeze: {arr.shape}"
    bin_idx = np.clip(arr * BINS, 0, BINS - 1)
    depth_mm = np.asarray(bin_to_mm(bin_idx, start_stop, bin_size_ps), dtype=np.float32)
    depth_mm[arr <= 0] = 0.0
    return depth_mm


def _load_hist(raw_field: object) -> tuple[np.ndarray, int, int]:
    try:
        from scipy import sparse
    except ImportError:
        sparse = None

    if sparse is not None and sparse.issparse(raw_field):
        dense = raw_field.toarray()
        if dense.ndim != 2 or dense.shape[1] != BINS:
            raise ValueError(f"unexpected sparse spad shape: {dense.shape}")
        side = int(np.sqrt(dense.shape[0]))
        if side * side != dense.shape[0]:
            raise ValueError(f"sparse spad pixels are not square: {dense.shape[0]}")
        # MATLAB stored spad as `sparse(reshape(detections, nr*nc, []))` which is
        # column-major: pixel (r, c) → row r + c*nr. numpy default C-order reshape
        # would transpose the image; use order='F' to undo MATLAB's flatten.
        return dense.reshape(side, side, BINS, order="F").astype(np.float32, copy=False), side, side

    arr = np.asarray(raw_field)
    if arr.ndim == 4 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim != 3:
        raise AssertionError(f"unexpected spad shape: {arr.shape}")

    if arr.shape[0] == BINS:
        _, nr, nc = arr.shape
        hist = np.transpose(arr, (1, 2, 0)).astype(np.float32, copy=False)
    elif arr.shape[2] == BINS:
        nr, nc, _ = arr.shape
        hist = arr.astype(np.float32, copy=False)
    else:
        raise AssertionError(f"unexpected spad shape: {arr.shape}")

    return hist, nr, nc


def _array2(raw: dict, name: str, shape: tuple[int, int], dtype) -> np.ndarray | None:
    if name not in raw:
        return None
    arr = np.asarray(raw[name]).squeeze()
    if arr.shape != shape:
        raise ValueError(f"{name} shape {arr.shape} != hist spatial {shape}")
    return arr.astype(dtype, copy=False)


def _load_rates(
    raw: dict, nr: int, nc: int, start_stop: StartStop
) -> np.ndarray | None:
    if "rates" not in raw:
        return None
    arr = np.asarray(raw["rates"])
    if arr.ndim == 4 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim != 3:
        raise ValueError(f"unexpected rates shape: {arr.shape}")
    if arr.shape == (BINS, nr, nc):
        arr = np.transpose(arr, (1, 2, 0))
    elif arr.shape != (nr, nc, BINS):
        raise ValueError(f"unexpected rates shape: {arr.shape}")
    rates = arr.astype(np.float32, copy=False)
    if start_stop == "reverse":
        rates = rates[:, :, ::-1].copy()
    return rates


def _load_rates_norm_params(
    raw: dict, nr: int, nc: int
) -> tuple[np.ndarray | None, np.ndarray | None]:
    if "rates_norm_params" not in raw:
        return None, None
    params = raw["rates_norm_params"]
    try:
        offset = np.asarray(params["rates_offset"][0, 0]).squeeze()
        scaling = np.asarray(params["rates_scaling"][0, 0]).squeeze()
    except (KeyError, IndexError, ValueError):
        return None, None
    if offset.shape != (nr, nc) or scaling.shape != (nr, nc):
        return None, None
    return offset.astype(np.float32, copy=False), scaling.astype(np.float32, copy=False)


def load_spad_mat(
    mat_path: str | Path,
    *,
    use_field: str = "spad",
    start_stop: StartStop = "forward",
) -> SpadSample:
    """Load one SimSPADDataset .mat sample."""

    try:
        from scipy.io import loadmat
    except ImportError as exc:
        raise RuntimeError("scipy is required: pip install scipy") from exc

    mat_path = Path(mat_path)
    raw = loadmat(str(mat_path), squeeze_me=False)

    if use_field not in raw:
        raise KeyError(f"{mat_path.name}: field '{use_field}' not in {list(raw.keys())}")

    bin_size_ps = (_scalar(raw, "bin_size") or (BIN_PS * 1e-12)) * 1e12
    hist_hw_b, nr, nc = _load_hist(raw[use_field])
    if start_stop == "reverse":
        hist_hw_b = hist_hw_b[:, :, ::-1].copy()

    if "bin" in raw:
        depth_mm = _depth_from_bin_field(raw["bin"], start_stop, bin_size_ps)
    elif "bins" in raw:
        depth_mm = _depth_from_bins_field(raw["bins"], start_stop, bin_size_ps)
    else:
        depth_mm = np.zeros((nr, nc), dtype=np.float32)

    if depth_mm.shape != (nr, nc):
        raise ValueError(f"GT depth shape {depth_mm.shape} != hist spatial {(nr, nc)}")

    rates = _load_rates(raw, nr, nc, start_stop)
    rates_offset, rates_scaling = _load_rates_norm_params(raw, nr, nc)

    return SpadSample(
        hist=hist_hw_b,
        depth_mm=depth_mm,
        sbr=_scalar(raw, "SBR"),
        mean_signal_photons=_scalar(raw, "mean_signal_photons"),
        mean_background_photons=_scalar(raw, "mean_background_photons"),
        sample_id=mat_path.stem,
        start_stop=start_stop,
        bin_size_ps=bin_size_ps,
        intensity=_array2(raw, "intensity", (nr, nc), np.float32),
        est_argmax_bins=_array2(raw, "est_range_bins_argmax", (nr, nc), np.uint16),
        est_lmf_bins=_array2(raw, "est_range_bins_lmf", (nr, nc), np.uint16),
        est_zncc_bins=_array2(raw, "est_range_bins_zncc", (nr, nc), np.uint16),
        rates=rates,
        rates_offset=rates_offset,
        rates_scaling=rates_scaling,
    )


def iter_dataset(
    root: str | Path,
    *,
    pattern: str = "*.mat",
    limit: int | None = None,
    **load_kwargs,
) -> Iterator[SpadSample]:
    """Yield loaded samples under a directory."""

    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"{root} not found")
    files = sorted(root.rglob(pattern))
    if limit is not None:
        files = files[:limit]
    for file_path in files:
        yield load_spad_mat(file_path, **load_kwargs)


def sanity_check(sample: SpadSample) -> dict:
    """Run a quick argmax sanity check against GT depth."""

    hist = sample.hist
    gt = sample.depth_mm
    argmax_bin = hist.argmax(axis=2)
    pred_mm = np.asarray(
        bin_to_mm(argmax_bin, sample.start_stop, sample.bin_size_ps),
        dtype=np.float32,
    )
    valid = gt > 0
    err = np.abs(pred_mm - gt)[valid]
    hit = float((err < 200).mean()) if err.size else float("nan")
    rmse = float(np.sqrt(np.mean(err**2))) if err.size else float("nan")
    return {
        "sample_id": sample.sample_id,
        "shape": tuple(hist.shape),
        "start_stop": sample.start_stop,
        "bin_size_ps": sample.bin_size_ps,
        "valid_px": int(valid.sum()),
        "argmax_hit_rate": hit,
        "argmax_rmse_mm": rmse,
        "sbr": sample.sbr,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python sim_spad_loader.py <path/to/sample.mat or dir>")
        sys.exit(0)
    target = Path(sys.argv[1])
    samples = [load_spad_mat(target)] if target.is_file() else list(iter_dataset(target, limit=5))
    for sample in samples:
        print(sanity_check(sample))
