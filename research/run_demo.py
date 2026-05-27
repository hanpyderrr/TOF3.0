"""
run_demo.py — 模拟直方图 + 雾分离处理 端到端演示

1) 两场景对比（清空气 / 中雾），目标在中距 4m：
   控制台打印 探到率/命中率/RMSE/分离质量分 Q，出 out/depth_compare.png
2) 代表像素直方图 out/pixel_hist.png
3) 目标距离扫描 out/sweep_distance.png：固定中雾，目标从 2m 到 6.5m，
   看 argmax 与分离的命中率随距离怎么变（哪段算法救得回、哪段是物理极限）

用法： python3 run_demo.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tof_sim import (make_scene, make_histograms, bin_to_mm,
                     BINS, SENSOR_H, SENSOR_W)
import tof_process as tp

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)


def run_case(name, fog_level, ball_mm=4000.0, bg_mm=5200.0):
    hist, truth = make_scene(fog_level=fog_level, laser_power=1.0, seed=0,
                             ball_mm=ball_mm, bg_mm=bg_mm)
    d_arg = tp.depth_argmax(hist)
    sep = tp.depth_separate(hist)
    d_sep = sep["depth"]

    rmse_a, good_a, det_a = tp.eval_depth(d_arg, truth)
    rmse_s, good_s, det_s = tp.eval_depth(d_sep, truth)
    Q, rate, prom = tp.quality_score(sep)

    print(f"\n=== {name}  (fog={fog_level}, ball={ball_mm:.0f}mm) ===")
    print(f"{'method':<10}{'detect%':>9}{'good%':>8}{'RMSE_mm':>10}")
    print(f"{'argmax':<10}{det_a*100:>8.1f}{good_a*100:>8.1f}{rmse_a:>10.1f}")
    print(f"{'separate':<10}{det_s*100:>8.1f}{good_s*100:>8.1f}{rmse_s:>10.1f}")
    print(f"分离质量分 Q={Q:.3f}  (有效率={rate*100:.1f}%  归一显著性={prom:.3f})")
    return dict(name=name, fog=fog_level, hist=hist, truth=truth,
                d_arg=d_arg, d_sep=d_sep)


def plot_depth_compare(clear, fog):
    fig, ax = plt.subplots(2, 3, figsize=(11, 7))
    panels = [
        (clear["truth"], "clear: truth"),
        (clear["d_arg"], "clear: argmax"),
        (clear["d_sep"], "clear: separate"),
        (fog["truth"], "fog: truth"),
        (fog["d_arg"], "fog: argmax"),
        (fog["d_sep"], "fog: separate"),
    ]
    for a, (img, title) in zip(ax.ravel(), panels):
        m = a.imshow(np.ma.masked_equal(img, 0), cmap="viridis",
                     vmin=500, vmax=6000)
        a.set_title(title, fontsize=10)
        a.axis("off")
        fig.colorbar(m, ax=a, fraction=0.046, shrink=0.8)
    fig.suptitle("Depth maps (mm) — argmax vs fog-separation", fontsize=12)
    fig.tight_layout()
    p = os.path.join(OUT, "depth_compare.png")
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def plot_pixel_hist(fog):
    cy, cx = SENSOR_H // 2, SENSOR_W // 2
    h = fog["hist"][cy, cx].astype(float)
    true_mm = fog["truth"][cy, cx]
    b = np.arange(BINS); mm = bin_to_mm(b)
    arg_bin = int(h.argmax()); sep_mm = fog["d_sep"][cy, cx]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(mm, h, lw=0.8, color="#333", label="histogram")
    ax.axvline(true_mm, color="green", ls="--", label=f"true {true_mm:.0f}mm")
    ax.axvline(bin_to_mm(arg_bin), color="red", ls=":",
               label=f"argmax {bin_to_mm(arg_bin):.0f}mm")
    if sep_mm > 0:
        ax.axvline(sep_mm, color="blue", ls="-.", label=f"separate {sep_mm:.0f}mm")
    ax.set_xlabel("distance (mm)  [large bin = near]")
    ax.set_ylabel("photon counts")
    ax.set_title(f"Center pixel histogram under fog (pixel {cy},{cx})")
    ax.legend(fontsize=9); ax.invert_xaxis()
    fig.tight_layout()
    p = os.path.join(OUT, "pixel_hist.png")
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def sweep_distance(fog_level=0.5, dists=None):
    """固定中雾，目标为均匀平面，距离从近到远扫，画两法命中率 vs 距离。"""
    if dists is None:
        dists = np.arange(2000, 6600, 400, dtype=float)
    H, W = SENSOR_H, SENSOR_W
    rng = np.random.default_rng(1)
    good_a, good_s = [], []
    for d in dists:
        depth = np.full((H, W), d)
        depth[rng.random((H, W)) < 0.05] = 0.0
        hist = make_histograms(depth, fog_level=fog_level,
                               laser_power=1.0, reflectivity=0.6, seed=int(d))
        truth = np.full((H, W), d); truth[depth == 0] = 0.0
        _, ga, _ = tp.eval_depth(tp.depth_argmax(hist), truth)
        _, gs, _ = tp.eval_depth(tp.depth_separate(hist)["depth"], truth)
        good_a.append(ga * 100); good_s.append(gs * 100)
        print(f"  sweep d={d:.0f}mm  argmax good={ga*100:5.1f}%  "
              f"separate good={gs*100:5.1f}%")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(dists, good_a, "o-", color="red", label="argmax")
    ax.plot(dists, good_s, "s-", color="blue", label="separate")
    ax.set_xlabel("target distance (mm)")
    ax.set_ylabel("good hit rate (%)")
    ax.set_title(f"Hit rate vs distance under fog (fog_level={fog_level})")
    ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout()
    p = os.path.join(OUT, "sweep_distance.png")
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


if __name__ == "__main__":
    clear = run_case("CLEAR", 0.0)
    fog = run_case("FOG", 0.5)
    p1 = plot_depth_compare(clear, fog)
    p2 = plot_pixel_hist(fog)
    print("\n--- 目标距离扫描（中雾）---")
    p3 = sweep_distance(0.5)
    print(f"\n图已保存:\n  {p1}\n  {p2}\n  {p3}")
