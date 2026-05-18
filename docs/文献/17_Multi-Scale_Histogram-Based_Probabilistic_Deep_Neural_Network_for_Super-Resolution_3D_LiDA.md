# 17. 多尺度直方图概率深度网络超分辨率 3D LiDAR

## 文件
Multi-Scale Histogram-Based Probabilistic Deep Neural Network for Super-Resolution 3D LiDAR Imaging.pdf

## 一句话简介
论文提出以时间多尺度直方图为输入的概率估计深度网络，并结合超分辨率网络，实现从低分辨率 SPAD 输出到高分辨率深度图的重建。

## 核心方法
多尺度 histogram 输入 + 概率编码器 + 超分辨率网络，降低片上直方图硬件成本。

## 对你的 ToF 成像代码的启发
可作为后期深度学习路线：先用物理算法生成可靠训练标签，再训练小网络做深度补全/超分辨率。

## 局限和注意事项
需要数据集和训练资源；初期不要直接依赖它解决透雾物理分离问题。

## 抽取到的关键词
single-photon, SPAD, TCSPC, ToF, LiDAR, histogram, depth, 3D imaging, denoising, super-resolution

## 摘要/首页片段
> LiDAR (Light Detection and Ranging) imaging based on SPAD (Single-Photon Avalanche Diode) technology suffers from severe area penalty for large on-chip histogram peak detection circuits required by the high precision of measured depth values. In this work, a probabilistic estimation- based super-resolution neural network for SPAD imaging that ﬁrstly uses temporal multi-scale histograms as inputs is proposed. To reduce the area and cost of on-chip histogram computation, only part of the histogram hardware for calculating the reﬂected photons is implemented on a chip. On account of the distribution rule of returned photons, a probabilistic encoder as a part of the network is ﬁrst proposed to solve the depth estimation problem of SPADs. By jointly using this neural network with a super-resolution network, 16× up-sampling depth estimation is realized using 32× 32 multi-scale histogram outputs. Finally, the effectiveness of this neural network was veriﬁed in the laboratory with a 32× 32 SPAD sensor system.
