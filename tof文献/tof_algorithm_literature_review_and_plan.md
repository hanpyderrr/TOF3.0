# 单光子 ToF 成像与透雾算法文献总结及代码路线

## 结论先行

你现在初步开始写代码，建议不要一上来就做深度学习或复杂贝叶斯重建。最稳的路线是：

1. **先做基础 ToF 成像链路**：原始 photon histogram -> 标定 -> 背景估计 -> 峰检测 -> 亚 bin 精修 -> 深度图/置信度图。
2. **再做透雾算法**：在时间直方图域分离近距离雾/烟后向散射峰和目标峰，而不是只对最终深度图做图像增强。
3. **最后做高级重建**：泊松/Bayesian/ADMM 或小型神经网络，用来补全低光子、低分辨率和无效像素。

最关键的一点：**一定要保存原始时间直方图或至少多 bin 回波数据**。如果只保存 32x32 的强度/深度结果，后续很多透雾算法都做不了。

## 推荐代码路线

### 第一阶段：基础 ToF 成像，先跑通

输入建议：
- 每个像素的 TCSPC/histogram，形状类似 `H x W x B`，例如 `32 x 32 x 1024`。
- 同步保存暗场、无目标背景、不同距离标定板数据。

核心步骤：
1. 暗计数/背景扣除：用无光或无目标帧估计每个 bin 的背景。
2. pile-up 简单校正：光子数较高时先做经验校正，低光子时可先跳过。
3. 峰检测：先用 `matched filter / smooth + argmax / CFAR threshold`。
4. 亚 bin 定位：对峰附近 3-7 个 bin 做二次曲线或高斯拟合。
5. bin 到距离：`distance = c * (bin - offset) * bin_width / 2`，注意系统延迟 offset。
6. 置信度输出：每个像素输出 `depth, peak_count, background, SBR, peak_width, valid_flag`。
7. 空间后处理：中值滤波、邻域一致性、无效像素填补。

推荐第一版方法：
- 清晰空气：`背景扣除 + CFAR/阈值峰检测 + 高斯局部拟合`
- 低光子：`Poisson log-likelihood / matched filter`
- 输出：深度图 + 置信度图 + 回波质量图

### 第二阶段：透雾算法，重点在直方图域

雾中典型问题：
- 近距离出现强后向散射峰。
- 目标峰变弱、变宽、可能被雾峰拖尾覆盖。
- 多次散射导致峰偏移和长尾。
- 只看最大峰会经常选到雾峰，而不是目标峰。

推荐透雾第一版：
1. 对每个像素或局部 patch 的 histogram 做平滑。
2. 找近距离雾峰和远距离候选目标峰。
3. 用 `lognormal/gamma` 拟合雾/烟散射峰。
4. 用 `Gaussian` 拟合目标峰。
5. 选择满足空间连续性和 SBR 条件的目标峰输出深度。

推荐透雾第二版：
- `Gamma 背向散射模型 + DBSCAN 残差聚类 + Gaussian 目标峰拟合`
- 这条路线来自 2025 Optics Express 单光子去雾文献，适合你后续写论文/创新点。

推荐透雾第三版：
- `dual-Gamma / multinomial pile-up compensation / Bayesian reconstruction`
- 适合极低 SBR、强雾、远距离，但实现复杂。

### 第三阶段：高级重建和深度学习

在你已经有可靠物理算法和实验数据后，再考虑：
- 多帧联合：利用连续帧目标深度相关。
- 空间正则：非局部均值、TV、NLTV、ADMM。
- 贝叶斯重建：输出深度不确定性。
- 深度学习：多尺度直方图输入，做深度超分辨率或无效像素补全。

不建议一开始直接训练网络，因为你现在最缺的是稳定标定数据和真实雾中标签。

## 最推荐优先读的论文

1. `2020.11-SPIE会议论文-澳大利亚-利用统计混合模型减少雾霾环境SPAD图像中的噪声.pdf`
   - 最适合作为透雾第一版算法：lognormal 雾峰 + Gaussian 目标峰 + EM。
2. `Three-dimensional single-photon imaging.pdf`
   - 低 SBR 透雾三维成像核心论文：pile-up 补偿 + dual-Gamma。
3. `2025.12-OpticsExpress-火箭军工程大学-基于密度聚类引导高斯模型拟合的单光子去雾成像方法_translated(1).pdf`
   - 最适合发展成你的创新路线：Gamma + DBSCAN + Gaussian。
4. `Adaptive_Gating_for_Single-Photon_3D_Imaging.pdf`
   - 如果硬件支持门控，值得重点看。
5. `High-speed 3D-imaging based on a range-gated and large SPAD array .pdf`
   - 基础高速单光子 3D 成像链路参考。
6. `Robust real-time 3D imaging of moving scenes through atmospheric obscurant using single-photon LiDAR.pdf`
   - 系统级透雾实时成像参考。

## 论文总览表

