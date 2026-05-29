"""
run_verify_baseline.py — Phase A 上界 + 数据集 baseline 实测

功能
----
针对算法 roadmap §三那段误传的 "rates 上 argmax = 32.3%"，用真数字钉死。
对 5 个不同场景样本跑 5 个估计器 × 4 个容差档 hit_rate + RMSE：
  1. argmax 在带噪 spad 上（我们的 baseline）
  2. argmax 在反归一化 rates 上（无噪上界，实测 ≈ 100% / 12 mm）
  3. ``est_range_bins_argmax``（数据集自带 baseline）
  4. ``est_range_bins_lmf``
  5. ``est_range_bins_zncc``

上游
----
- ``research/datasets/scene_group0/<scene>/spad_0011_p1.mat``（5 个场景的同名样本）
- ``sim_spad_loader.load_spad_mat`` + ``SpadSample.denormalized_rates()``

下游
----
- 控制台打印 per-sample 和 mean 两张表
- 写 ``research/out/verify_baseline.md``

依赖
----
- numpy
- 不依赖 algorithms/ 模块（直接调 hist.argmax，不走 contracts 那套）

备注
----
- 5 样本是钉锚点，不是完整 benchmark；要全集分层用 ``run_benchmark.py``
- 修完 loader F-order bug 后 5 样本均值：
  argmax_spad 0.579 ≈ ds_argmax 0.580（算法等价）
  argmax_rates 1.000（上界）
- tol_mm 档默认 [12, 24, 60, 200]；12 ≈ 1 bin，200 ≈ 17 bin
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

# allow running as `python research/run_verify_baseline.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.sim_spad_loader import BINS, load_spad_mat, bin_to_mm


SAMPLES = [
    "dining_room_0022/spad_0011_p1.mat",
    "dining_room_0003/spad_0011_p1.mat",
    "living_room_0008/spad_0011_p1.mat",
    "home_office_0006/spad_0011_p1.mat",
    "office_0002c/spad_0011_p1.mat",
]
TOLS_MM = [12, 24, 60, 200]
DATA_ROOT = Path(__file__).resolve().parent / "datasets"


def bin_to_mm_arr(bin_idx, bin_size_ps):
    return np.asarray(bin_idx, dtype=np.float64) * bin_size_ps * 0.299792458 / 2.0


def metrics_for(pred_bin, gt_bin, bin_size_ps, tols_mm):
    """Return dict of hit_rate@tol and rmse_mm. pred/gt are bin indices, (H,W)."""

    pred_mm = bin_to_mm_arr(pred_bin, bin_size_ps)
    gt_mm = bin_to_mm_arr(gt_bin, bin_size_ps)
    mask = gt_bin > 0
    if not np.any(mask):
        return {f"hit_{t}mm": float("nan") for t in tols_mm} | {"rmse_mm": float("nan")}
    err_mm = np.abs(pred_mm[mask] - gt_mm[mask])
    out = {f"hit_{t}mm": float((err_mm < t).mean()) for t in tols_mm}
    out["rmse_mm"] = float(np.sqrt(np.mean(err_mm**2)))
    return out


def gather_estimators(sample) -> dict:
    """Return {algo_name: pred_bin_array(H,W)} for the five estimators."""

    bins = BINS
    out: dict[str, np.ndarray] = {}

    # 1. argmax on noisy spad
    out["argmax_spad"] = sample.hist.argmax(axis=2)

    # 2. argmax on denormalized rates (upper bound)
    dr = sample.denormalized_rates("scale_then_offset")
    out["argmax_rates"] = dr.argmax(axis=2) if dr is not None else None

    # 3-5. dataset-provided estimates, clipped to [0, BINS-1]
    for key, attr in [
        ("est_argmax", "est_argmax_bins"),
        ("est_lmf", "est_lmf_bins"),
        ("est_zncc", "est_zncc_bins"),
    ]:
        arr = getattr(sample, attr)
        out[key] = None if arr is None else np.clip(arr.astype(np.int32), 0, bins - 1)

    return out


def format_table(rows, headers):
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    sep = " | "
    lines = [sep.join(str(h).ljust(w) for h, w in zip(headers, widths))]
    lines.append("-+-".join("-" * w for w in widths))
    for r in rows:
        lines.append(sep.join(str(c).ljust(w) for c, w in zip(r, widths)))
    return "\n".join(lines)


def main():
    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = []  # list of (sample_id, algo, metrics)
    for rel in SAMPLES:
        path = DATA_ROOT / rel
        if not path.exists():
            print(f"SKIP (missing): {rel}", file=sys.stderr)
            continue
        sample = load_spad_mat(path)
        bin_size_ps = sample.bin_size_ps
        bin_mm = bin_size_ps * 0.299792458 / 2.0
        # GT bin from depth_mm
        gt_bin = np.zeros_like(sample.depth_mm, dtype=np.int32)
        valid = sample.depth_mm > 0
        gt_bin[valid] = np.clip(np.round(sample.depth_mm[valid] / bin_mm).astype(np.int32), 1, BINS - 1)

        ests = gather_estimators(sample)
        for algo, pred in ests.items():
            if pred is None:
                continue
            m = metrics_for(pred, gt_bin, bin_size_ps, TOLS_MM)
            all_results.append({
                "sample": sample.sample_id,
                "scene": rel.split("/")[1],
                "algo": algo,
                **m,
            })

    if not all_results:
        print("No samples processed.", file=sys.stderr)
        sys.exit(1)

    # Per-sample table
    headers = ["sample", "algo"] + [f"hit_{t}mm" for t in TOLS_MM] + ["rmse_mm"]
    rows = []
    for r in all_results:
        rows.append([
            r["sample"][:18],
            r["algo"],
            *[f"{r[f'hit_{t}mm']:.3f}" for t in TOLS_MM],
            f"{r['rmse_mm']:.1f}",
        ])
    table = format_table(rows, headers)
    print(table)

    # Aggregate (mean across samples) per algo
    print("\n=== mean across samples ===")
    algos = sorted({r["algo"] for r in all_results}, key=lambda a: (
        {"argmax_spad": 0, "argmax_rates": 1, "est_argmax": 2, "est_lmf": 3, "est_zncc": 4}.get(a, 99)
    ))
    agg_rows = []
    for algo in algos:
        subset = [r for r in all_results if r["algo"] == algo]
        row = [algo]
        for t in TOLS_MM:
            vals = [r[f"hit_{t}mm"] for r in subset]
            row.append(f"{np.mean(vals):.3f}")
        rmses = [r["rmse_mm"] for r in subset]
        row.append(f"{np.mean(rmses):.1f}")
        agg_rows.append(row)
    agg_table = format_table(agg_rows, ["algo"] + [f"hit_{t}mm" for t in TOLS_MM] + ["rmse_mm"])
    print(agg_table)

    # write markdown report
    report = out_dir / "verify_baseline.md"
    with report.open("w") as fp:
        fp.write("# Phase A baseline 实测 (run_verify_baseline.py)\n\n")
        fp.write(f"samples: {len(SAMPLES)}, tols_mm: {TOLS_MM}\n\n")
        fp.write("## Per-sample × algo\n\n```\n")
        fp.write(table + "\n```\n\n")
        fp.write("## Mean across samples\n\n```\n")
        fp.write(agg_table + "\n```\n")
    print(f"\nWritten: {report}")


if __name__ == "__main__":
    main()
