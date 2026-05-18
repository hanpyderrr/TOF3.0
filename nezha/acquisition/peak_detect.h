#pragma once
/*
 * peak_detect.h — TCSPC 直方图峰值检测（哪吒端共用）
 *
 * ExampleTOF.cpp（真实 PF32）和 sim_pf32.cpp（模拟器）共享同一套实现，
 * 保证模拟路径和真实路径的距离换算完全一致。
 *
 * 时序约定（反向 start-stop）：
 *   bin 越大 → 飞行时间越短 → 目标越近
 *   dist_mm = (TDC_BINS - 1 - peak_bin) × BIN_SIZE_MM
 */
#include <stdint.h>

#define PD_TDC_BINS    1024
#define PD_BIN_MM      8.25f    /* 55 ps × c/2 */
#define PD_MIN_COUNTS  5        /* 峰值低于此阈值视为噪声，返回 0 */

/*
 * pd_bin_to_depth() — 对单像素直方图做峰值检测，返回距离（mm）
 *
 * 输入：hist[bins]   该像素的 TDC 计数直方图
 *       bins         直方图 bin 数（通常 1024）
 * 返回：距离（mm），若峰值计数 < PD_MIN_COUNTS 则返回 0（无效像素）
 *
 * 算法：argmax 法（O(bins)），峰值不足时返回 0
 */
static inline uint16_t pd_bin_to_depth(const uint16_t *hist, unsigned int bins)
{
    uint16_t     maxVal  = 0;
    unsigned int peakBin = 0;

    for (unsigned int b = 0; b < bins; ++b) {
        if (hist[b] > maxVal) {
            maxVal  = hist[b];
            peakBin = b;
        }
    }

    if (maxVal < PD_MIN_COUNTS) return 0;

    float dist = (float)(bins - 1u - peakBin) * PD_BIN_MM;
    if (dist > 8450.f) dist = 8450.f;
    return (uint16_t)(dist + 0.5f);
}