| 序号 | 主题 | 文件 | 对项目价值 |
|---:|---|---|---|
| 1 | 雾对成像激光雷达测距分布的影响 | `025022_1_online.pdf` | 可用于设计你的透雾实验指标：不要只看最终深度图，要记录每个像素或区域的时间直方图、峰宽、峰偏移、近距离雾峰强度、目标峰强度。 |
| 2 | SNSPD 单光子激光雷达海雾测量 | `2017.11-ScientificReports-南京大学-测量海况的演示雾采用基于SNSPD的激光雷达系统.pdf` | 对你的系统启发在于：透雾不只是图像增强，还可以从距离回波曲线估计雾层位置和浓度；可把近距离雾峰作为环境参数输入后续算法。 |
| 3 | SNSPD 海雾 LiDAR 中文译文 | `2017.11-ScientificReports-南京大学-测量海况的演示雾采用基于SNSPD的激光雷达系统_translated.pdf` | 建议作为中文快速阅读版，用来写论文综述中单光子探测透雾/测雾应用背景。 |
| 4 | 多时相/多光谱单光子 3D LiDAR 联合重建 | `2019.5-SSPD-赫瑞瓦特大学-多时空或多光谱的联合重建单曲-光子3D 激光雷达图像.pdf` | 适合在基础峰检测跑通后，用作第二阶段重建：把相邻像素、连续帧和多波长信息作为正则项，提升低信噪比下的深度稳定性。 |
| 5 | 多时相/多光谱联合重建中文译文 | `2019.5-SSPD-赫瑞瓦特大学-多时空或多光谱的联合重建单曲-光子3D 激光雷达图像_translated.pdf` | 可作为你后续写“模型驱动重建”章节的主要中文参考。 |
| 6 | 雾霾环境 SPAD 图像统计混合模型降噪 | `2020.11-SPIE会议论文-澳大利亚-利用统计混合模型减少雾霾环境SPAD图像中的噪声.pdf` | 强烈建议作为透雾算法第一版的核心参考：先实现每像素或小块区域的雾峰/目标峰混合拟合，再输出目标峰位置和置信度。 |
| 7 | 雾霾 SPAD 混合模型中文译文 | `2020.11-SPIE会议论文-澳大利亚-利用统计混合模型减少雾霾环境SPAD图像中的噪声_translated.pdf` | 建议先读中文版掌握思路，再按英文原文或公式实现。 |
| 8 | 非均匀背景下多光谱单光子 3D LiDAR 稳健贝叶斯重建 | `2022.5-IEEE-赫瑞瓦特大学-多光谱的稳健贝叶斯重建单曲-光子非均匀背景的3D LIDAR数据.pdf` | 适合你的第二阶段透雾重建：给每个深度像素输出置信度/方差，而不是只给一个深度值；可用于剔除低可信像素。 |
| 9 | 稳健贝叶斯重建中文译文 | `2022.5-IEEE-赫瑞瓦特大学-多光谱的稳健贝叶斯重建单曲-光子非均匀背景的3D LIDAR数据_translated.pdf` | 可作为你写算法路线时“高级鲁棒重建/不确定性估计”的参考。 |
| 10 | DBSCAN 残余聚类引导的单光子去雾三维成像 | `2025.12-OpticsExpress-火箭军工程大学-基于密度聚类引导高斯模型拟合的单光子去雾成像方法_translated(1).pdf` | 建议作为透雾算法第二版：第一版做 lognormal/Gaussian 混合模型；第二版加入 DBSCAN 清理残余散射光子。 |
| 11 | 脉宽补偿的 LiDAR 定时方法 | `A_Sampling-Based_Pulsewidth-Compensated_Timing_Method_Independent_of_Distance_and_Reflectivity_for_LiDAR_Application.pdf` | 适合你做系统标定：不同反射率板、不同距离下测峰宽和深度偏差，建立脉宽/峰宽补偿表。 |
| 12 | 单光子 3D 成像自适应门控 | `Adaptive_Gating_for_Single-Photon_3D_Imaging.pdf` | 如果你的硬件支持可调 gate/window，后续可以用它来减少雾峰或强背景造成的 pile-up；如果不能调门控，也可借鉴其“先粗扫再局部采集”的策略。 |
| 13 | 从物理参数估计单光子 LiDAR 最小测距时间 | `An analytical model from physical parameters to minimum ranging time for.pdf` | 非常适合你做实验前的曝光/积分时间估算：给定雾衰减、目标反射率和距离，估计需要多少帧或多少积分时间。 |
| 14 | dToF Flash LiDAR 异步深度传感 | `Asynchronous Depth Sensing through Direct.pdf` | 你的第一版可以实现帧式 CFAR 峰检测；后续若要实时，可改为每像素达到置信阈值即停止积分或报告。 |
| 15 | 距离选通大 SPAD 阵列高速 3D 成像 | `High-speed 3D-imaging based on a range-gated and large SPAD array .pdf` | 适合你做基础成像代码的参考：先做首次/最强峰检测，再用邻域一致性修复孤立噪声和无效像素。 |
| 16 | 雾中多次散射 LiDAR 回波影响 | `Impact of Multi-Scattered LiDAR Returns in Fog.pdf` | 用于解释实验中目标峰变宽、偏移、弱目标被淹没等现象；算法上应保留峰宽、偏度、SBR等质量指标。 |
| 17 | 多尺度直方图概率深度网络超分辨率 3D LiDAR | `Multi-Scale Histogram-Based Probabilistic Deep Neural Network for Super-Resolution 3D LiDAR Imaging.pdf` | 可作为后期深度学习路线：先用物理算法生成可靠训练标签，再训练小网络做深度补全/超分辨率。 |
| 18 | 大气遮蔽物中运动场景实时单光子 3D 成像 | `Robust real-time 3D imaging of moving scenes through atmospheric obscurant using single-photon LiDAR.pdf` | 建议重点阅读：用于写系统背景、性能目标和实时处理路线；也提醒算法要能处理运动目标，而不是只对静态场景有效。 |
| 19 | SPAD LiDAR 背景光抑制 | `sensors-18-04338-v2.pdf` | 可借鉴为你的质量控制模块：强背景/强雾时，不只看单光子峰值，也看局部符合、事件密度和假警率。 |
| 20 | GAN 生成雾中 LiDAR 数据 | `Simulation of LiDAR Under Fog with Generative Adversarial Networks for Robust 3D Object Detection.pdf` | 如果你后期缺少大量雾中数据，可考虑先建立物理仿真，再用学习方法做数据增强；初期不推荐作为主线。 |
| 21 | SPAD 成像传感器在荧光 LiDAR 中的应用 | `Single-photon avalanche diode imaging sensor for.pdf` | 可作为硬件背景参考，说明 SPAD 阵列不仅能做强回波测距，也能处理弱信号时间分辨成像。 |
| 22 | 低 SBR 雾中三维单光子成像 | `Three-dimensional single-photon imaging.pdf` | 这是透雾算法主线文献之一。建议在混合高斯模型之后，进一步实现 dual-Gamma/伽马模型分离非目标光子。 |
| 23 | 超快 3D 扫描 LiDAR 综述 | `Towards an ultrafast 3D imaging scanning LiDAR.pdf` | 用于写总体背景和系统路线选择；也可帮助你判断是面阵 flash、扫描式还是混合式更适合后续系统。 |
| 24 | 距离选通大 SPAD 阵列高速 3D 成像中文论文 | `基于距离选通和大型单光子雪崩二极管阵列激光雷达系统的高速三维成像.pdf` | 适合中文阅读，直接借鉴其基础成像流程和去噪思路。 |
| 25 | 1550 nm 紧凑型单光子卫星激光测距 | `用于卫星激光测距的紧凑型单光子激光雷达.pdf` | 对硬件结构和抗后向散射有启发，尤其是双基地/光路隔离思路；算法上可借鉴 Hough/轨迹一致性用于动态目标。 |
| 26 | 多尺度直方图概率网络中文论文 | `用于超分辨率3D激光雷达成像的基于多尺度直方图的概率深度神经网络.pdf` | 适合后期提升 32x32 系统空间分辨率：先输出稳定低分辨率深度，再做学习式上采样。 |
| 27 | dToF 异步深度传感中文论文 | `通过直接飞行时间闪光激光雷达实现异步深度传感.pdf` | 可作为你第一版峰检测模块的工程化方向：每个像素输出深度、峰值、噪声地板和 false alarm 风险。 |

