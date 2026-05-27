"""Shared algorithm contracts for SPAD depth estimation prototypes."""
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
