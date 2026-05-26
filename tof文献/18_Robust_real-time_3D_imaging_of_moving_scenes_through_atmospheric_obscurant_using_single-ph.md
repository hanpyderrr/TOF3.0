# 18. 大气遮蔽物中运动场景实时单光子 3D 成像

## 文件
Robust real-time 3D imaging of moving scenes through atmospheric obscurant using single-photon LiDAR.pdf

## 一句话简介
论文展示单光子 LiDAR 在雾、烟等大气遮蔽物中对运动场景进行鲁棒实时 3D 成像。它是你透雾 ToF 成像最重要的系统级参考之一。

## 核心方法
利用单光子 ToF 高灵敏度和时间分辨率，结合实时重建算法，在强散射环境中恢复运动目标深度。

## 对你的 ToF 成像代码的启发
建议重点阅读：用于写系统背景、性能目标和实时处理路线；也提醒算法要能处理运动目标，而不是只对静态场景有效。

## 局限和注意事项
具体实现依赖其实验系统和数据，复现需要结合你的硬件输出格式。

## 抽取到的关键词
single-photon, single photon, SPAD, TCSPC, time-of-flight, ToF, LiDAR, fog, haze, scattering, gated, histogram, depth, 3D imaging, Bayesian, super-resolution

## 摘要/首页片段
> 1 Vol.:(0123456789)Scientific Reports | (2021) 11:11236 | https://doi.org/10.1038/s41598-021-90587-8 www.nature.com/scientificreports Robust real‑time 3D imaging of moving scenes through atmospheric obscurant using single‑photon LiDAR Rachael Tobin1*, Abderrahim Halimi1, Aongus McCarthy1, Philip J. Soan2 & Gerald S. Buller1 Recently, time‑of‑flight LiDAR using the single‑photon detection approach has emerged as a potential solution for three‑dimensional imaging in challenging measurement scenarios, such as over distances of many kilometres. The high sensitivity and picosecond timing resolution afforded by single‑photon detection offers high‑resolution depth profiling of remote, complex scenes while maintaining low power optical illumination. These properties are ideal for imaging in highly scattering environments such as through atmospheric obscurants, for example fog and smoke. In this