## 每篇论文详细总结

# 1. 雾对成像激光雷达测距分布的影响

## 文件
025022_1_online.pdf

## 一句话简介
论文研究雾环境下成像激光雷达测距数据概率密度分布的变化。重点不是提出单光子重建算法，而是分析雾散射会如何改变距离回波分布，使回波不再是简单的目标峰。它对理解透雾实验中的误差来源有价值。

## 核心方法
通过雾条件下的激光雷达回波统计，观察雾散射、后向散射和目标回波对测距概率分布的影响。

## 对你的 ToF 成像代码的启发
可用于设计你的透雾实验指标：不要只看最终深度图，要记录每个像素或区域的时间直方图、峰宽、峰偏移、近距离雾峰强度、目标峰强度。

## 局限和注意事项
更偏物理和统计分析，不是直接可用的单光子 ToF 成像代码方案。

## 抽取到的关键词
LiDAR, fog, scattering, backscatter, gated

## 摘要/首页片段
> ViewOnline ExportCitation RESEARCH ARTICLE | FEBRUARY 28 2018 The effect of fog on the probability density distribution of the ranging data of imaging laser radar Wenhua Song; JianCheng Lai; Zabih Ghassemlooy; Zhiyong Gu; Wei Yan; Chunyong Wang; Zhenhua Li AIP Advances 8, 025022 (2018) https://doi.org/10.1063/1.5011781 Articles You May Be Interested In Turbulence-free ghost imaging Appl. Phys. Lett. (March 2011) Pulsed laser ablation of bulk target and particle products in liquid for nanomaterial fabrication AIP Advances (January 2019) CAPACITIVE PROBE FOR NON DESTRUCTIVE INSPECTION OF EXTERNAL POST ‐ TENSIONED DUCTS: MODELLING BY DPSM TECHNIQUE AIP Conf. Proc. (February 2010) 31 March 2026 08:49:23 AIP ADV ANCES8, 025022 (2018) The eﬀect of fog on the probability density distribution of the ranging data of imaging laser radar Wenhua Song,1 JianCheng Lai, 1,a Zabih Ghassemlooy,2,3 Zhiy

# 2. SNSPD 单光子激光雷达海雾测量

## 文件
2017.11-ScientificReports-南京大学-测量海况的演示雾采用基于SNSPD的激光雷达系统.pdf

## 一句话简介
论文展示了基于超导纳米线单光子探测器的远距离海雾 LiDAR 系统，用于海雾高度、浓度和速度估计。它说明单光子探测在低回波、远距离和散射环境下的优势。

## 核心方法
利用高灵敏度、低暗计数的 SNSPD 接收远距离 Mie 散射回波，并从回波距离分布推断海雾结构。

## 对你的 ToF 成像代码的启发
对你的系统启发在于：透雾不只是图像增强，还可以从距离回波曲线估计雾层位置和浓度；可把近距离雾峰作为环境参数输入后续算法。

## 局限和注意事项
系统尺度是远距离海雾监测，不是近距离 32x32 SPAD 面阵 ToF 成像；硬件 SNSPD 与 PF32/SPAD 阵列差异较大。

## 抽取到的关键词
single-photon, single photon, LiDAR, fog, scattering, backscatter, gated, 雾, 激光雷达

## 摘要/首页片段
> 1 ScIENTIfIc REPORTS | 7: 15113 | DOI:10.1038/s41598-017-15429-y www.nature.com/scientificreports Demonstration of measuring sea fog with an SNSPD-based Lidar system Jiang Zhu1, Yajun Chen1, Labao Zhang1, Xiaoqing Jia1, Zhijun Feng2, Ganhua Wu3, Xiachao Yan1, Jiquan Zhai2, Yang Wu1, Qi Chen1, Xiaoying Zhou1, Zhizhong Wang3, Chi Zhang3, Lin Kang1, Jian Chen1 & Peiheng Wu1 The monitor of sea fogs become more important with the rapid development of marine activities. Remote sensing through laser is an effective tool for monitoring sea fogs, but still challengeable for large distance. We demonstrated a Long-distance Lidar for sea fog with superconducting nanowire single-photon detector (SNSPD), which extended the ranging area to a 180-km diameter area. The system, which was verified by using a benchmark distance measurement of a known island, is applied to the Mie scattering weather predicti

# 3. SNSPD 海雾 LiDAR 中文译文

