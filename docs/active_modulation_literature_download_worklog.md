# 激光主动调制分离雾与目标：文献下载与阅读工作记录

日期：2026-05-26

## 背景问题

用户提出的研究设想是：通过改变激光调制或采集条件，观察雾散射回波和真实目标回波的响应差异，从而分离雾和目标。

前面讨论中形成的核心判断：

- 如果只改变激光功率，且系统工作在线性区，则雾和目标都会近似等比例增强，无法提供分离信息。
- 如果高/低功率归一化响应比 `R(t) = H_high(t) / (k * H_low(t))` 在雾峰区域和目标峰区域明显不同，则说明功率变化引入了可利用的非线性响应差异，功率调制路线有继续验证价值。
- 如果 `R(t)` 基本是一条平线，则说明功率调制没有提供额外可分离维度，应转向时间门控、焦距扫描、偏振、多频调制或统计混合模型。

## 初步文献判断

目前没有确认到直接使用“高低激光功率差分 + `R(t)` 响应比”来分离雾峰和目标峰的现成论文。

但已有文献覆盖了相邻方向：

1. 多时间门控：改变接收时间窗口，分离雾散射与目标回波。
2. 偏振/phasor ToF：利用雾散射和目标反射在偏振、相位域的差异。
3. Range-gated 主动成像：用时间门控抑制后向散射。
4. SPAD pile-up 建模：证明高光子通量会改变单光子直方图形状，但主要用于补偿而非主动分离。
5. 二值连续波功率调制 LiDAR：说明功率调制 LiDAR 可用于硬目标、气溶胶和云测量。
6. 脉冲压缩/编码调制 LiDAR：通过编码波形和相关检测改善散射介质中的目标探测。

因此更稳妥的研究表述是：

> 现有透雾 ToF 方法多依赖单次直方图统计建模、时间门控、偏振或多频相位分离；尚少见利用不同激光功率下 SPAD pile-up 非线性响应差异来主动分离雾散射峰与目标峰的实验。本文拟通过高/低功率归一化响应比 `R(t)` 验证雾峰与目标峰是否具有可分离的非线性响应特征。

## 新建下载目录

已新建目录：

`E:\codex-workspace\tof_active_modulation_papers`

该目录用于保存本轮主动调制相关论文 PDF 和临时下载文件。

## 计划整理的 6 篇论文

### 1. Time-of-flight imaging in fog using multiple time-gated exposures

定位：最接近“主动改变采集条件分离雾和目标”的论文。

已下载文件：

`E:\codex-workspace\tof_active_modulation_papers\01_Time-of-flight_imaging_in_fog_multiple_time-gated_exposures.pdf`

状态：已成功下载，约 4.0 MB。

相关链接：

- https://cir.nii.ac.jp/crid/2120870839829927936
- https://www.image.media.kyoto-u.ac.jp/en/publication/jrnl-intl/202102-oe/

待做：

- 阅读全文。
- 总结其多 time-gated exposure 如何估计雾散射属性。
- 对比本项目的功率调制/时间窗口软件分离思路。

### 2. Time-of-Flight Imaging in Fog Using Polarization Phasor Imaging

定位：CW-ToF/phasor + 偏振分离雾散射与目标分量。

目标文件：

`E:\codex-workspace\tof_active_modulation_papers\02_Time-of-Flight_Imaging_in_Fog_Using_Polarization_Phasor_Imaging.pdf`

当前状态：未成功下载正文 PDF。当前文件大小约 1.8 KB，是 PMC 的下载挑战页，不是论文正文。

相关链接：

- https://pmc.ncbi.nlm.nih.gov/articles/PMC9104460/
- https://www.mdpi.com/1424-8220/22/9/3159

已尝试：

- 直接下载 PMC PDF。
- 直接下载 MDPI PDF。
- 读取 PMC proof-of-work JS，并尝试生成 cookie。

问题：

- PMC 返回 challenge 页面。
- MDPI 返回 403。

待做：

- 继续寻找可下载 PDF 镜像，或使用 HTML 全文阅读并总结。

### 3. Active imaging through dense fog based on range-gated detection

定位：range-gated detection + 偏振去雾，分析 signal light、backscattering light、forward scattering light。

已下载文件：

`E:\codex-workspace\tof_active_modulation_papers\03_Active_imaging_through_dense_fog_range-gated_polarization.pdf`

状态：已成功下载，约 5.1 MB。

相关链接：

- https://pubmed.ncbi.nlm.nih.gov/37710437/
- Optics Express 31(16), 25527

待做：

- 阅读全文。
- 总结其门控位置、偏振处理和散射光分离逻辑。
- 判断是否能作为本项目“时间门控/主动调制”的强参考。

### 4. Signal Processing Based Pile-up Compensation for Gated SPADs

定位：SPAD pile-up 建模与补偿。它不直接做雾/目标分离，但支撑“高光子通量会改变直方图形状”这一物理基础。

