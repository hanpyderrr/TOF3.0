"""
tof_sim.py — PF32 单光子 TCSPC 直方图物理模拟器（早期原型）

⚠️ **路线状态**：早期 PF32 工程化原型，**reverse start-stop**（55 ps/bin、32×32），
与当前算法研究主线（Gutierrez forward, 80 ps/bin, 64×64）方向分歧。
**保留不动**用于演示物理建模思路 + `run_demo.py` 出图；新算法不要再扩展它，
应该走 ``sim_spad_loader`` + Gutierrez 数据集。

功能
----
合成与真实 PF32 API 完全一致的 ``uint16[H, W, BINS]`` 直方图：
  1. 暗计数 + 环境光：每 bin 泊松小常数
  2. 目标回波峰：高斯(sigma≈IRF) + 1/d² + exp(-2α·d) 双程雾衰减
  3. 雾后向散射：近距强、随距离指数衰减
  4. 泊松采样 → clip uint16

时序约定（与 PF32 真机一致，反向 start-stop）：
    bin 越大 -> 飞行时间越短 -> 目标越近
    dist_mm = (BINS - 1 - bin) * BIN_MM,  BIN_MM = 55 ps × c/2 = 8.25 mm

上游
----
- 无外部数据；纯合成
- ``make_scene(fog_level, laser_power, ball_mm, bg_mm)`` 是主入口

下游
----
- ``tof_process.py``（同一路线的算法原型，调用 ``BINS / BIN_MM / IRF_SIGMA_BINS``）
- ``run_demo.py``（出 depth_compare / pixel_hist / sweep_distance 三图）

依赖
----
- numpy
- 不依赖任何真实数据集

备注
----
- IRF_SIGMA_BINS=1.5 假设系统 IRF ~200 ps FWHM
- ``make_scene`` 默认 5% 像素无目标，模拟低 SNR/边缘
- 物理依据：单光子 LiDAR 透雾标准模型，雾近距散射峰是 argmax 失效根因
"""
import numpy as np

# ── 物理常量 ──────────────────────────────────────────────
BINS      = 1024
BIN_PS    = 55.0                 # 每 bin 时间分辨率 (ps)
C_MM_PS   = 0.299792458          # 光速 mm/ps
BIN_MM    = BIN_PS * C_MM_PS / 2.0   # ≈ 8.243 mm/bin
MAX_MM    = (BINS - 1) * BIN_MM       # ≈ 8434 mm
SENSOR_H  = 32
SENSOR_W  = 32

IRF_SIGMA_BINS = 1.5             # IRF 高斯宽度 (~200ps FWHM)


def bin_to_mm(b):
    return (BINS - 1 - np.asarray(b, dtype=float)) * BIN_MM


def mm_to_bin(d):
    return (BINS - 1) - np.asarray(d, dtype=float) / BIN_MM


# ── 雾散射剖面（与像素无关，均匀雾）──────────────────────
def fog_profile(fog_level, laser_power):
    """返回 shape (BINS,) 的雾后向散射期望计数（未含泊松）。

    对每个 bin 对应距离 r：雾把激光散射回来，强度 ∝
        beta * exp(-2*alpha*r) / (r^2 + r0^2)
    近距(大 bin)最强，随 r 指数衰减 -> 近距偏斜散射峰。
    """
    if fog_level <= 0:
        return np.zeros(BINS, dtype=float)

    alpha = 0.25 * fog_level          # 衰减系数 (1/m)，正比雾浓度
    beta  = 1.0 * fog_level           # 后向散射系数，正比雾浓度
    r_m   = np.clip(bin_to_mm(np.arange(BINS)) / 1000.0, 1e-3, None)  # 距离(m)
    r0    = 0.4                        # 近距软化，避免 r->0 发散
    prof  = beta * np.exp(-2.0 * alpha * r_m) / (r_m ** 2 + r0 ** 2)
    prof  = prof * laser_power * 6.0   # 标度常数：中雾下散射峰达数百 counts
    # 与 IRF 卷积（散射也经同样系统响应展宽）
    prof  = _gauss_smooth(prof, IRF_SIGMA_BINS)
    return prof


def _gauss_smooth(x, sigma):
    rad = int(sigma * 4 + 1)
    k = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(x, k, mode="same")