## 文件
2017.11-ScientificReports-南京大学-测量海况的演示雾采用基于SNSPD的激光雷达系统_translated.pdf

## 一句话简介
这是上一篇 SNSPD 海雾 LiDAR 论文的中文译文，内容更便于快速阅读。核心仍是利用单光子探测器扩展远距离雾探测能力，并从散射回波中估计雾层信息。

## 核心方法
单光子远距离回波采集、Mie 散射回波分析、海雾高度和浓度估计。

## 对你的 ToF 成像代码的启发
建议作为中文快速阅读版，用来写论文综述中单光子探测透雾/测雾应用背景。

## 局限和注意事项
不要和英文原文重复引用太多；算法落地性有限。

## 抽取到的关键词
LiDAR, 单光子, 雾, 散射, 激光雷达

## 摘要/首页片段
> 115113SCIENTIfIc报告|7： |DOI:10.1038/s41598-017-15429-y 耳鼻喉科 www.nature.com/scientificreports 基于 SNSPD 的激光雷达系统测 量海雾的演示 1 1 1 1 2 3 1 2 1 1 1 3 3 1 1 江竹 、陈亚军 、张拉宝 、贾晓青 、冯志军 、吴甘华 、严晓超 、翟继全 、吴 阳 、陈琦 、周晓英 、王志忠 、张驰 、康林 、陈健 、吴培恒1 随着海洋活动的快速发展，海雾监测的重要性日益凸显。激光遥感技术虽是监测海雾的有效手段， 但在远距离探测方面仍存在挑战。我们开发了一种采用超导纳米线单光子探测器（SNSPD）的长距 离激光雷达系统，将测距范围扩展至180公里直径区域。该系统通过已知岛屿的基准距离测量验证 后，成功应用于Mie散射天气预报激光雷达系统。雾回波信号在测距范围内的分布特征 激光雷达系统测得海雾高度为42.3~63.5公里和53.2~74.2公里。根据分布数据推算出雾浓度和雾速，结 果与天气预报相符。由于地球曲率半径的影响，海雾高度约200米，该高度能见度约为90公里。因 此，这种基于 SNSPD 的激光雷达在海雾测量方面的能力接近理论极限，其信噪比极高。 1 2,3 海雾是海洋天气的常见现象，对渔业、航行和飞行安全具有重大影响。激光天气雷达 是一种常用的海 雾探测技术，具有优异的方位精度、距离分辨率以及高质量、低背景噪声的特点。基于单光子探测器 的激光光子雷达用于探测云层范围与浓度、湿度、风场、空气污染、污染物扩散等，并提供天气预报 。 4,5 6 7–13 14,15 16,17 目前，激光雷达天气预报中使用的单光子探测器主要是以盖革模式运行的InGaAs/InP雪崩光电二极 管 。为了提高探测率，采用了主动、被动、栅极脉冲抑制等方法实现自持雪崩淬灭。红外探测效率 通常低于30%，暗计数为几千次 。因此，传统激光雷达用于天气预报的探测范围约为20公里。 SN- SPD 是一种新型单光子探测器 ，具有高探测效率、低暗计数、快速探测率、高灵敏度、宽响应光 谱等优

# 4. 多时相/多光谱单光子 3D LiDAR 联合重建

## 文件
2019.5-SSPD-赫瑞瓦特大学-多时空或多光谱的联合重建单曲-光子3D 激光雷达图像.pdf

## 一句话简介
论文面向雾、水体、伪装等复杂场景，提出利用泊松统计、空间非局部相关、目标光子聚类以及时相/光谱相关性的联合重建方法。它属于较高级的模型优化路线。

## 核心方法
建立包含深度和反射率先验的代价函数，用 ADMM 求解；利用非局部空间相关和多帧/多谱相关性增强低光子数据。

## 对你的 ToF 成像代码的启发
适合在基础峰检测跑通后，用作第二阶段重建：把相邻像素、连续帧和多波长信息作为正则项，提升低信噪比下的深度稳定性。

## 局限和注意事项
实现复杂度较高，实时性和参数调节压力较大；不适合作为第一版代码。

## 抽取到的关键词
single-photon, single photon, TCSPC, ToF, LiDAR, fog, gated, histogram, depth, 3D imaging, Bayesian, denoising, 激光雷达

## 摘要/首页片段
> The aim of this paper is to propose a specialized algorithm to process Multitemporal or Multispectral 3D single-photon Lidar images. Of particular interest are challenging scenar- ios often encountered in real world, i.e., imaging through ob- scurants such as water, fog or imaging multilayered targets such as target behind camouﬂage. To restore the data, the algorithm accounts for data Poisson statistics and available prior knowledge regarding target depth and reﬂectivity esti- mates. More precisely, it accounts for (a) the non-local spa- tial correlations between pixels, (b) the spatial clustering of target returned photons and (c) spectral and temporal corre- lations between frames. An alternating direction method of multipliers (ADMM) algorithm is used to minimize the re- sulting cost function since it offers good convergence proper- ties. The algorithm is validated on real data which show the beneﬁt of the proposed strategy especially when dealing with multi-dimensional 3D data.

# 5. 多时相/多光谱联合重建中文译文

## 文件
2019.5-SSPD-赫瑞瓦特大学-多时空或多光谱的联合重建单曲-光子3D 激光雷达图像_translated.pdf

## 一句话简介
这是联合重建论文的中文译文，清楚概括了泊松统计、非局部空间相关、光谱/时间相关和 ADMM 优化框架。适合快速理解算法结构。

## 核心方法
泊松观测模型 + 深度/反射率先验 + 非局部全变差/协同稀疏 + ADMM。

## 对你的 ToF 成像代码的启发
可作为你后续写“模型驱动重建”章节的主要中文参考。

## 局限和注意事项
与英文版内容重复，实际代码仍需回到原文确认公式细节。

## 抽取到的关键词
TCSPC, LiDAR, 单光子, 雾, 激光雷达, 深度, 三维, 直方图

