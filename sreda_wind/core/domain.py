"""Computational domain sizing following COST 732 / AIJ recommendations.

The blockMesh box is axis-aligned. The streamwise axis (most aligned with the
flow) gets the inlet padding upstream and the outlet padding downstream; the
cross-stream axis gets symmetric lateral padding; the top is the height
padding. All paddings are multiples of the obstacle height H.

Note: for a diagonal wind the dominant axis is treated as streamwise. This is
exact for axis-aligned winds (cardinal directions) and a reasonable
approximation otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass

from .wind import flow_vector


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
class DomainFactors:
    """COST 732 domain extent factors, in multiples of H."""
    inlet: float = 5.0
    outlet: float = 8.0
    lateral: float = 2.5
    height: float = 5.0


@dataclass(frozen=True)
class Domain:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float
    streamwise_axis: str   # "x" or "y"

    @property
    def width(self):
        return self.xmax - self.xmin

    @property
    def depth(self):
        return self.ymax - self.ymin

    @property
    def height(self):
        return self.zmax - self.zmin


def compute_domain(bbox, H, direction_deg, factors=None):
    """Size the axis-aligned CFD domain around bbox for a given wind direction."""
    if factors is None:
        factors = DomainFactors()

    fx, fy = flow_vector(direction_deg)
    inlet = factors.inlet * H
    outlet = factors.outlet * H
    lateral = factors.lateral * H

    if abs(fx) >= abs(fy):
        # x streamwise, y cross-stream
        if fx >= 0.0:
            xmin = bbox.xmin - inlet
            xmax = bbox.xmax + outlet
        else:
            xmin = bbox.xmin - outlet
            xmax = bbox.xmax + inlet
        ymin = bbox.ymin - lateral
        ymax = bbox.ymax + lateral
        streamwise = "x"
    else:
        # y streamwise, x cross-stream
        if fy >= 0.0:
            ymin = bbox.ymin - inlet
            ymax = bbox.ymax + outlet
        else:
            ymin = bbox.ymin - outlet
            ymax = bbox.ymax + inlet
        xmin = bbox.xmin - lateral
        xmax = bbox.xmax + lateral
        streamwise = "y"

    return Domain(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
                  zmin=0.0, zmax=factors.height * H, streamwise_axis=streamwise)
