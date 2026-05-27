"""Argmax / spatial-argmax / dataset-ZNCC sanity comparison."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms import argmax
from algorithms import bg_sub_argmax
from algorithms import tail_bg_argmax
from algorithms import lmf
from algorithms.argmax import ArgmaxConfig
from contracts import DepthEstimate
from eval.metrics import compute_all
from eval.viz import plot_sanity_panel
from sim_spad_loader import load_spad_mat, bin_to_mm


def _dataset_estimate(sample, field_name: str, algo_name: str) -> DepthEstimate | None:
    """Wrap a dataset-provided bin estimate as a DepthEstimate."""
    bins = getattr(sample, field_name, None)
    if bins is None:
        return None
    depth_mm = np.asarray(
        bin_to_mm(bins.astype(np.float32), sample.start_stop, sample.bin_size_ps),
        dtype=np.float32,
    )
    valid = bins > 0
    confidence = np.where(valid, 1.0, 0.0).astype(np.float32)
    depth_mm[~valid] = 0.0
    return DepthEstimate(depth_mm=depth_mm, confidence=confidence, algo_name=algo_name)


def _find_first_mat() -> Path:
    dataset_root = ROOT / "datasets"
    files = sorted(dataset_root.rglob("*.mat"))
    if not files:
        raise FileNotFoundError(f"no .mat files found under {dataset_root}")
    return files[0]


def _print_table(rows: list[tuple[str, dict]]) -> None:
    col_w = 16
    header = f"{'metric':<22}" + "".join(f"{name:>{col_w}}" for name, _ in rows)
    print(header)
    print("-" * len(header))
    for key, label, fmt in [
        ("rmse_mm",          "RMSE (mm)",         "{:>14.1f}  "),
        ("hit_rate",         "hit_rate",           "{:>14.1f}% "),
        ("valid_pred_ratio", "valid_pred_ratio",   "{:>14.3f}  "),
    ]:
        vals = []
        for _, m in rows:
            v = m.get(key, float("nan"))
            if key == "hit_rate":
                vals.append(f"{v * 100:>{col_w - 1}.1f}%")
            elif key == "rmse_mm":
                vals.append(f"{v:>{col_w}.1f}")
            else:
                vals.append(f"{v:>{col_w}.3f}")
        print(f"{label:<22}" + "".join(vals))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mat_file", nargs="?")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    mat_path = Path(args.mat_file) if args.mat_file else _find_first_mat()
    sample = load_spad_mat(mat_path, start_stop="forward")
    sample_rates = load_spad_mat(mat_path, use_field="rates", start_stop="forward")

    print(f"\n[run_sanity] {sample.sample_id}  "
          f"SBR={sample.sbr}  signal_photons={sample.mean_signal_photons}\n")

    algos: list[tuple[str, DepthEstimate]] = []

    algos.append(("argmax_spad",   argmax.estimate(sample)))
    # rates is normalised [0,1] so min_counts=1.0 would reject every pixel
    algos.append(("argmax_rates",  argmax.estimate(sample_rates, ArgmaxConfig(min_counts=0.0))))
    algos.append(("lmf_spad",      lmf.estimate(sample)))
    algos.append(("lmf_rates",     lmf.estimate(sample_rates)))     # LMF on clean histogram
    algos.append(("spatial_3x3",   bg_sub_argmax.estimate(sample)))

    for field, name in [
        ("est_argmax_bins", "ds_argmax"),
        ("est_lmf_bins",    "ds_lmf"),
        ("est_zncc_bins",   "ds_zncc"),
    ]:
        est = _dataset_estimate(sample, field, name)
        if est is not None:
            algos.append((name, est))

    metrics = [(name, compute_all(est, sample)) for name, est in algos]
    _print_table(metrics)
    print()

    figs = [
        (name, plot_sanity_panel(sample, est, m, title=name))
        for (name, est), (_, m) in zip(algos, metrics)
    ]

    if args.save:
        out_dir = ROOT / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, fig in figs:
            p = out_dir / f"{sample.sample_id}_{name}.png"
            fig.savefig(p, dpi=150)
            print(f"[run_sanity] saved: {p}")
    else:
        import matplotlib.pyplot as plt
        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