## 摘要/首页片段
> 本文旨在提出一种专门处理多时相或多光谱三维单光子 激光雷达图像的算法。该算法特别关注现实场景中常见 的挑战性场景，例如穿透水体、雾气等遮挡物进行成 像，或对伪装目标后的多层目标进行成像。为恢复数 据，算法综合考虑了数据的泊松统计特性以及关于目标 深度和反射率估计的先验知识。具体而言，算法考虑了 以下因素：(a)像素间的非局部空间相关性，(b)目标返回 光子的空间聚类特性，(c)帧间光谱与时间相关性。由于 交替方向乘子法（ADMM）算法具有良好的收敛特性， 故采用该算法最小化所得代价函数。通过真实数据验证 表明，该算法在处理多维三维数据时展现出显著优势。 —索引术语 三维激光雷达成像、泊松统计、多光谱/ 多时相、 ADMM 、NR3D、协同稀疏性、非局部全变 差。

# 6. 雾霾环境 SPAD 图像统计混合模型降噪

## 文件
2020.11-SPIE会议论文-澳大利亚-利用统计混合模型减少雾霾环境SPAD图像中的噪声.pdf

## 一句话简介
论文针对 32x32 SPAD 阵列雾中成像，使用对数正态分布拟合雾散射峰、用高斯分布拟合目标峰，通过 EM 求解混合模型。它和你的 32x32 单光子 ToF 系统非常贴近。

## 核心方法
每个像素建立 lognormal + Gaussian 混合模型，用 EM 估计雾峰和目标峰，再从目标峰确定距离。

## 对你的 ToF 成像代码的启发
强烈建议作为透雾算法第一版的核心参考：先实现每像素或小块区域的雾峰/目标峰混合拟合，再输出目标峰位置和置信度。

## 局限和注意事项
原文指出距离估计准确性仍有限；真实场景中目标峰弱或多目标时，单个高斯可能不够。

## 抽取到的关键词
single photon, SPAD, ToF, LiDAR, fog, scattering, gated, histogram, depth, 雾

## 摘要/首页片段
> Navigating through fog plays a vital part in many remote sensing tasks. In this paper, we propose an Expectation- Maximization (EM) algorithm for ﬁtting a mixture of lognormal and Gaussian distributions to the probability distributions of photon returns for each pixel of a 32x32 Single Photon Avalanche Diode (SPAD) array image. The distance range of the target can be determined from the probability distribution of photon returns by modeling the peak produced due to fog scattering with a lognormal distribution while the peak produced by the target is modeled by a Gaussian distribution. In order to validate the algorithm, 32x32 SPAD array images of simple shapes (triangle, circle and square) are imaged at visibilities down to 50.8m through the fog in an indoor tunnel. Several aspects of the algorithm performance are then assessed. It is found that the algorithm can reconstruct and distinguish diﬀerent shapes for all of our experimental fog conditions. Classiﬁcation of shapes using only the total area of the shape is found to be 100% accurate for our tested fog conditions. However, it is found that the accuracy of the distance range of the target using the estimated model is poor. The

# 7. 雾霾 SPAD 混合模型中文译文

## 文件
2020.11-SPIE会议论文-澳大利亚-利用统计混合模型减少雾霾环境SPAD图像中的噪声_translated.pdf

## 一句话简介
这是统计混合模型论文的中文译文，明确说明雾散射峰可用对数正态建模，目标回波峰用高斯建模，并用 EM 拟合。它对你实现透雾代码非常直接。

## 核心方法
lognormal 雾峰 + Gaussian 目标峰 + EM 参数估计。

## 对你的 ToF 成像代码的启发
建议先读中文版掌握思路，再按英文原文或公式实现。

## 局限和注意事项
翻译版可能有术语误差，公式和参数要回查原文。

## 抽取到的关键词
SPAD, ToF, fog, 单光子, 透雾, 雾, 散射, 激光雷达, 深度, 三维, 直方图

## 摘要/首页片段
> 在众多遥感任务中，雾区导航技术至关重要。本文提出一种期望最大化（EM）算法，用于拟合32x32单光子雪 崩二极管（SPAD）阵列图像中每个像素光子返回概率分布的对数正态与高斯混合分布。通过将雾散射产生的峰 值建模为对数正态分布，而将目标产生的峰值建模为高斯分布，可从光子返回概率分布中确定目标距离范围。 为验证算法有效性，我们在室内隧道中对50.8米能见度的雾区拍摄了三角形、圆形和正方形等简单形状的32x32 SPAD阵列图像。随后对算法性能的多个方面进行了评估。研究发现，该算法能在所有实验雾条件下重建并区分 不同形状。仅使用形状总面积进行分类时，测试雾条件下的准确率达到100%。然而，使用该模型估算的目标距 离范围准确性较差。因此，未来的工作将致力于研究更优的统计混合模型及估计方法。

# 8. 非均匀背景下多光谱单光子 3D LiDAR 稳健贝叶斯重建

## 文件
2022.5-IEEE-赫瑞瓦特大学-多光谱的稳健贝叶斯重建单曲-光子非均匀背景的3D LIDAR数据.pdf

## 一句话简介
论文提出分层贝叶斯算法，面向雾、水等遮蔽物导致的高且非均匀背景噪声，联合估计目标深度、反射率和不确定性。它强调不确定性输出，适合做鲁棒决策。

## 核心方法
分层贝叶斯建模、多尺度信息融合、变量相关性加权、输出深度和反射率的点估计与不确定性。

## 对你的 ToF 成像代码的启发
适合你的第二阶段透雾重建：给每个深度像素输出置信度/方差，而不是只给一个深度值；可用于剔除低可信像素。

## 局限和注意事项
计算复杂，依赖先验和参数；初版不建议直接完整复现。

## 抽取到的关键词
single-photon, SPAD, ToF, LiDAR, fog, scattering, histogram, depth, 3D imaging, Bayesian, denoising, super-resolution

