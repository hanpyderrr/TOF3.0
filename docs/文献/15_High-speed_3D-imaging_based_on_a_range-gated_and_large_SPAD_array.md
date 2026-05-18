# 15. 距离选通大 SPAD 阵列高速 3D 成像

## 文件
High-speed 3D-imaging based on a range-gated and large SPAD array .pdf

## 一句话简介
论文使用 512x512 SPAD 阵列和距离选通机制，提出改进首次光子成像算法，并利用邻域反射率相关性去噪，实现高速三维成像。

## 核心方法
range-gated 采集 + first-photon depth reconstruction + 邻域反射率相关去噪。

## 对你的 ToF 成像代码的启发
适合你做基础成像代码的参考：先做首次/最强峰检测，再用邻域一致性修复孤立噪声和无效像素。

## 局限和注意事项
硬件阵列规模和门控能力可能与你不同；首次光子法在雾中可能容易被近距离散射误导。

## 抽取到的关键词
single-photon, single photon, SPAD, TCSPC, time-of-flight, ToF, LiDAR, fog, scattering, backscatter, gated, depth, 3D imaging, denoising, super-resolution

## 摘要/首页片段
> In this work, we present a range-gated single-photon LiDAR system designed for three-dimensional imaging of static and moving objects. The system employs a 512 × 512 silicon-based single-photon avalanche diode (SPAD) array detector, featuring high temporal resolution and small pixel pitch. We propose an improved first-photon imaging algorithm tailored for gated array systems. The algorithm performs image denoising based on the strong reflectance correlation between adjacent pixel positions, and then reconstructs depth information by detecting the photon for each pixel. Compared to traditional algorithms, the method we proposed achieves a 6- fold improvement in image acquisition speed with a low Mean Absolute Error (MAE). Finally, we achieve large field of view (FOV) of 43 ◦ × 43 ◦ , high-resolution 3D imaging of various moving objects (ping pong balls, windmills, and water mist) with an integration time of 0.625 ms, reaching an imaging frame rate of up to 51.3 fps.
