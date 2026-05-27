# Export trained TOF depth models to ONNX.
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.models.hist3d_net import DepthUNet, Hist3DNet


def build_model(name: str) -> torch.nn.Module:
    if name == "hist3d":
        return Hist3DNet()
    if name == "unet":
        return DepthUNet()
    raise ValueError(f"unsupported model: {name}")


def load_checkpoint(model: torch.nn.Module, checkpoint_path: Path) -> None:
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model.load_state_dict(state_dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a PF32 depth model to ONNX")
    parser.add_argument("--model", choices=["hist3d", "unet"], required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = build_model(args.model)
    load_checkpoint(model, args.checkpoint)
    model.eval()

    dummy = (
        torch.zeros(1, 1, 32, 32, 1024, dtype=torch.float32)
        if args.model == "hist3d"
        else torch.zeros(1, 1, 32, 32, dtype=torch.float32)
    )
    input_name = "histogram" if args.model == "hist3d" else "depth"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with torch.no_grad():
        torch_output = model(dummy).cpu().numpy()

    torch.onnx.export(
        model,
        dummy,
        args.output,
        input_names=[input_name],
        output_names=["depth"],
        opset_version=17,
        dynamic_axes={input_name: {0: "batch"}, "depth": {0: "batch"}},
    )

    session = ort.InferenceSession(str(args.output), providers=["CPUExecutionProvider"])
    ort_output = session.run(None, {input_name: dummy.cpu().numpy()})[0]
    max_error = float(np.max(np.abs(torch_output - ort_output)))
    if max_error >= 1e-4:
        raise RuntimeError(f"ONNX verification failed: max error {max_error:.6g}")

    print(f"input {input_name}: {tuple(dummy.shape)}")
    print(f"output depth: {tuple(ort_output.shape)}")
    print(f"onnx max_abs_error={max_error:.6g}")


if __name__ == "__main__":
    main()
