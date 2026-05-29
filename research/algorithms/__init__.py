"""
algorithms/ — 深度估计算法实现包

每个子模块导出一个 ``estimate(sample, cfg)`` 函数，返回 ``contracts.DepthEstimate``。
所有算法都不做磁盘 IO，输入 ``SpadSample``，输出 ``DepthEstimate``，便于组合与对比。

模块清单
--------
- ``argmax``         : 直方图直接取峰（baseline）
- ``lmf``            : Gaussian IRF 匹配滤波（FFT 互相关）
- ``bg_sub_argmax``  : K×K 空间池化后 argmax（文件名误导，实为 spatial pooling）
- ``tail_bg_argmax`` : 尾部均匀背景估计 + 减除 + argmax

约定见 docs/research_code_style.md。
"""
