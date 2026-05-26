# 12. 单光子 3D 成像自适应门控

## 文件
Adaptive_Gating_for_Single-Photon_3D_Imaging.pdf

## 一句话简介
论文针对强环境光下 SPAD pile-up 问题，提出基于 Thompson sampling 的自适应门控，让门位置根据已有光子观测逐步更新，以降低深度误差和采集时间。

## 核心方法
把门控位置选择建模为序贯决策问题，利用历史光子观测更新门位置。

## 对你的 ToF 成像代码的启发
如果你的硬件支持可调 gate/window，后续可以用它来减少雾峰或强背景造成的 pile-up；如果不能调门控，也可借鉴其“先粗扫再局部采集”的策略。

## 局限和注意事项
需要硬件支持快速门控或可控时间窗口；软件层无法完全替代。

## 抽取到的关键词
single-photon, single photon, SPAD, TCSPC, time-of-flight, ToF, LiDAR, scattering, histogram, depth, 3D imaging, Bayesian, super-resolution

## 摘要/首页片段
> Single-photon avalanche diodes (SPADs) are growing in popularity for depth sensing tasks. However, SPADs still struggle in the presence of high ambient light due to the effects of pile-up. Conventional techniques leverage fixed or asynchronous gating to minimize pile-up effects, but these gating schemes are all non-adaptive, as they are unable to incorporate factors such as scene priors and pre- vious photon detections into their gating strategy. We pro- pose an adaptive gating scheme built upon Thompson sam- pling. Adaptive gating periodically updates the gate posi- tion based on prior photon observations in order to mini- mize depth errors. Our experiments show that our gating strategy results in significantly reduced depth reconstruc- tion error and acquisition time, even when operating out- doors under strong sunlight conditions.
