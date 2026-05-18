# 20. GAN 生成雾中 LiDAR 数据

## 文件
Simulation of LiDAR Under Fog with Generative Adversarial Networks for Robust 3D Object Detection.pdf

## 一句话简介
论文用生成模型模拟雾中 LiDAR 点云，用于增强恶劣天气目标检测训练数据。它不是单光子 ToF 成像算法，但对构建仿真数据集有启发。

## 核心方法
WGAN-LSTM 学习真实雾中 LiDAR 点云分布，并生成带雾效应的数据。

## 对你的 ToF 成像代码的启发
如果你后期缺少大量雾中数据，可考虑先建立物理仿真，再用学习方法做数据增强；初期不推荐作为主线。

## 局限和注意事项
面向点云目标检测，不面向 SPAD photon histogram 或单光子深度估计。

## 抽取到的关键词
LiDAR, fog, gated, denoising

## 摘要/首页片段
> Collecting real LiDAR data from actual scenarios in adverse weather is an expensive and time-consuming process, yet crucial for developing robust perception algorithms. Publicly available datasets published for relevant purposes are often limited to acquisitions under clear weather, which leads to a lack of diversity for the most challenging and unexpected situations that can be encountered in the real world. Virtual datasets that are generated to include emulated adverse weather conditions will significantly facilitate the development and testing processes of more robust perception algorithms. In this paper, we propose a Wasserstein Generative Adversarial Network (WGAN)–Long Short-Term Memory (LSTM) network architecture trained on real continuous LiDAR point clouds gathered in a foggy environment. The output of the generator portion of the network is projected onto a fully simulated virtual scenario. Instead of directly addressing the domain gap induced by this method, we show indirectly that training on the generated dataset improves the performance and robustness of 3D object detection algorithms.
