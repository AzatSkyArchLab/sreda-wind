"""Generic COST 732 / AIJ domain sizing -- PARKED, NOT in the build path.

NOT used in the AIJ validation path; parked for a possible future general city
engine. The working case-build path (runner -> generate_case) takes the domain
explicitly from the AIJ case spec instead, so a generic formula can never
silently substitute the validated wind-tunnel geometry. This module is kept (it
is unit-tested and may seed a future product city engine) but nothing in the
build path imports or calls it.

The blockMesh box is axis-aligned. The streamwise axis (most aligned with the
flow) gets the inlet padding upstream and the outlet padding downstream; the
cross-stream axis gets symmetric lateral padding; the top is the height
padding. All paddings are multiples of the obstacle height H.
"""
from __future__ import annotations

from dataclasses import dataclass

from .box import BBox, Domain
from .wind import flow_vector


@dataclass(frozen=True)
class DomainFactors:
    """COST 732 domain extent factors, in multiples of H."""
    inlet: float = 5.0
    outlet: float = 8.0
    lateral: float = 2.5
    height: float = 5.0


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
