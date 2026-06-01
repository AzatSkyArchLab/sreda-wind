"""Polygon triangulation and footprint extrusion (ported from the v4.8 monolith).

CCW normalization for correct outward normals, ear clipping for concave
polygons (L/U shapes), fast fan triangulation for convex ones.
"""
from __future__ import annotations

import math

from .mesh import TriMesh


def is_ccw(coords):
    """True if the 2D polygon is counter-clockwise (positive shoelace area)."""
    n = len(coords)
    if n < 3:
        return True
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]
    return area > 0


def ensure_ccw(coords):
    """Return coords as CCW (reversed if needed) for outward STL normals."""
    if not is_ccw(coords):
        return list(reversed(coords))
    return list(coords)


def is_convex_polygon(coords):
    """True if the polygon is convex (allows fast fan triangulation)."""
    n = len(coords)
    if n < 3:
        return True
    sign = None
    for i in range(n):
        p0 = coords[i]
        p1 = coords[(i + 1) % n]
        p2 = coords[(i + 2) % n]
        cross = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
        if cross != 0:
            if sign is None:
                sign = cross > 0
            elif (cross > 0) != sign:
                return False
    return True


def _strip_closing_duplicate(vertices):
    if len(vertices) > 3:
        dx = vertices[0][0] - vertices[-1][0]
        dy = vertices[0][1] - vertices[-1][1]
        if math.sqrt(dx * dx + dy * dy) < 0.001:
            return vertices[:-1]
    return vertices


def triangulate_ear_clipping(coords):
    """Triangulate a 2D polygon (convex or concave) into a list of triangles.

    Each triangle is a tuple of three 2D points. Works for L/U shapes.
    """
    if len(coords) < 3:
        return []

    vertices = _strip_closing_duplicate(list(ensure_ccw(coords)))
    if len(vertices) < 3:
        return []

    triangles = []
    indices = list(range(len(vertices)))

    def _point_in_triangle(px, py, a, b, c):
        def cross(ax, ay, bx, by, cx, cy):
            return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy)
        d1 = cross(px, py, a[0], a[1], b[0], b[1])
        d2 = cross(px, py, b[0], b[1], c[0], c[1])
        d3 = cross(px, py, c[0], c[1], a[0], a[1])
        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)

    def is_ear(i):
        n = len(indices)
        if n < 3:
            return False
        p0 = vertices[indices[(i - 1) % n]]
        p1 = vertices[indices[i]]
        p2 = vertices[indices[(i + 1) % n]]
        # Convex corner for CCW polygon?
        cross = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
        if cross <= 0:
            return False
        for j in range(n):
            if j in ((i - 1) % n, i, (i + 1) % n):
                continue
            px, py = vertices[indices[j]]
            if _point_in_triangle(px, py, p0, p1, p2):
                return False
        return True

    max_iter = len(vertices) * 3
    iteration = 0
    while len(indices) > 3 and iteration < max_iter:
        ear_found = False
        n = len(indices)
        for i in range(n):
            if is_ear(i):
                p0 = vertices[indices[(i - 1) % n]]
                p1 = vertices[indices[i]]
                p2 = vertices[indices[(i + 1) % n]]
                triangles.append((p0, p1, p2))
                indices.pop(i)
                ear_found = True
                break
        if not ear_found:
            break
        iteration += 1

    if len(indices) == 3:
        triangles.append((vertices[indices[0]], vertices[indices[1]], vertices[indices[2]]))
    return triangles


def _centroid(coords):
    sx = 0.0
    sy = 0.0
    for (x, y) in coords:
        sx += x
        sy += y
    n = len(coords)
    return (sx / n, sy / n)


def extrude_footprint(coords, height):
    """Extrude a 2D footprint to a watertight TriMesh: side walls + roof + floor.

    coords: list of (x, y); height: extrusion height [m]. Returns a TriMesh with
    outward-facing winding (walls outward, roof up, floor down).
    """
    mesh = TriMesh()
    if len(coords) < 3:
        return mesh

    poly = list(coords)
    if len(poly) > 1 and poly[0] == poly[-1]:
        poly = poly[:-1]
    if len(poly) < 3:
        return mesh
    poly = ensure_ccw(poly)
    h = height

    # Side walls: two triangles per edge, wound for outward normals.
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        x0, y0 = poly[i]
        x1, y1 = poly[j]
        dx, dy = x1 - x0, y1 - y0
        if math.sqrt(dx * dx + dy * dy) < 0.001:
            continue
        mesh.triangles.append(((x0, y0, 0.0), (x1, y1, 0.0), (x1, y1, h)))
        mesh.triangles.append(((x0, y0, 0.0), (x1, y1, h), (x0, y0, h)))

    # Roof and floor.
    if is_convex_polygon(poly):
        cx, cy = _centroid(poly)
        for i in range(n):
            j = (i + 1) % n
            x0, y0 = poly[i]
            x1, y1 = poly[j]
            mesh.triangles.append(((cx, cy, h), (x0, y0, h), (x1, y1, h)))      # roof up
            mesh.triangles.append(((cx, cy, 0.0), (x1, y1, 0.0), (x0, y0, 0.0)))  # floor down
    else:
        flat = triangulate_ear_clipping(poly)
        if not flat:
            cx, cy = _centroid(poly)
            flat = []
            for i in range(n):
                j = (i + 1) % n
                flat.append(((cx, cy), poly[i], poly[j]))
        for (p0, p1, p2) in flat:
            mesh.triangles.append(((p0[0], p0[1], h), (p1[0], p1[1], h), (p2[0], p2[1], h)))
            mesh.triangles.append(((p0[0], p0[1], 0.0), (p2[0], p2[1], 0.0), (p1[0], p1[1], 0.0)))
    return mesh