## 摘要/首页片段
> This paper presents a new Bayesian algorithm for the robust reconstruction of multispectral single-photon Lidar data ac- quired in extreme conditions. We focus on imaging through obscurants (i.e., fog, water) leading to high and possibly non-uniform background noise. The proposed hierarchical Bayesian method accounts for multiscale information to pro- vide distribution estimates for the target’s depth and reﬂec- tivity, i.e., point and uncertainty measures of the estimates to improve decision making. The correlations between variables are enforced using a weighting scheme that allows the incor- poration of guide information available from other sensors or state-of-the-art algorithms. Results on synthetic and real data show improved reconstruction of the scene in extreme conditions when compared to the state-of-the-art algorithms.

# 9. 稳健贝叶斯重建中文译文

## 文件
2022.5-IEEE-赫瑞瓦特大学-多光谱的稳健贝叶斯重建单曲-光子非均匀背景的3D LIDAR数据_translated.pdf

## 一句话简介
中文译文概括了极端背景噪声下的多光谱单光子 LiDAR 贝叶斯重建。重点是多尺度信息、引导信息和不确定性估计。

## 核心方法
分层贝叶斯 + 多尺度 + 引导信息加权。

## 对你的 ToF 成像代码的启发
可作为你写算法路线时“高级鲁棒重建/不确定性估计”的参考。

## 局限和注意事项
同英文版重复，具体实现仍需看公式。

## 抽取到的关键词
SPAD, ToF, LiDAR, 单光子, 雾, 激光雷达, 深度, 三维, 直方图

## 摘要/首页片段
> 本文提出了一种新型贝叶斯算法，用于在极端环境下对 多光谱单光子激光雷达数据进行鲁棒重建。针对雾、水 等遮蔽物导致的高背景噪声（可能不均匀分布）成像问 题，我们开发了分层贝叶斯方法。该方法通过整合多尺 度信息，不仅能精确估算目标深度和反射率，还能提供 点估计值及其不确定性度量，从而优化决策过程。通过 加权方案强制变量间相关性，可有效整合其他传感器提 供的引导信息或先进算法。实验结果表明，相较于现有 最先进算法，该方法在极端环境下对场景的重建效果显 著提升。 —索引术语 三维重建、多光谱激光雷达成像、遮蔽 物、贝叶斯推断、鲁棒估计。

# 10. DBSCAN 残余聚类引导的单光子去雾三维成像

## 文件
2025.12-OpticsExpress-火箭军工程大学-基于密度聚类引导高斯模型拟合的单光子去雾成像方法_translated(1).pdf

## 一句话简介
论文提出先用伽马模型拟合并分离烟雾背向散射峰，再用 DBSCAN 分析拟合残差、去除残余噪声光子，最后对目标光子做高斯拟合得到深度。它是当前最贴合你透雾成像目标的路线之一。

## 核心方法
Gamma 背向散射模型 + DBSCAN 残差聚类 + Gaussian 目标峰拟合。

## 对你的 ToF 成像代码的启发
建议作为透雾算法第二版：第一版做 lognormal/Gaussian 混合模型；第二版加入 DBSCAN 清理残余散射光子。

## 局限和注意事项
译文显示年份为 2025/2026，需确认正式发表信息；DBSCAN 参数对不同雾浓度和光子数敏感。

## 抽取到的关键词
TCSPC, ToF, 单光子, 雾, 散射, 激光雷达, 深度, 三维, 直方图

## 摘要/首页片段
> 在强烟雾散射环境中，单光子计数激光雷达面临双重挑战：强烈的散射噪声与低 回波光子计数，这导致信噪比（SNR）极低，进而严重限制烟雾穿透成像性能。残余噪 声光子在烟雾环境中的背向散射峰进行伽马模型拟合后仍持续存在，并干扰目标高斯模 型拟合的准确性。为解决这一问题，本研究提出了一种基于 DBSCAN 残余聚类引导的 高斯模型拟合的烟雾穿透三维成像算法。首先构建伽马模型以拟合回波光子数据，提供 目标回波位置的初始估计并分离背向散射峰；随后设计 DBSCAN 密度聚类算法分析拟 合残差，有效识别并去除残余噪声光子，从而精确分离目标信号峰；最后对滤波后的目 标光子进行高斯模型拟合，实现高精度深度估计。该方法通过 DBSCAN 密度聚类技 术，有效实现了烟雾散射环境中的信号与噪声分离。在米德尔伯里模拟数据集的实验结 果表明，相较于传统算法，所提算法在不同烟雾颗粒尺寸（0.4、

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

# 19. SPAD LiDAR 背景光抑制

## 文件
sensors-18-04338-v2.pdf

## 一句话简介
论文提出基于自适应 photon coincidence detection 的背景光抑制方法，改善户外强背景下 SPAD LiDAR 的动态范围。

## 核心方法
自适应调整光子符合检测参数，同时压制背景事件并保持目标测量性能。

## 对你的 ToF 成像代码的启发
可借鉴为你的质量控制模块：强背景/强雾时，不只看单光子峰值，也看局部符合、事件密度和假警率。

## 局限和注意事项
偏电路/检测策略；如果硬件只输出累积直方图，能借鉴但不一定能完整实现。

## 抽取到的关键词
single-photon, single photon, SPAD, time-of-flight, ToF, LiDAR, histogram, depth

## 摘要/首页片段
> Light detection and ranging (LiDAR) systems based on silicon single-photon avalanche diodes (SPAD) offer several advantages, like the fabrication of system-on-chips with a co-integrated detector and dedicated electronics, as well as low cost and high durability due to well-established CMOS technology. On the other hand, silicon-based detectors suffer from high background light in outdoor applications, like advanced driver assistance systems or autonomous driving, due to the limited wavelength range in the infrared spectrum. In this paper we present a novel method based on the adaptive adjustment of photon coincidence detection to suppress the background light and simultaneously improve the dynamic range. A major disadvantage of ﬁxed parameter coincidence detection is the increased dynamic range of the resulting event rate, allowing good measurement performance only at a speciﬁc target reﬂectance. To overcome this limitation we have implemented adaptive photon coincidence detection. In this technique the parameters of the photon coincidence detection are adjusted to the actual measured background light intensity, giving a reduction of the event rate dynamic range and allowing the pe

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

