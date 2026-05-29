"""
contracts.py — research/ 共享数据契约

功能
----
定义算法之间约定的"输入/输出/配置"形态：
- ``AlgoConfig`` : 各算法 Config dataclass 的基类，便于统一传参
- ``DepthEstimate`` : 算法输出统一容器（depth + confidence + 元信息）

上游
----
- 算法实现：research/algorithms/*.py 继承 ``AlgoConfig`` 定义自己的参数
- 数据加载：``sim_spad_loader.SpadSample`` 是另一边的契约（输入端）

下游
----
- 评估：``eval/metrics.compute_all`` 接收 ``DepthEstimate``
- 可视：``eval/viz.plot_sanity_panel`` 接收 ``DepthEstimate``
- 入口脚本：``run_sanity / run_benchmark / run_accumulation / run_verify_baseline``

依赖
----
- numpy (np.ndarray 仅作类型注解)
- 无第三方依赖；纯 dataclass

备注
----
- ``depth_mm`` 形状 (H, W)，单位毫米；无效像素请用 0.0
- ``confidence`` 形状 (H, W)，[0, 1]
- ``extras`` 留给算法塞中间量（peak_bin、bg_level 等），不入主指标
- 不要在该文件加业务逻辑——它只是契约
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class AlgoConfig:
    """Base class for algorithm configuration dataclasses."""


@dataclass
class DepthEstimate:
    """Depth estimate returned by algorithm implementations."""

    depth_mm: np.ndarray
    confidence: np.ndarray
    algo_name: str
    extras: dict = field(default_factory=dict)
