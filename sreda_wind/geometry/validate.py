"""Polygon validation and cleanup for building footprints.

Lightweight, dependency-free: shoelace area, CCW normalization, closure. Heavy
self-intersection repair (Shapely make_valid) can be layered on later for messy
city data; it is not needed for clean benchmark geometry.
"""
from __future__ import annotations

from .triangulate import ensure_ccw


def polygon_area(coords):
    """Absolute area of a 2D polygon via the shoelace formula."""
    n = len(coords)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]
    return abs(area) / 2.0


def validate_polygon(coords, height, min_area=1.0):
    """Validate and clean a footprint. Returns a dict or None if invalid.

    Enforces at least 3 vertices, a minimum area, CCW winding and explicit
    closure (first vertex repeated at the end).
    """
    if len(coords) < 3:
        return None
    if polygon_area(coords) < min_area:
        return None

    cleaned = ensure_ccw([(c[0], c[1]) for c in coords])
    if cleaned[0] != cleaned[-1]:
        cleaned = cleaned + [cleaned[0]]
    return {"coords": cleaned, "height": height}