# 21. SPAD 成像传感器在荧光 LiDAR 中的应用

## 文件
Single-photon avalanche diode imaging sensor for.pdf

## 一句话简介
论文展示 SPAD 成像传感器用于亚表面荧光 LiDAR。它说明 SPAD 阵列在弱光、时间分辨和深度相关成像中的能力。

## 核心方法
SPAD 阵列采集时间相关光子信号，用于荧光/深度相关成像。

## 对你的 ToF 成像代码的启发
可作为硬件背景参考，说明 SPAD 阵列不仅能做强回波测距，也能处理弱信号时间分辨成像。

## 局限和注意事项
应用方向不是透雾 ToF；算法参考价值一般。

## 抽取到的关键词
single-photon, single photon, SPAD, LiDAR, fog, scattering, histogram, depth, 3D imaging

## 摘要/首页片段
> 1126 Vol. 8, No. 8 / August 2021 / Optica Memorandum Single-photon avalanche diode imaging sensor for subsurface fluorescence LiDAR P/e.sc/t.sc/r.sc B/r.sc/u.sc/z.sc/a.sc,1,* A/r.sc/t.sc/h.sc/u.sc/r.sc P/e.sc/t.sc/u.sc/s.sc/s.sc/e.sc/a.sc/u.sc,1 A/r.sc/i.sc/n.sc U/l.sc/k.sc/u.sc,2 J/a.sc/s.sc/o.sc/n.sc G/u.sc/n.sc/n.sc,1 S/a.sc/m.sc/u.sc/e.sc/l.sc S/t.sc/r.sc/e.sc/e.sc/t.sc/e.sc/r.sc,1 K/i.sc/m.sc/b.sc/e.sc/r.sc/l.sc/e.sc/y.sc S/a.sc/m.sc/k.sc/o.sc/e.sc,1,3 C/l.sc/a.sc/u.sc/d.sc/i.sc/o.sc B/r.sc/u.sc/s.sc/c.sc/h.sc/i.sc/n.sc/i.sc,2 E/d.sc/o.sc/a.sc/r.sc/d.sc/o.sc C/h.sc/a.sc/r.sc/b.sc/o.sc/n.sc,2 AND B/r.sc/i.sc/a.sc/n.sc P/o.sc/g.sc/u.sc/e.sc1,3 1Thayer School of Engineering, Dartmouth College, Hanover, New Hampshire 03766, USA 2Advanced Quantum Architecture Laboratory, EPFL, 2002 Neuchâtel, Switzerland 3Department of Surgery, Geisel School of Medicine, Hanover, New Hampshire 03755, USA

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

# 23. 超快 3D 扫描 LiDAR 综述

## 文件
Towards an ultrafast 3D imaging scanning LiDAR.pdf

## 一句话简介
综述扫描式 3D LiDAR 的高速成像技术，包括扫描机制、ToF、探测器和重建方法。适合建立整体技术路线图。

## 核心方法
综述性质，比较多种高速扫描 LiDAR 架构和关键技术。

## 对你的 ToF 成像代码的启发
用于写总体背景和系统路线选择；也可帮助你判断是面阵 flash、扫描式还是混合式更适合后续系统。

## 局限和注意事项
不是单一可复现算法。

## 抽取到的关键词
single-photon, time-of-flight, ToF, LiDAR, scattering, gated, depth, 3D imaging

## 摘要/首页片段
> T owards an ultrafast 3D imaging scanning LiDAR system: a review ZHI LI,1,† YAQI HAN,1,† LICAN WU,1 ZIHAN ZANG,1 MAOLIN DAI,2,3 SZE YUN SET,2,3 SHINJI YAMASHITA,2,3 QIAN LI,4 AND H. Y . FU1,* 1Tsinghua Shenzhen International Graduate School, Tsinghua University, Shenzhen 518055, China 2Department of Electrical Engineering and Information Systems, The University of Tokyo, Tokyo 113-8656, Japan 3Research Center for Advanced Science and Technology, The University of Tokyo, Tokyo 153-8904, Japan 4School of Electronic and Computer Engineering, Peking University , Shenzhen 518055, China †These authors contributed equally to this work. *Corresponding author: hyfu@sz.tsinghua.edu.cn Received 15 November 2023; revised 26 March 2024; accepted 27 March 2024; posted 29 March 2024 (Doc. ID 509710); published 29 July 2024 Light detection and ranging (LiDAR), as a hot imaging technology in both industr

# 24. 距离选通大 SPAD 阵列高速 3D 成像中文论文

## 文件
基于距离选通和大型单光子雪崩二极管阵列激光雷达系统的高速三维成像.pdf

## 一句话简介
这是 High-speed 3D-imaging 的中文版本/相关稿，说明了距离选通 SPAD 阵列、改进首次光子算法、邻域反射率去噪和高速动态目标成像。

## 核心方法
range-gated SPAD array + first-photon reconstruction + spatial denoising。

## 对你的 ToF 成像代码的启发
适合中文阅读，直接借鉴其基础成像流程和去噪思路。

## 局限和注意事项
与英文版本重复；硬件规模可能不同。

## 抽取到的关键词
SPAD, TCSPC, ToF, LiDAR, 单光子, 雾, 散射, 激光雷达, 深度, 三维

