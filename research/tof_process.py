"""
tof_process.py — TCSPC 直方图处理（早期原型）

⚠️ **路线状态**：与 ``tof_sim.py`` 同源的 PF32 reverse start-stop 路线，
**与当前主线（Gutierrez forward、``research/algorithms/``）分歧**。
保留不动用于 ``run_demo.py`` 出图；新算法都在 ``research/algorithms/`` 写。

功能
----
两条路径，对比 baseline vs 雾分离：
  A) ``depth_argmax(hist)``    : peak_detect.h 等价（直接取最大 bin）
  B) ``depth_separate(hist)``  : 雾/目标分离 ——
       扣暗本底（20% 分位）→ 中值滤波估散射包络 → matched filter（高斯卷积）
       → MAD 估噪声 → find_peaks 取最显著峰 → 抛物线亚 bin 精修
  + ``quality_score(sep)`` 出全图闭环目标 Q = 有效率 × tanh(平均显著性 / 10)
  + ``eval_depth(pred, gt, tol_mm=300)`` 出 (rmse, good_rate, detect_rate)

上游
----
- ``tof_sim.make_histograms / make_scene`` 出 hist
- 仅供 ``run_demo.py`` 调用

下游
----
- ``run_demo.py`` 出 depth_compare / pixel_hist / sweep_distance 三图
- 历史上对应"主动调制闭环"的算法侧入口（commit 22 2026-05-22）

依赖
----
- scipy.ndimage.median_filter / gaussian_filter1d
- scipy.signal.find_peaks
- ``tof_sim.{BINS, BIN_MM, IRF_SIGMA_BINS, bin_to_mm}``

备注
----
- MIN_PEAK_COUNTS=5（与 PF32 C 端 ``peak_detect.h::PD_MIN_COUNTS`` 同步）
- MIN_PROMINENCE=4σ（matched filter 残差中目标峰最小显著性）
- ``depth_separate`` 是双重 for 循环逐像素跑——32×32 OK，64×64 慢，
  迁到主线时应向量化
- 当年实测：中雾 4 m 下 argmax 16% → 分离 96%（RMSE 2.4 mm）
"""
import numpy as np
from scipy.ndimage import median_filter, gaussian_filter1d
from scipy.signal import find_peaks

from tof_sim import BINS, BIN_MM, IRF_SIGMA_BINS, bin_to_mm

MIN_PEAK_COUNTS = 5      # 峰值绝对下限（同 peak_detect.h PD_MIN_COUNTS）
MIN_PROMINENCE  = 4.0    # matched-filter 残差中目标峰的最小显著性（× 噪声σ）


# ── A) argmax 基线（= 现有 C 端 pd_bin_to_depth）──────────
def depth_argmax(hist):
    """hist (H,W,BINS) uint16 -> depth_mm (H,W) float32。"""
    H, W, _ = hist.shape
    peak_bin = hist.argmax(axis=2)
    peak_val = hist.max(axis=2)
    depth = bin_to_mm(peak_bin).astype(np.float32)
    depth[peak_val < MIN_PEAK_COUNTS] = 0.0
    return depth


# ── 亚 bin 抛物线精修 ─────────────────────────────────────
def _parabolic_subbin(y, b):
    if b <= 0 or b >= len(y) - 1:
        return float(b)
    y0, y1, y2 = float(y[b - 1]), float(y[b]), float(y[b + 1])
    denom = (y0 - 2 * y1 + y2)
    if denom == 0:
        return float(b)
    return b + 0.5 * (y0 - y2) / denom