已下载文件：

`E:\codex-workspace\tof_active_modulation_papers\04_Signal_Processing_Based_Pile-up_Compensation_for_Gated_SPADs.pdf`

状态：已成功下载，约 2.1 MB。

相关链接：

- https://arxiv.org/abs/1806.07437

待做：

- 阅读全文。
- 提取 pile-up 观测模型、补偿方法和实验条件。
- 判断是否能改造成“高低功率响应差异”的数学依据。

### 5. Compact lidar system using binary continuous wave power modulation

定位：二值连续波功率调制 LiDAR，可用于硬目标、气溶胶和云测量。它不是单光子透雾分离方案，但能支撑“功率调制 LiDAR 已用于大气/目标测量”。

已下载文件：

`E:\codex-workspace\tof_active_modulation_papers\05_Compact_lidar_binary_continuous_wave_power_modulation.pdf`

状态：已成功下载，约 2.5 MB。

相关链接：

- https://recercat.cat/handle/2117/118189

待做：

- 阅读全文。
- 总结二值功率调制波形、目标/气溶胶/云测量方式。
- 判断它和本项目“高低功率响应比”的关系。

### 6. Pulse compression lidar through scattering media

定位：脉冲压缩/编码调制 LiDAR，通过编码波形和相关检测改善 fog、haze、smoke 等散射介质中的目标探测。

当前状态：尚未下载到 PDF。

已知问题：

- 初步找到的是 ScienceDirect 摘要页，未确认开放 PDF。
- 还需要继续查作者稿、机构仓储或其他开放版本。

待做：

- 继续检索 `Pulse compression lidar through scattering media`、`A scheme of pulse compression lidar with enhanced modulated bandwidth` 等关键词。
- 若无法取得全文，则保存正式摘要页信息，并在总结中标注“未取得全文，基于摘要总结”。

## 下载目录当前文件状态

截至中断前，下载目录中重要文件如下：

| 文件 | 大小 | 判断 |
|---|---:|---|
| `01_Time-of-flight_imaging_in_fog_multiple_time-gated_exposures.pdf` | 4031114 | 正常 PDF |
| `02_Time-of-Flight_Imaging_in_Fog_Using_Polarization_Phasor_Imaging.pdf` | 1816 | 非正文 PDF，疑似 PMC challenge 页面 |
| `03_Active_imaging_through_dense_fog_range-gated_polarization.pdf` | 5070396 | 正常 PDF |
| `04_Signal_Processing_Based_Pile-up_Compensation_for_Gated_SPADs.pdf` | 2087136 | 正常 PDF |
| `05_Compact_lidar_binary_continuous_wave_power_modulation.pdf` | 2542487 | 正常 PDF |
| `test_1.dat` | 10950964 | NAIST 下载测试文件，可能也是第 1 篇相关 PDF，待确认 |
| `test_3.dat` | 79712 | NAIST 仓储下载测试文件，待确认 |
| `test_6.dat` | 2318 | Optica 下载测试页，不是 PDF |
| `test_7.dat` | 2320 | Optica 下载测试页，不是 PDF |
| `pmc_pow.js` / `pmc_vendor.js` / `pmc_cookie.js` | 临时文件 | 用于尝试 PMC proof-of-work 下载，可后续清理 |

## 后续建议

建议下一步按以下顺序继续：

1. 先阅读已成功下载的 1、3、4、5 四篇。
2. 给每篇单独写一份 Markdown 总结，放在 `tof文献` 或新建子目录中。
3. 继续获取第 2 篇 PDF；如果仍然受阻，则直接基于 PMC/MDPI HTML 全文总结。
4. 继续检索第 6 篇开放版本；如果拿不到全文，则基于摘要页总结，并明确标注限制。
5. 总结时重点回答：这篇是否真的做了“主动改变激励/采集条件”，它如何区分雾散射和目标回波，对本项目的功率调制、时间门控、焦距扫描分别有什么启发。

## 与本项目方案的暂定结论

功率调制路线不应作为唯一主算法，而更适合作为辅助判别特征：

- 用 `R(t)` 检测早期雾峰区域是否出现非线性响应。
- 将异常区域标记为雾/pile-up 风险区。
- 在低异常或模型残差区域寻找目标峰。
- 与 Gamma/lognormal 雾峰模型、Gaussian 目标峰模型、时间门控或焦距扫描联合使用。

更稳的整体路线是：

1. 单帧直方图模型：雾峰 `Gamma/lognormal`，目标峰 `Gaussian`。
2. 主动响应特征：高低功率 `R(t)` 或多时间窗口响应。
3. 目标恢复：避开强雾/pile-up 区域后做目标峰拟合。
4. 置信度输出：输出深度、目标峰强度、雾峰强度、`R(t)` 异常度、SBR 和 valid flag。
