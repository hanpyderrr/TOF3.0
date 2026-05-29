"""
inject_fog.py — 跨雾模型注入工具（算法测试阶段 2）

功能
----
对任意 ``SpadSample``（forward 或 reverse start-stop）叠加可控雾散射回波，
产出 (无雾 GT × 多雾模型 × 多档浓度) 矩阵，评估算法跨雾鲁棒性。

雾模型（见 docs/algorithm_test_plan.md §2.1）:
    gamma       : β · r^(k-1) · exp(-α·r)             [训练用，文献 10 火箭军]
    lognormal   : β · exp(-(ln r - μ)²/2σ²) / r       [测试用，留 TODO]
    exponential : β · exp(-2α·r) / (r² + r₀²)         [测试用，留 TODO]
    mie_lite    : Mie 近似 + 目标峰展宽/拖尾           [测试用，留 TODO]

每模型三档 light / medium / dense，粗对应 Koschmieder 能见度 5m / 3m / 1m
（σ_atm = 3.912 / visibility）。具体物理参数见 _FOG_PRESETS。

上游
----
- 任意 ``sim_spad_loader.SpadSample``（含 hist / start_stop / mean_signal_photons）
- 调用方传 ``model`` / ``level`` 选雾型、可注入 ``rng`` 复现

下游
----
- 新 ``SpadSample``（hist 已叠加雾，sample_id 加后缀 ``__model_level``）
- ``fog_meta`` dict（参数 + 总光子 + peak_bin）供评估关联

依赖
----
- numpy
- ``sim_spad_loader.BINS / BIN_MM / SpadSample / StartStop``

备注
----
- 雾加性叠加在 hist 上（假设激光回波与雾后向散射通路独立），Poisson 可关
- SBR 在叠加后失真，评估端要用 fog_meta 重算
- 算法路线图 Step 6 的核心工具——尚未跑过 5 样本 × 3 雾档全表
"""
from __future__ import annotations

from dataclasses import replace
from typing import Literal, NamedTuple

import numpy as np

from sim_spad_loader import BINS, BIN_MM, SpadSample, StartStop

FogModel = Literal["gamma", "lognormal", "exponential", "mie_lite"]
FogLevel = Literal["light", "medium", "dense"]


class _FogParams(NamedTuple):
    """单档雾物理参数。alpha 单位 1/mm,beta 是相对强度系数。"""
    alpha: float       # 大气消光系数
    beta_rel: float    # 雾光子总数 / 信号光子总数 的目标比例
    k: float           # gamma 形状参数(>=1)


# Koschmieder visibility = 3.912 / α_total (km)。这里 α 单位 1/mm。
# light  ≈ visibility 5m → α ≈ 0.78/m = 7.8e-4 /mm
# medium ≈ visibility 3m → α ≈ 1.30/m = 1.30e-3 /mm
# dense  ≈ visibility 1m → α ≈ 3.91/m = 3.91e-3 /mm
_FOG_PRESETS: dict[FogLevel, _FogParams] = {
    "light":  _FogParams(alpha=7.8e-4, beta_rel=0.3, k=2.0),
    "medium": _FogParams(alpha=1.3e-3, beta_rel=1.0, k=2.0),
    "dense":  _FogParams(alpha=3.9e-3, beta_rel=3.0, k=2.0),
}


# ── bin → distance 映射 ──────────────────────────────────────────────────────
def _bin_distance_mm(start_stop: StartStop) -> np.ndarray:
    """返回 shape (BINS,) 的距离数组(mm),按 start_stop 方向。"""
    bins = np.arange(BINS, dtype=np.float32)
    if start_stop == "forward":
        return bins * BIN_MM
    return (BINS - 1 - bins) * BIN_MM


# ── Gamma 雾 profile ─────────────────────────────────────────────────────────
def _gamma_profile(start_stop: StartStop, params: _FogParams) -> np.ndarray:
    """Γ-分布散射剖面,shape (BINS,),未归一化。"""
    r = _bin_distance_mm(start_stop)  # (BINS,) mm
    # r=0 时 r^(k-1) 可能爆炸或为 0,加 epsilon 稳数值
    r_safe = np.maximum(r, BIN_MM * 0.5)  # 半个 bin 兜底
    profile = (r_safe ** (params.k - 1.0)) * np.exp(-params.alpha * r_safe)
    return profile.astype(np.float32)


_PROFILE_FNS = {
    "gamma": _gamma_profile,
    # 后续按 plan 表格补:
    # "lognormal":  _lognormal_profile,
    # "exponential": _exponential_profile,
    # "mie_lite":   _mie_lite_profile,
}


