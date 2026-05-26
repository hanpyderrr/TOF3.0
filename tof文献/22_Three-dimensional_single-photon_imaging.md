# 22. 低 SBR 雾中三维单光子成像

## 文件
Three-dimensional single-photon imaging.pdf

## 一句话简介
论文针对雾和背景噪声导致的极低 SBR，提出基于多项分布观测模型补偿 pile-up，并用 dual-Gamma 估计剔除非信号光子，实现远距离透雾 3D 成像。

## 核心方法
multinomial observation model + pile-up compensation + dual-Gamma estimation 分离散射/噪声光子和目标光子。

## 对你的 ToF 成像代码的启发
这是透雾算法主线文献之一。建议在混合高斯模型之后，进一步实现 dual-Gamma/伽马模型分离非目标光子。

## 局限和注意事项
模型实现比简单峰检测复杂，参数估计需要足够的时间直方图数据。

## 抽取到的关键词
single-photon, SPAD, ToF, LiDAR, fog, scattering, backscatter, gated, histogram, depth, 3D imaging

## 摘要/首页片段
> Due to the strong scattering of fog and the strong background noise, the signal-to- background ratio (SBR) is extremely low, which severely limits the 3D imaging capability of single-photondetectorarraythroughfog. Here,weproposeanoutdoorthree-dimensionalimaging algorithmthroughfog,whichcanseparatesignalphotonsfromnon-signalphotons(scatteringand noise photons) with SBR as low as 0.003. This is achieved by using the observation model based on multinomial distribution to compensate for the pile-up, and using dual-Gamma estimation to eliminate non-signal photons. We show that the proposed algorithm enables accurate 3D imaging of 1.4 km in the visibility of 1.7 km. Compared with the traditional algorithms, the target recovery (TR) of the reconstructed image is improved by 20.5%, and the relative average ranging error (RARE) is reduced by 28.2%. It has been successfully demonstrated for targets at different distances and imaging times. This research successfully expands the fog scattering estimation model from indoor to outdoor environment, and improves the weather adaptability of the single-photon detector array. © 2022 Optica Publishing Group under the terms of the Optica Open Access P
