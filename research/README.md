# algorithm — 哪吒端 ToF 直方图处理算法原型

P9 算法管道的快速验证原型（Python）。**先用模拟直方图把"雾/目标分离"跑通**，
验证有效后再把 `tof_process.py` 的算法移植到真实采集 `ExampleTOF.cpp` 的处理段。

> 当前 PF32 硬件未到，用与真实 API **完全一致的数据类型/布局**做模拟输入。

## 数据契约（与真实 PF32 一致）

PF32 `getHistogram(pf32, buf, accumSeconds)` 输出 `uint16[noOfPixels × noOfTDCCodes]`，
本原型即 `uint16 ndarray (H, W, BINS) = (32, 32, 1024)`。

反向 start-stop（与 `nezha/acquisition/peak_detect.h` 一致）：
`bin 越大 → 越近`，`dist_mm = (1023 - bin) × 8.25mm`，量程 ≈ 8.45m。

## 文件

| 文件 | 作用 |
|------|------|
| `tof_sim.py` | 物理直方图模拟器：目标峰(Beer-Lambert 双程雾衰减) + 雾后向散射(近距指数拖尾) + 暗计数 + 泊松噪声 |
| `tof_process.py` | 处理：`depth_argmax()`(现有 C 端等价基线) vs `depth_separate()`(雾分离) + 指标 |
| `run_demo.py` | 端到端演示：清空气/中雾对比 + 代表像素直方图 + 目标距离扫描，出 `out/*.png` |

## 运行

```bash
cd research
python3 run_demo.py        # 需 numpy / scipy / matplotlib
# 结果图在 out/： depth_compare.png  pixel_hist.png  sweep_distance.png
```

## 雾分离算法（第一版）

逐像素：扣暗本底(低分位) → 中值滤波估雾散射包络并扣除 → IRF 高斯 matched filter
→ `find_peaks`(显著性 = 峰高/噪声σ) → 选最显著峰 → 抛物线亚 bin 精修。

## 分离效果指标（闭环目标函数）

- 逐像素：SBR(信背比)、峰显著性(峰高/噪声σ)、雾-目标可分度
- 全图：`Q = 有效像素率 × 归一化平均峰显著性`，闭环时**最大化 Q**

## 验证结论

中雾 4m 目标：argmax 命中率 **16%** → 雾分离 **96%**（RMSE 2.4mm）。

距离扫描（中雾）分三段：

| 距离 | argmax | 分离 | 说明 |
|------|--------|------|------|
| 2–3.6m | 100% | 100% | 目标峰强，雾不碍事 |
| 4–5.2m | 97%→2% | **100%** | **分离算法价值区**：argmax 被雾峰带偏，分离能扣雾救回 |
| ≥5.6m | ≈0% | 94%→64% | **物理探测极限**：雾衰减太强，需闭环加激光功率/调焦提 SNR |

→ 量化论证了主动调制闭环的必要性：闭环目标 = 把"分离命中率随距离下降"那条线往远推。

## 待改进

1. 有雾下无效像素偶发假峰（椒盐噪点）→ 加空间一致性/邻域滤波
2. 雾散射包络改用显式 Gamma/指数拟合，比中值滤波更稳
3. pile-up 校正（高光子通量下早 bin 偏置）暂未建模
4. 物理模型参数(α 衰减、β 散射、IRF)待真实 PF32 数据标定替换
5. 验证稳定后移植 `tof_process.py` → `ExampleTOF.cpp` 处理段（C 实现）

> 物理模型为单光子 LiDAR 透雾标准认知（目标峰 Beer-Lambert 双程衰减 +
> 雾近距后向散射峰），具体文献来源待补（联网检索当时服务过载）。
