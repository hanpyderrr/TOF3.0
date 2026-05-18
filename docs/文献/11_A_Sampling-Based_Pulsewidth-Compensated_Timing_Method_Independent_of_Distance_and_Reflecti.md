# 11. 脉宽补偿的 LiDAR 定时方法

## 文件
A_Sampling-Based_Pulsewidth-Compensated_Timing_Method_Independent_of_Distance_and_Reflectivity_for_LiDAR_Application.pdf

## 一句话简介
论文研究回波脉宽对 ToF 定时偏差的影响，并提出与距离和反射率相对独立的脉宽补偿方法。它更偏测距精度标定，而不是图像重建。

## 核心方法
分析回波脉宽、补偿值和飞行时间之间的关系，通过采样估计脉宽补偿。

## 对你的 ToF 成像代码的启发
适合你做系统标定：不同反射率板、不同距离下测峰宽和深度偏差，建立脉宽/峰宽补偿表。

## 局限和注意事项
不是单光子 SPAD 直方图透雾算法，更多用于提高清晰空气下的测距一致性。

## 抽取到的关键词
time-of-flight, ToF, LiDAR

## 摘要/首页片段
> Light detection and ranging (LiDAR) with a high-ranging accuracy and large detection range serves as a critical component in the field of optical measurement. In this article, we specifically propose a sampling-based pulsewidth-compensated timing method for LiDAR ranging, which reveals the pulsewidth compensation value indepen- dent of distance and reflectivity. Characteristics of echo signals are analyzed to set up the relationship among the pulsewidth, compensation value, and time of flight. The implementation procedure of the timing method is described in detail, and ranging parameter calibration and experiments are carried out. Distance measurement precision and accuracy within 5 cm are consistently achieved across target boards with a reflectivity of 10% and 90% over ranges from 1 to 50 m. Eventually, a MEMS-based single-beam LiDAR system works to verify the ranging ability, and the experimental results show that the sampling-based pulsewidth- compensated timing method provides a promising potential for LiDAR large dynamic ranging.
