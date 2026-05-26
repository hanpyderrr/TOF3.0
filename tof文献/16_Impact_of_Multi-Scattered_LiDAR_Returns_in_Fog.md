# 16. 雾中多次散射 LiDAR 回波影响

## 文件
Impact of Multi-Scattered LiDAR Returns in Fog.pdf

## 一句话简介
论文分析雾中多次散射回波对 LiDAR 测距和目标检测的影响。它强调雾中回波不只是单次后向散射，还可能出现展宽、拖尾和偏移。

## 核心方法
从雾散射物理模型和 LiDAR 回波角度研究多次散射返回。

## 对你的 ToF 成像代码的启发
用于解释实验中目标峰变宽、偏移、弱目标被淹没等现象；算法上应保留峰宽、偏度、SBR等质量指标。

## 局限和注意事项
偏物理建模，不是完整图像重建算法。

## 抽取到的关键词
single photon, LiDAR, fog, scattering, backscatter, gated, depth

## 摘要/首页片段
> Citation: Hevisov, D.; Liemert, A.; Reitzle, D.; Kienle, A. Impact of Multi-Scattered LiDAR Returns in Fog. Sensors 2024, 24, 5121. https:// doi.org/10.3390/s24165121 Received: 4 July 2024 Revised: 1 August 2024 Accepted: 6 August 2024 Published: 7 August 2024 Copyright: © 2024 by the authors. Licensee MDPI, Basel, Switzerland. This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution (CC BY) license (https:// creativecommons.org/licenses/by/ 4.0/). sensors Article Impact of Multi-Scattered LiDAR Returns in Fog David Hevisov * , André Liemert, Dominik Reitzle and Alwin Kienle Institute for Laser Technologies in Medicine and Metrology at the University of Ulm (ILM), D-89081 Ulm, Germany; andre.liemert@ilm-ulm.de (A.L.); dominik.reitzle@ilm-ulm.de (D.R.); alwin.kienle@ilm-ulm.de (A.K.) * Correspondence: david.hevisov@ilm-ulm.de Ab