## 摘要/首页片段
> 在本工作中， 我们展示了一种用于静态和移动物体三维成像的距离选通单光子激光雷达系统。 该系统 采用了一个 512 × 512 硅基单光子雪崩二极管 (SPAD) 阵列探测器，具有高时间分辨率和小像素间距。我 们提出了一种针对选通阵列系统改进的首次光子成像算法。该算法基于相邻像素位置之间的强反射率相 关性进行图像去噪，然后通过检测每个像素的光子来重建深度信息。与传统算法相比，我们提出的方法 在低平均绝对误差 (MAE) 的情况下，图像采集速度提高了 6 倍。最后，我们实现了 43∘ × 43∘ 的大视场 (FOV)， 以0.625 ms 的积分时间对各种移动物体 (乒乓球、 风车和水雾) 进行高分辨率三维成像， 成像帧率 高达 5

# 25. 1550 nm 紧凑型单光子卫星激光测距

## 文件
用于卫星激光测距的紧凑型单光子激光雷达.pdf

## 一句话简介
论文介绍 1550 nm 紧凑型单光子 LiDAR，用于卫星激光测距，包含抑制后向散射噪声、扫描跟踪和绝对测距方法。

## 核心方法
双基地结构抑制后向散射、扫描跟踪、CPPM 和 Hough transform 绝对测距。

## 对你的 ToF 成像代码的启发
对硬件结构和抗后向散射有启发，尤其是双基地/光路隔离思路；算法上可借鉴 Hough/轨迹一致性用于动态目标。

## 局限和注意事项
远距离 SLR 场景，与近距离成像透雾不同。

## 抽取到的关键词
single-photon, SPAD, TCSPC, time-of-flight, ToF, LiDAR, scattering, backscatter, histogram, 单光子, 激光雷达

## 摘要/首页片段
> Satellite laser ranging (SLR), a cornerstone technology in space geodesy, plays a critical role in satellite orbit determination and Earth gravity field inversion. Here, we developed a compact single-photon LiDAR system for SLR operating at 1550 nm. The system features a bistatic configuration for backscattering noise suppression, an enhanced scan-tracking technique toimprovedynamictargetdetectionprobability,andanabsoluterangingmethodutilizingchaotic pulse position modulation (CPPM) and the Hough transform. Experimental results demonstrate a static target absolute ranging of 8.56 km, and dynamic ranging capabilities of up to 953.89 km with a ranging RMSE of 0.41 m. The theoretical normal point precision at high pulse repetition frequencies is estimated to be within a few millimeters. Trajectory and full-waveform analysis further validate the system’s ability to detect radial velocity (−6.53 ∼ −2.05 km/s ) and attitude changesoftargets. Thisworkprovesthefeasibilityofsingle-photonLiDARforSLRapplications and enables what we believe to be new solutions for satellite orbit determination, space target identification, attitude sensing and debris monitoring. © 2025 Optica Publishing Group 

# 26. 多尺度直方图概率网络中文论文

## 文件
用于超分辨率3D激光雷达成像的基于多尺度直方图的概率深度神经网络.pdf

## 一句话简介
中文版本说明用时间多尺度直方图和概率编码器进行 SPAD 深度估计，再结合超分辨率网络将低分辨率深度图上采样。

## 核心方法
多尺度直方图 + 概率编码 + 深度超分辨率。

## 对你的 ToF 成像代码的启发
适合后期提升 32x32 系统空间分辨率：先输出稳定低分辨率深度，再做学习式上采样。

## 局限和注意事项
需要训练数据，且学习结果要防止在雾中产生虚假结构。

## 抽取到的关键词
SPAD, TCSPC, ToF, LiDAR, 单光子, 激光雷达, 深度, 直方图

## 摘要/首页片段
> 基于单光子雪崩二极管 (SPAD) 技术的激光雷达 (LiDAR) 成像，因高精度测量深度值所需的大 型片上直方图峰值检测电路而遭受严重的面积惩罚。 在这项工作中， 提出了一种基于概率估计的SPAD 成 像超分辨率神经网络， 该网络首先使用时间多尺度直方图作为输入。 为了减少片上直方图计算的面积和成 本， 芯片上仅实现了用于计算反射光子的部分直方图硬件。 基于返回光子的分布规律， 首次提出了一种概 率编码器作为网络的一部分来解决 SPAD 的深度估计问题。通过将该神经网络与超分辨率网络联合使用， 利用 16× 多尺度直方图输出实现了 32 × 32 上采样深度估计。 最后， 在实验室中使用32 × 32 SPAD 传感器 系统验证了该神经网络的有效性。

# 27. dToF 异步深度传感中文论文

## 文件
通过直接飞行时间闪光激光雷达实现异步深度传感.pdf

## 一句话简介
中文论文说明用异步峰检测持续监测每像素直方图形成过程，并用 CFAR 风格自适应阈值增强背景噪声下的鲁棒性。

## 核心方法
异步 peak detection + adaptive CFAR threshold。

## 对你的 ToF 成像代码的启发
可作为你第一版峰检测模块的工程化方向：每个像素输出深度、峰值、噪声地板和 false alarm 风险。

## 局限和注意事项
如果 PF32 API 只能给完整帧，异步优势暂时用不上。

## 抽取到的关键词
SPAD, ToF, 单光子, 激光雷达, 深度, 三维, 直方图

## 摘要/首页片段
> ——在本文中，我们提出了一种基于单光子雪崩二极管(SPAD) 的直接飞行时间 (dToF) 闪光激光 雷达技术的新型异步深度传感方法。 我们的方法引入了一种异步峰值检测机制， 该机制持续监测每个像素 内的直方图形成， 从而在不受传统基于帧的系统限制的情况下实现高效、 延迟最小化的深度测量。 一种受 恒虚警率 (CFAR) 方法启发的自适应阈值技术被用于针对环境光子噪声进行鲁棒的峰值检测。 实验验证表 明我们的方法能够异步报告深度事件，在降低延迟和提高效率的同时提供与传统方法相当的精度。最后， 我们提出了一种 SPAD 接收器架构，展示了在先进激光雷达应用中实际硬件实现的潜力。