# ── 主入口 ──────────────────────────────────────────────────────────────────
def inject_fog(
    sample: SpadSample,
    *,
    model: FogModel = "gamma",
    level: FogLevel = "medium",
    rng: np.random.Generator | None = None,
    poisson: bool = True,
) -> tuple[SpadSample, dict]:
    """
    对 sample 叠加指定模型/档位的雾散射回波。

    Returns
    -------
    new_sample : SpadSample
        hist 已叠加雾;depth_mm/start_stop/SBR 等元数据保持(SBR 在叠加后失真,
        评估端要用 fog_meta 重算)。sample_id 后缀 `__{model}_{level}`。
    fog_meta : dict
        {
          "fog_model": str, "fog_level": str,
          "alpha": float, "beta": float, "k": float,
          "peak_bin": int,                  # 雾 profile 最大值位置
          "total_fog_photons_per_pixel": float,
          "rng_seed": int | None,
        }
    """
    if model not in _PROFILE_FNS:
        raise NotImplementedError(
            f"fog model '{model}' not implemented yet; available: {list(_PROFILE_FNS)}"
        )

    params = _FOG_PRESETS[level]
    rng = rng or np.random.default_rng()
    seed_state = rng.bit_generator.seed_seq.entropy if hasattr(rng.bit_generator, "seed_seq") else None  # type: ignore[attr-defined]

    # 1. 算未归一化 profile
    profile = _PROFILE_FNS[model](sample.start_stop, params)  # (BINS,)
    profile_sum = float(profile.sum())
    if profile_sum <= 0:
        raise RuntimeError(f"fog profile sum<=0; params={params}")

    # 2. 算每像素信号光子总数,用 beta_rel 标定雾总光子
    #    若 .mat 提供 mean_signal_photons 就用,否则用 hist.sum 估
    if sample.mean_signal_photons is not None and sample.mean_signal_photons > 0:
        sig_photons = float(sample.mean_signal_photons)
    else:
        sig_photons = float(sample.hist.sum(axis=-1).mean())

    target_fog_photons = params.beta_rel * sig_photons
    beta = target_fog_photons / profile_sum  # 缩放使 sum(beta·profile) = target

    fog_hist_1d = (beta * profile).astype(np.float32)  # (BINS,) 期望光子/bin

    # 3. 广播到 (H,W,BINS),按需 Poisson 采样
    h, w, _ = sample.hist.shape
    if poisson:
        # Poisson 采样:期望率统一,但每 pixel/bin 独立采样
        fog_hist_3d = rng.poisson(lam=np.broadcast_to(fog_hist_1d, (h, w, BINS))).astype(np.float32)
    else:
        fog_hist_3d = np.broadcast_to(fog_hist_1d, (h, w, BINS)).astype(np.float32).copy()

    new_hist = sample.hist + fog_hist_3d

    fog_meta = {
        "fog_model": model,
        "fog_level": level,
        "alpha": params.alpha,
        "beta": beta,
        "k": params.k,
        "peak_bin": int(np.argmax(profile)),
        "total_fog_photons_per_pixel": float(fog_hist_1d.sum()),
        "rng_seed": seed_state,
        "poisson": poisson,
    }
    new_sample = replace(
        sample,
        hist=new_hist,
        sample_id=f"{sample.sample_id}__{model}_{level}",
    )
    return new_sample, fog_meta


# ── 自检 ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Smoke test: 假数据上跑一遍 gamma × 三档,检查 profile 形状/光子守恒。
    数据到位后再跑真 Gutierrez sample。
    """
    fake_hist = np.zeros((4, 4, BINS), dtype=np.float32)
    # 模拟单 peak @ bin 300 (forward 下约 2.47m),每 pixel 1000 信号光子
    fake_hist[:, :, 300] = 1000.0
    fake = SpadSample(
        hist=fake_hist,
        depth_mm=np.full((4, 4), 300 * BIN_MM, dtype=np.float32),
        sbr=10.0,
        mean_signal_photons=1000.0,
        mean_background_photons=0.0,
        sample_id="fake",
        start_stop="forward",
    )
    for lv in ("light", "medium", "dense"):
        out, meta = inject_fog(fake, model="gamma", level=lv, rng=np.random.default_rng(42))  # type: ignore[arg-type]
        print(f"[{lv:6}] α={meta['alpha']:.2e} β={meta['beta']:.2e} "
              f"peak_bin={meta['peak_bin']:4d} fog_photons={meta['total_fog_photons_per_pixel']:.1f} "
              f"hist_sum_after={out.hist.sum(axis=-1).mean():.1f}")
