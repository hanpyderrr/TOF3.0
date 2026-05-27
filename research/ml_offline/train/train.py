# Training entrypoint for PF32 TOF depth models.
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.data.tof_dataset import TofHistogramDataset, TIME_BIN_PS, LIGHT_MM_PER_PS
from ml.models.hist3d_net import DepthUNet, Hist3DNet

try:
    from pytorch_msssim import ssim
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    ssim = None


def build_model(name: str) -> nn.Module:
    if name == "hist3d":
        return Hist3DNet()
    if name == "unet":
        return DepthUNet()
    raise ValueError(f"unsupported model: {name}")


def histogram_peak_depth(histogram: torch.Tensor) -> torch.Tensor:
    peak_bins = histogram.argmax(dim=-1).to(torch.float32)
    return peak_bins * TIME_BIN_PS * LIGHT_MM_PER_PS / 2.0


def depth_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    l1 = F.l1_loss(pred, target)
    if ssim is None:
        return l1
    max_depth = torch.clamp(target.amax(dim=(1, 2, 3), keepdim=True), min=1.0)
    pred_norm = pred / max_depth
    target_norm = target / max_depth
    return l1 + (1.0 - ssim(pred_norm, target_norm, data_range=1.0, size_average=True))


def split_dataset(dataset: TofHistogramDataset, val_fraction: float = 0.2, seed: int = 42) -> tuple[Subset, Subset]:
    indices = list(range(len(dataset)))
    random.Random(seed).shuffle(indices)
    val_size = max(1, int(len(indices) * val_fraction)) if len(indices) > 1 else 0
    val_indices = indices[:val_size]
    train_indices = indices[val_size:] or indices
    if not val_indices:
        val_indices = train_indices
    return Subset(dataset, train_indices), Subset(dataset, val_indices)


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    device: torch.device,
    model_name: str,
) -> tuple[float, tuple[float, float]]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    pred_min = float("inf")
    pred_max = float("-inf")

    for batch in tqdm(loader, leave=False):
        histogram = batch["histogram"].to(device)
        target = batch["depth"]
        if target is None:
            raise ValueError("training requires paired foggy_dir/clear_dir samples with depth targets")
        target = target.to(device)

        inputs = histogram if model_name == "hist3d" else histogram_peak_depth(histogram)
        with torch.set_grad_enabled(training):
            pred = model(inputs)
            loss = depth_loss(pred, target)
            if training:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()

        total_loss += float(loss.detach()) * histogram.size(0)
        pred_min = min(pred_min, float(pred.detach().min()))
        pred_max = max(pred_max, float(pred.detach().max()))

    return total_loss / len(loader.dataset), (pred_min, pred_max)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PF32 TOF depth models")
    parser.add_argument("--model", choices=["hist3d", "unet"], default="hist3d")
    parser.add_argument("--data-dir", type=Path, default=None, help="Unpaired .tch directory, for compatibility")
    parser.add_argument("--foggy-dir", type=Path, default=None, help="Paired foggy .tch directory")
    parser.add_argument("--clear-dir", type=Path, required=True, help="Paired clear .tch directory")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("ml/runs"))
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    foggy_dir = args.foggy_dir or args.data_dir
    if foggy_dir is None:
        raise SystemExit("--foggy-dir or --data-dir is required for training")

    device = torch.device(args.device)
    dataset = TofHistogramDataset(foggy_dir=foggy_dir, clear_dir=args.clear_dir)
    train_set, val_set = split_dataset(dataset)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = build_model(args.model).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    best_loss = float("inf")

    for epoch in range(1, args.epochs + 1):
        train_loss, train_range = run_epoch(model, train_loader, optimizer, device, args.model)
        val_loss, val_range = run_epoch(model, val_loader, None, device, args.model)
        scheduler.step()

        checkpoint = {
            "model": args.model,
            "epoch": epoch,
            "state_dict": model.state_dict(),
            "val_loss": val_loss,
            "args": vars(args),
        }
        torch.save(checkpoint, args.output_dir / f"epoch_{epoch:03d}.pth")
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save(checkpoint, args.output_dir / "best_model.pth")

        print(
            f"epoch={epoch} train_loss={train_loss:.6f} val_loss={val_loss:.6f} "
            f"train_depth_range=({train_range[0]:.2f},{train_range[1]:.2f}) "
            f"val_depth_range=({val_range[0]:.2f},{val_range[1]:.2f})"
        )


if __name__ == "__main__":
    main()
