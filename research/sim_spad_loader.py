"""Loader for Gutierrez-Barragan ICCV 2023 SimSPADDataset .mat samples."""
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
        ):
            arr = getattr(self, name)
            if arr is not None:
                assert arr.shape == (h, w), f"{name} shape {arr.shape} mismatch hist {(h, w)}"


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
        return dense.reshape(side, side, BINS).astype(np.float32, copy=False), side, side

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