# ── B) 雾/目标分离（逐像素）──────────────────────────────
def _process_pixel(h):
    """单像素直方图 -> (depth_mm, sbr, prominence_sigma, valid)。"""
    h = h.astype(float)

    # 1) 暗本底：低分位作环境/暗计数估计，扣除
    dark = np.percentile(h, 20.0)
    h0 = np.clip(h - dark, 0, None)

    # 2) 散射包络：大窗中值滤波得到慢变雾散射基线，扣掉 -> 残差突出尖峰
    #    目标峰窄(~几 bin)被中值滤波保留为基线低估，雾散射宽缓被当基线扣除
    env = median_filter(h0, size=41, mode="nearest")
    resid = np.clip(h0 - env, 0, None)

    # 3) matched filter：用 IRF 高斯核卷积提升窄峰 SNR
    mf = gaussian_filter1d(resid, IRF_SIGMA_BINS)

    # 4) 噪声水平：残差的稳健 σ（MAD）
    noise = 1.4826 * np.median(np.abs(resid - np.median(resid))) + 1e-6

    # 5) 峰检测：显著性 = 峰高 / 噪声σ
    peaks, props = find_peaks(mf, prominence=MIN_PROMINENCE * noise)
    if len(peaks) == 0:
        return 0.0, 0.0, 0.0, False

    # 6) 选最显著峰作为目标（散射包络已被扣除，近距雾峰被压平）
    proms = props["prominences"]
    k = int(np.argmax(proms))
    pb = int(peaks[k])
    prom_sigma = float(proms[k] / noise)

    # 绝对计数下限（防纯噪声）
    if h0[pb] < MIN_PEAK_COUNTS:
        return 0.0, 0.0, 0.0, False

    # 7) 亚 bin 精修
    pb_sub = _parabolic_subbin(mf, pb)
    depth = float((BINS - 1 - pb_sub) * BIN_MM)
    depth = max(0.0, min(depth, (BINS - 1) * BIN_MM))

    # 8) SBR：峰邻域信号 / 背景本底
    lo, hi = max(0, pb - 3), min(BINS, pb + 4)
    sig = float(h0[lo:hi].sum())
    bg = dark * (hi - lo) + 1e-6
    sbr = sig / bg

    return depth, sbr, prom_sigma, True


def depth_separate(hist):
    """hist (H,W,BINS) -> dict(depth, sbr, prominence, valid)。"""
    H, W, _ = hist.shape
    depth = np.zeros((H, W), np.float32)
    sbr = np.zeros((H, W), np.float32)
    prom = np.zeros((H, W), np.float32)
    valid = np.zeros((H, W), bool)
    for y in range(H):
        for x in range(W):
            d, s, p, v = _process_pixel(hist[y, x])
            depth[y, x], sbr[y, x], prom[y, x], valid[y, x] = d, s, p, v
    return {"depth": depth, "sbr": sbr, "prominence": prom, "valid": valid}


# ── 全图分离质量分 Q（闭环目标函数）──────────────────────
def quality_score(sep):
    """Q = 有效像素率 × 归一化平均峰显著性。越大越好。"""
    valid = sep["valid"]
    rate = valid.mean()
    if valid.any():
        prom_norm = np.tanh(sep["prominence"][valid].mean() / 10.0)
    else:
        prom_norm = 0.0
    return float(rate * prom_norm), float(rate), float(prom_norm)


# ── 评估：对真值算有效区 RMSE ─────────────────────────────
def eval_depth(depth_est, depth_true, tol_mm=300.0):
    """返回 (rmse_mm, good_rate, detect_rate)，分母均为"有目标像素数"。
      detect_rate = 探到任意峰的比例（不论对错）
      good_rate   = 探到且落在真值 ±tol_mm 的比例（核心指标）
      rmse_mm     = 命中像素上的 RMSE
    """
    has_t = depth_true > 0
    n_t = int(has_t.sum())
    if n_t == 0:
        return float("nan"), 0.0, 0.0
    est_v = depth_est > 0
    both = has_t & est_v
    err_all = depth_est - depth_true
    hit = both & (np.abs(err_all) < tol_mm)
    detect_rate = float(both.sum() / n_t)
    good_rate = float(hit.sum() / n_t)
    rmse = float(np.sqrt((err_all[hit] ** 2).mean())) if hit.any() else float("nan")
    return rmse, good_rate, detect_rate
