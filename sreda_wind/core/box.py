"""Axis-aligned box value types shared across the engine.

These are plain geometric value types (no sizing policy): a BBox for an obstacle
footprint and a Domain for the computational box. The domain is supplied
explicitly per case (e.g. an AIJ wind-tunnel geometry); it is NOT derived from a
generic formula in the working build path.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BBox:
    """Axis-aligned footprint bounding box of the obstacles."""
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    @property
    def width(self):
        return self.xmax - self.xmin

    @property
    def depth(self):
        return self.ymax - self.ymin


@dataclass(frozen=True)
class Domain:
    """Axis-aligned computational domain (the blockMesh box)."""
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float
    streamwise_axis: str = "x"   # "x" or "y"; the inlet-to-outlet axis

    @property
    def width(self):
        return self.xmax - self.xmin

    @property
    def depth(self):
        return self.ymax - self.ymin

    @property
    def height(self):
        return self.zmax - self.zmin
