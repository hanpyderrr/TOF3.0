# 13. 从物理参数估计单光子 LiDAR 最小测距时间

## 文件
An analytical model from physical parameters to minimum ranging time for.pdf

## 一句话简介
论文建立从系统物理参数到最小测距时间的分析模型，用来指导 SPAD LiDAR 架构设计和参数优化。

## 核心方法
将发射功率、距离、反射率、背景、探测效率、暗计数等参数带入光子计数模型，估计达到可靠测距所需时间。

## 对你的 ToF 成像代码的启发
非常适合你做实验前的曝光/积分时间估算：给定雾衰减、目标反射率和距离，估计需要多少帧或多少积分时间。

## 局限和注意事项
模型用于设计和估算，不直接产生深度图。

## 抽取到的关键词
single-photon, single photon, SPAD, TCSPC, time-of-flight, ToF, LiDAR, fog, scattering, gated, histogram

## 摘要/首页片段
> Long-distance light detection and ranging (LiDAR) has been highly demanded for applications on unmanned vehicles and drones. CMOS-fabricated single-photon avalanche diodes (SPADs) play a key role in the receiver end due to their high photo-sensitivity and readiness for system-on-chip integration. However, the large amounts of involved components together with the diverse ranging conditions make engineering and optimizing these modules a daunting challenge. In this work, we have developed an analytical model for calculating minimum ranging time from the physical parameters for a photon-counting LiDAR. The experimental verifications of the model have been performed and a good consistency has been obtained. Our work enables architecture design and optimization for making low-cost high-performance SPAD LiDARs.
