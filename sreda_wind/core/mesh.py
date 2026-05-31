"""Adaptive mesh sizing.

Replaces the original fixed grid (hard clipped at 150x150x50) with a three-level
strategy whose density is driven by the obstacle height H and a target near-
facade cell size, bounded by an explicit cell budget:

  base mesh       ~ H/2          over the whole domain
  refinement box  base / 2^Lr    around the obstacles (+ padding)
  surface layer   base / 2^Ls    next to the facades

The budget is the only ceiling. Any compromise is reported in `warnings`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RefinementBox:
    xmin: float
    ymin: float
    zmin: float
    xmax: float
    ymax: float
    zmax: float


@dataclass
class MeshSpec:
    base_cell: float
    nx: int
    ny: int
    nz: int
    surface_level: int
    region_level: int
    refinement_box: RefinementBox
    estimated_cells: int
    warnings: list = field(default_factory=list)

    @property
    def facade_cell(self):
        """Effective cell size next to the facades after surface refinement."""
        return self.base_cell / (2 ** self.surface_level)


def _make_refinement_box(bbox, H, pad_factor=2.0, z_factor=1.5):
    pad = pad_factor * H
    return RefinementBox(
        xmin=bbox.xmin - pad, ymin=bbox.ymin - pad, zmin=0.0,
        xmax=bbox.xmax + pad, ymax=bbox.ymax + pad, zmax=z_factor * H,
    )


def _box_volume_fraction(box, domain):
    box_vol = (max(0.0, box.xmax - box.xmin)
               * max(0.0, box.ymax - box.ymin)
               * max(0.0, box.zmax - box.zmin))
    dom_vol = domain.width * domain.depth * domain.height
    if dom_vol <= 0.0:
        return 0.0
    return min(1.0, box_vol / dom_vol)


def compute_mesh_spec(domain, geometry_bbox, H, target_facade_cell=2.0,
                      cell_budget=3_000_000, min_base_cell=4.0):
    """Compute an adaptive MeshSpec that fits within cell_budget.

    domain: a core.domain.Domain. geometry_bbox: a core.domain.BBox of the
    obstacles. H: characteristic height. target_facade_cell: desired cell size
    next to the facades. cell_budget: hard ceiling on the estimated cell count.
    """
    warnings = []
    base_cell = max(H / 2.0, min_base_cell)
    target = target_facade_cell

    box = _make_refinement_box(geometry_bbox, H)
    frac = _box_volume_fraction(box, domain)

    nx = ny = nz = 0
    surface_level = region_level = 0
    estimated = 0

    while True:
        nx = max(20, int(domain.width / base_cell))
        ny = max(20, int(domain.depth / base_cell))
        nz = max(15, int(domain.height / base_cell))

        surface_level = max(2, math.ceil(math.log2(base_cell / target)))
        # If the box covers most of the domain, region refinement is not worth it.
        if frac > 0.5:
            region_level = 0
        else:
            region_level = max(1, surface_level - 1)

        base_cells = nx * ny * nz
        boxed = base_cells * frac
        unboxed = base_cells * (1.0 - frac)
        estimated = int(unboxed + boxed * (8 ** region_level))

        if estimated <= cell_budget:
            break

        # Too many cells: coarsen base and target together so surface_level holds.
        base_cell *= 1.25
        target *= 1.25
        if base_cell > H:
            warnings.append(
                "Cell budget too tight: base cell forced to {:.1f} m".format(base_cell))
            nx = max(20, int(domain.width / base_cell))
            ny = max(20, int(domain.depth / base_cell))
            nz = max(15, int(domain.height / base_cell))
            surface_level = max(2, math.ceil(math.log2(base_cell / target)))
            region_level = 0
            estimated = nx * ny * nz
            break

    if abs(target - target_facade_cell) > 1e-9:
        warnings.append(
            "Target facade cell relaxed from {:.1f} to {:.1f} m to fit budget".format(
                target_facade_cell, target))

    return MeshSpec(
        base_cell=base_cell, nx=nx, ny=ny, nz=nz,
        surface_level=surface_level, region_level=region_level,
        refinement_box=box, estimated_cells=estimated, warnings=warnings)
