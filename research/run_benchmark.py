"""Stratified benchmark: compare algorithms across SBR levels.

Scans the dataset, selects ~16 representative samples covering four SBR
strata (very-low / low / medium / high), runs all algorithms, and prints a
summary table.  One sample per (scene, SBR-stratum) pair ensures scene
diversity.

Usage:
    python run_benchmark.py [--dataset datasets/] [--save]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms import argmax, bg_sub_argmax, lmf
from algorithms.argmax import ArgmaxConfig
from contracts import DepthEstimate
from eval.metrics import compute_all
from sim_spad_loader import load_spad_mat, bin_to_mm

# ── SBR strata: (label, lo_inclusive, hi_exclusive, n_samples) ──────────────
STRATA = [
    ("very_low", 0.00, 0.10, 3),
    ("low",      0.10, 0.50, 5),
    ("medium",   0.50, 2.00, 5),
    ("high",     2.00, 999., 3),
]

ALGO_NAMES = ["argmax_spad", "argmax_rates", "lmf_spad", "lmf_rates",
              "spatial_3x3", "ds_argmax", "ds_lmf", "ds_zncc"]


def _quick_sbr(mat_path: Path) -> float | None:
    """Read only the SBR scalar from a .mat without loading the histogram."""
    try:
        from scipy.io import loadmat
        raw = loadmat(str(mat_path), variable_names=["SBR"], squeeze_me=True)
        v = raw.get("SBR")
        return float(v) if v is not None else None
    except Exception:
        return None


def _collect_files(dataset_root: Path) -> list[tuple[Path, str, float]]:
    """Return list of (path, scene_name, sbr) for all .mat files."""
    rows = []
    for mat in sorted(dataset_root.rglob("*.mat")):
        scene = mat.parent.name
        sbr = _quick_sbr(mat)
        if sbr is not None:
            rows.append((mat, scene, sbr))
    return rows


def _select_samples(rows: list[tuple[Path, str, float]]) -> list[Path]:
    """Pick one file per (scene, stratum), up to n_samples per stratum."""
    selected: list[Path] = []
    for label, lo, hi, n in STRATA:
        in_stratum = [(p, sc) for p, sc, sbr in rows if lo <= sbr < hi]
        # one per scene, then cap at n
        seen_scenes: set[str] = set()
        picks: list[Path] = []
        for path, scene in in_stratum:
            if scene not in seen_scenes:
                seen_scenes.add(scene)
                picks.append(path)
            if len(picks) >= n:
                break
        selected.extend(picks)
        print(f"  stratum {label:10s} ({lo:.2f}–{hi:.2f}): {len(picks)} samples")
    return selected


def _dataset_estimate(sample, field_name: str, algo_name: str) -> DepthEstimate | None:
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


def _run_one(mat_path: Path) -> dict:
    sample = load_spad_mat(mat_path, start_stop="forward")
    sample_rates = load_spad_mat(mat_path, use_field="rates", start_stop="forward")

    estimates = {
        "argmax_spad":  argmax.estimate(sample),
        "argmax_rates": argmax.estimate(sample_rates, ArgmaxConfig(min_counts=0.0)),
        "lmf_spad":     lmf.estimate(sample),
        "lmf_rates":    lmf.estimate(sample_rates),
        "spatial_3x3":  bg_sub_argmax.estimate(sample),
    }
    for field, name in [("est_argmax_bins", "ds_argmax"),
                        ("est_lmf_bins",    "ds_lmf"),
                        ("est_zncc_bins",   "ds_zncc")]:
        est = _dataset_estimate(sample, field, name)
        if est is not None:
            estimates[name] = est

    row = {
        "sample_id": sample.sample_id,
        "scene":     mat_path.parent.name,
        "sbr":       sample.sbr or float("nan"),
    }
    for algo_name, est in estimates.items():
        m = compute_all(est, sample)
        row[f"{algo_name}_hit"] = m["hit_rate"]
        row[f"{algo_name}_rmse"] = m["rmse_mm"]
    return row


def _print_summary(results: list[dict]) -> None:
    algos = [a for a in ALGO_NAMES if f"{a}_hit" in results[0]]

    # Header
    col = 12
    print(f"\n{'sample':<26} {'sbr':>6}", end="")
    for a in algos:
        print(f"  {a[:col]:>{col}}", end="")
    print()
    print("-" * (26 + 8 + len(algos) * (col + 2)))

    # Per-sample rows (hit_rate %)
    for r in results:
        print(f"{r['sample_id']:<26} {r['sbr']:>6.3f}", end="")
        for a in algos:
            v = r.get(f"{a}_hit", float("nan"))
            print(f"  {v * 100:>{col}.1f}%", end="")
        print()

    # Mean per stratum
    print()
    print(f"{'MEAN':>33}", end="")
    for a in algos:
        vals = [r[f"{a}_hit"] for r in results if f"{a}_hit" in r]
        print(f"  {np.mean(vals) * 100:>{col}.1f}%", end="")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="datasets")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    dataset_root = ROOT / args.dataset
    if not dataset_root.exists():
        print(f"[benchmark] dataset not found: {dataset_root}")
        return 1

    print(f"[benchmark] scanning {dataset_root} …")
    rows = _collect_files(dataset_root)
    print(f"[benchmark] found {len(rows)} files across "
          f"{len({sc for _, sc, _ in rows})} scenes\n")

    print("[benchmark] selecting samples …")
    selected = _select_samples(rows)
    print(f"\n[benchmark] running {len(selected)} samples × {len(ALGO_NAMES)} algorithms …\n")

    results = []
    for i, path in enumerate(selected, 1):
        print(f"  [{i:2d}/{len(selected)}] {path.parent.name}/{path.name} … ", end="", flush=True)
        r = _run_one(path)
        results.append(r)
        hit = r.get("argmax_spad_hit", float("nan"))
        print(f"argmax_spad hit={hit * 100:.1f}%")

    _print_summary(results)

    if args.save:
        import csv
        out = ROOT / "out" / "benchmark_results.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        if results:
            keys = list(results[0].keys())
            with open(out, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                w.writerows(results)
            print(f"\n[benchmark] saved: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
