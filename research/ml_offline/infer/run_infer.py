# CPU ONNX inference for PF32 .tch histogram files.
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.data.tof_dataset import LIGHT_MM_PER_PS, TIME_BIN_PS, normalize_histogram, read_tch


def histogram_peak_depth(histogram: np.ndarray) -> np.ndarray:
    peak_bins = histogram.argmax(axis=-1).astype(np.float32)
    return peak_bins * TIME_BIN_PS * LIGHT_MM_PER_PS / 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ONNX depth inference on one PF32 .tch file")
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--input-tch", type=Path, required=True)
    parser.add_argument("--output-npy", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session = ort.InferenceSession(str(args.model_path), providers=["CPUExecutionProvider"])
    input_meta = session.get_inputs()[0]

    histogram = normalize_histogram(read_tch(args.input_tch)["histogram"])
    if len(input_meta.shape) == 5:
        model_input = histogram[None, None, :, :, :].astype(np.float32)
    elif len(input_meta.shape) == 4:
        model_input = histogram_peak_depth(histogram)[None, None, :, :].astype(np.float32)
    else:
        raise ValueError(f"unsupported ONNX input rank: {len(input_meta.shape)}")

    started = time.perf_counter()
    depth = session.run(None, {input_meta.name: model_input})[0]
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    depth_map = np.asarray(depth[0, 0], dtype=np.float32)
    args.output_npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output_npy, depth_map)

    print(f"input_shape={model_input.shape} output_shape={depth_map.shape} elapsed_ms={elapsed_ms:.3f}")


if __name__ == "__main__":
    main()
