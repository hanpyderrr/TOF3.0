# Dataset utilities for PF32 TCSPC histogram files.
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    from torch.utils.data import Dataset
except ImportError:  # Allows ONNX inference utilities to reuse .tch readers without PyTorch.
    torch = None
    Dataset = object


TCH_MAGIC = b"TCHIST1\0"
TCH_HEADER = struct.Struct("<8sIHHHHQ")
TIME_BIN_PS = 55.0
LIGHT_MM_PER_PS = 0.299792458


def read_tch(path: str | Path) -> dict[str, Any]:
    """Read one .tch histogram file into metadata plus uint16 histogram."""
    path = Path(path)
    with path.open("rb") as fh:
        header = fh.read(TCH_HEADER.size)
        if len(header) != TCH_HEADER.size:
            raise ValueError(f"{path} is too small for a .tch header")

        magic, seq, width, height, bins, sample_bytes, payload_bytes = TCH_HEADER.unpack(header)
        if magic != TCH_MAGIC:
            raise ValueError(f"{path} has invalid magic {magic!r}")
        if sample_bytes != 2:
            raise ValueError(f"{path} sampleBytes={sample_bytes}, expected 2")

        expected_bytes = width * height * bins * sample_bytes
        if payload_bytes != expected_bytes:
            raise ValueError(f"{path} payloadBytes={payload_bytes}, expected {expected_bytes}")

        payload = fh.read(payload_bytes)
        if len(payload) != payload_bytes:
            raise ValueError(f"{path} payload is truncated")

    histogram = np.frombuffer(payload, dtype="<u2").reshape(height, width, bins).copy()
    return {
        "seq": seq,
        "width": width,
        "height": height,
        "bins": bins,
        "histogram": histogram,
        "path": path,
    }


def normalize_histogram(histogram: np.ndarray) -> np.ndarray:
    hist = histogram.astype(np.float32, copy=False)
    max_value = float(hist.max())
    if max_value <= 0.0:
        return hist.copy()
    return hist / max_value


def histogram_to_depth_mm(histogram: np.ndarray) -> np.ndarray:
    peak_bins = np.asarray(histogram).argmax(axis=-1).astype(np.float32)
    return peak_bins * TIME_BIN_PS * LIGHT_MM_PER_PS / 2.0


class TofHistogramDataset(Dataset):
    """PyTorch dataset for single or paired foggy/clear PF32 TCSPC samples."""

    def __init__(
        self,
        data_dir: str | Path | None = None,
        *,
        foggy_dir: str | Path | None = None,
        clear_dir: str | Path | None = None,
    ) -> None:
        if foggy_dir is not None or clear_dir is not None:
            if foggy_dir is None or clear_dir is None:
                raise ValueError("foggy_dir and clear_dir must be provided together")
            self.pairs = self._scan_pairs(Path(foggy_dir), Path(clear_dir))
            self.samples: list[Path] = []
        else:
            if data_dir is None:
                raise ValueError("data_dir is required for unpaired inference mode")
            self.samples = sorted(Path(data_dir).glob("*.tch"))
            self.pairs = []

        if not self.samples and not self.pairs:
            raise ValueError("no .tch files found")

    @staticmethod
    def _scan_pairs(foggy_dir: Path, clear_dir: Path) -> list[tuple[Path, Path]]:
        foggy_files = {p.name: p for p in sorted(foggy_dir.glob("*.tch"))}
        clear_files = {p.name: p for p in sorted(clear_dir.glob("*.tch"))}
        names = sorted(foggy_files.keys() & clear_files.keys())
        if not names:
            raise ValueError("no paired .tch files found by matching file name")
        return [(foggy_files[name], clear_files[name]) for name in names]

    def __len__(self) -> int:
        return len(self.pairs) if self.pairs else len(self.samples)

    def __getitem__(self, index: int):
        if torch is None:
            raise ImportError("TofHistogramDataset requires torch; install ml/requirements.txt")

        if self.pairs:
            foggy_path, clear_path = self.pairs[index]
            foggy_hist = read_tch(foggy_path)["histogram"]
            clear_hist = read_tch(clear_path)["histogram"]
            depth = histogram_to_depth_mm(clear_hist).astype(np.float32)
            depth_tensor: torch.Tensor | None = torch.from_numpy(depth).unsqueeze(0)
        else:
            foggy_hist = read_tch(self.samples[index])["histogram"]
            depth_tensor = None

        hist = normalize_histogram(foggy_hist)
        return {
            "histogram": torch.from_numpy(hist).unsqueeze(0),
            "depth": depth_tensor,
        }
