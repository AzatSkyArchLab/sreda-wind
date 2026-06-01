"""Triangle mesh: the internal geometry representation.

A TriMesh is a flat list of triangles, each triangle being three (x, y, z)
points. This is STL-native (STL stores explicit per-facet vertices) and trivial
to merge. Indexed meshes from the frontend are expanded into this form later.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TriMesh:
    triangles: list = field(default_factory=list)  # list of (p0, p1, p2); p = (x, y, z)

    @property
    def triangle_count(self):
        return len(self.triangles)

    def bbox(self):
        """Return (xmin, ymin, zmin, xmax, ymax, zmax) over all vertices."""
        if not self.triangles:
            return None
        xs_min = ys_min = zs_min = float("inf")
        xs_max = ys_max = zs_max = float("-inf")
        for tri in self.triangles:
            for (x, y, z) in tri:
                if x < xs_min:
                    xs_min = x
                if y < ys_min:
                    ys_min = y
                if z < zs_min:
                    zs_min = z
                if x > xs_max:
                    xs_max = x
                if y > ys_max:
                    ys_max = y
                if z > zs_max:
                    zs_max = z
        return (xs_min, ys_min, zs_min, xs_max, ys_max, zs_max)


def merge(meshes):
    """Concatenate several TriMesh objects into one."""
    out = TriMesh()
    for m in meshes:
        out.triangles.extend(m.triangles)
    return out
