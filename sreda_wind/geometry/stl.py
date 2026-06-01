"""STL serialization for TriMesh: ASCII and binary writers, and a reader.

Per-facet normals are computed from the triangle winding (right-hand rule), so
they point outward as long as the mesh was built with consistent winding.
Binary STL is ~5-10x smaller than ASCII and is preferred for large scenes.
"""
from __future__ import annotations

import math
import struct

from .mesh import TriMesh


def _normal(p0, p1, p2):
    """Unit normal of a triangle from the right-hand rule."""
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def write_ascii(mesh, path, name="buildings"):
    """Write the mesh as an ASCII STL file."""
    lines = ["solid " + name]
    for (p0, p1, p2) in mesh.triangles:
        nx, ny, nz = _normal(p0, p1, p2)
        lines.append("  facet normal {} {} {}".format(nx, ny, nz))
        lines.append("    outer loop")
        lines.append("      vertex {} {} {}".format(p0[0], p0[1], p0[2]))
        lines.append("      vertex {} {} {}".format(p1[0], p1[1], p1[2]))
        lines.append("      vertex {} {} {}".format(p2[0], p2[1], p2[2]))
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid " + name)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def write_binary(mesh, path):
    """Write the mesh as a binary STL file."""
    with open(path, "wb") as f:
        header = b"sreda-wind binary STL"
        f.write(header + b"\x00" * (80 - len(header)))
        f.write(struct.pack("<I", len(mesh.triangles)))
        for (p0, p1, p2) in mesh.triangles:
            nx, ny, nz = _normal(p0, p1, p2)
            f.write(struct.pack("<3f", nx, ny, nz))
            f.write(struct.pack("<3f", p0[0], p0[1], p0[2]))
            f.write(struct.pack("<3f", p1[0], p1[1], p1[2]))
            f.write(struct.pack("<3f", p2[0], p2[1], p2[2]))
            f.write(struct.pack("<H", 0))  # attribute byte count


def _looks_binary(path):
    with open(path, "rb") as f:
        head = f.read(5)
    return head[:5].lower() != b"solid"


def read_stl(path):
    """Read an STL file (binary or ASCII) into a TriMesh."""
    if _looks_binary(path):
        return _read_binary(path)
    return _read_ascii(path)


def _read_binary(path):
    mesh = TriMesh()
    with open(path, "rb") as f:
        f.read(80)
        (count,) = struct.unpack("<I", f.read(4))
        for _ in range(count):
            f.read(12)  # normal, recomputed on demand
            p0 = struct.unpack("<3f", f.read(12))
            p1 = struct.unpack("<3f", f.read(12))
            p2 = struct.unpack("<3f", f.read(12))
            f.read(2)
            mesh.triangles.append((p0, p1, p2))
    return mesh


def _read_ascii(path):
    mesh = TriMesh()
    verts = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
                if len(verts) == 3:
                    mesh.triangles.append((verts[0], verts[1], verts[2]))
                    verts = []
    return mesh