# ── 向量化生成整帧直方图 ──────────────────────────────────
def make_histograms(depth_mm, fog_level=0.0, laser_power=1.0,
                     reflectivity=1.0, dark=2.0, seed=None):
    """生成 (H, W, BINS) uint16 直方图帧。

    depth_mm     : (H, W) 每像素目标真实距离 (mm)，<=0 表示无目标(只本底+雾)
    fog_level    : 0=清空气, 0.5=中雾, 1.0=浓雾
    laser_power  : 相对激光功率（影响目标峰与雾峰幅度）
    reflectivity : (H,W) 或标量，目标反射率
    dark         : 暗计数+环境光每 bin 期望
    """
    rng = np.random.default_rng(seed)
    H, W = depth_mm.shape
    b = np.arange(BINS)

    # 1) 本底
    expect = np.full((H, W, BINS), dark, dtype=float)

    # 2) 目标峰（向量化）
    d = depth_mm.astype(float)
    has_t = d > 0
    d_safe = np.where(has_t, d, 1.0)
    peak_bin = mm_to_bin(d_safe)                       # (H,W)
    d_m = d_safe / 1000.0
    alpha = 0.25 * fog_level
    refl = np.broadcast_to(reflectivity, (H, W)).astype(float)
    amp = (laser_power * refl / (d_m ** 2 + 0.1)
           * np.exp(-2.0 * alpha * d_m) * 2500.0)      # (H,W) 峰幅标度
    amp = np.where(has_t, amp, 0.0)
    gauss = np.exp(-0.5 * ((b[None, None, :] - peak_bin[:, :, None])
                           / IRF_SIGMA_BINS) ** 2)
    expect += amp[:, :, None] * gauss

    # 3) 雾后向散射（所有像素共享剖面 + 小幅每像素扰动）
    prof = fog_profile(fog_level, laser_power)          # (BINS,)
    if prof.any():
        jitter = rng.normal(1.0, 0.05, size=(H, W, 1))
        expect += prof[None, None, :] * jitter

    # 4) 泊松采样 -> uint16
    expect = np.clip(expect, 0, None)
    counts = rng.poisson(expect)
    return np.clip(counts, 0, 65535).astype(np.uint16)


# ── 场景：背景墙 + 前景目标球 ─────────────────────────────
def make_scene(fog_level=0.0, laser_power=1.0, seed=0,
               bg_mm=6500.0, ball_mm=2800.0, ball_r=0.45):
    """返回 (hist (H,W,BINS) uint16, depth_true (H,W) float)。

    背景墙 ~6.5m，前景球 ~2.8m，5% 无效像素。
    """
    H, W = SENSOR_H, SENSOR_W
    yy, xx = np.mgrid[0:H, 0:W]
    nx = xx / (W - 1) * 2 - 1
    ny = yy / (H - 1) * 2 - 1

    depth = np.full((H, W), bg_mm, dtype=float)
    depth += np.sin(nx * 3.0) * 120 + np.cos(ny * 2.5) * 90  # 墙起伏

    r2 = nx ** 2 + ny ** 2
    in_ball = r2 < ball_r ** 2
    dz = np.sqrt(np.clip(ball_r ** 2 - r2, 0, None))
    depth[in_ball] = (ball_mm - dz * 1200.0)[in_ball]        # 球凸起

    refl = np.where(in_ball, 0.8, 0.5)                       # 球反射率略高

    rng = np.random.default_rng(seed)
    invalid = rng.random((H, W)) < 0.05
    depth_in = depth.copy()
    depth_in[invalid] = 0.0                                  # 无目标像素

    hist = make_histograms(depth_in, fog_level=fog_level,
                           laser_power=laser_power,
                           reflectivity=refl, seed=seed)
    depth_true = depth.copy()
    depth_true[invalid] = 0.0
    return hist, depth_true


if __name__ == "__main__":
    h, d = make_scene(fog_level=0.6)
    print("hist", h.shape, h.dtype, "range", int(h.min()), int(h.max()))
    print("depth_true range mm:", float(d[d > 0].min()), float(d.max()))
    cy, cx = SENSOR_H // 2, SENSOR_W // 2
    print("center pixel argmax bin:", int(h[cy, cx].argmax()),
          "-> mm:", float(bin_to_mm(h[cy, cx].argmax())),
          "(true %.0f)" % d[cy, cx])
