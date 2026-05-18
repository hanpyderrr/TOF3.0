# 14. dToF Flash LiDAR 异步深度传感

## 文件
Asynchronous Depth Sensing through Direct.pdf

## 一句话简介
论文提出不等整帧直方图完成，而是在每个像素直方图形成过程中连续监测峰值，满足阈值就报告深度事件，从而降低延迟。

## 核心方法
异步峰值检测 + 类 CFAR 自适应阈值，对环境光噪声保持鲁棒。

## 对你的 ToF 成像代码的启发
你的第一版可以实现帧式 CFAR 峰检测；后续若要实时，可改为每像素达到置信阈值即停止积分或报告。

## 局限和注意事项
更偏硬件/实时架构；软件离线处理时收益不明显。

## 抽取到的关键词
single-photon, single photon, SPAD, time-of-flight, ToF, LiDAR, histogram, depth

## 摘要/首页片段
> In this paper, we present a novel asynchronous depth-sensing approach utilizing direct Time-of-Flight (dToF) flash LiDAR technology based on Single Photon Avalanche Diodes (SPAD). Our method introduces an asynchronous peak detection mechanism that continuously monitors histogram formation within each pixel, enabling efficient, latency-minimized depth measurement without the constraints of traditional frame-based systems. An adaptive thresholding technique inspired by the Con- stant False Alarm Rate (CFAR) method is utilized for robust peak detection against ambient photon noise. Experimental validation demonstrates our method’s ability to asynchronously report depth events, providing comparable accuracy to conventional methods with reduced latency and enhanced efficiency. Finally, we have proposed a SPAD receiver architecture that showcases the potential for practical hardware implementation in advanced LiDAR applications.
