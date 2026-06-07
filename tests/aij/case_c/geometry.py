"""AIJ Case C geometry: 8 city-block cubes in a 3x3 ring, centre by config.

Cube D = 0.2 m, H = D = 0.2 m. 3x3 grid, pitch 0.4 m, so cube centres at
x,y in {-0.4, 0, +0.4}. The 8 SURROUNDING cubes (always present, all height H)
are the four corners and the four edge-midpoints; the centre (0,0) varies by
config: "0H" empty, "1H" a cube of height H, "2H" a cube of height 2H. Layout
confirmed from the measurement grid (SPEC.md §2). Wind along +x.
"""
from __future__ import annotations

from sreda_wind.geometry import extrude_footprint, merge, write_binary

D = 0.2                  # cube side / length scale
H = D                    # cube height (H = D)
PITCH = 0.4              # grid pitch (street gap = PITCH - D = 0.2)

# The 8 surrounding grid positions (all of the 3x3 except the centre).
_SURROUNDING = (
    (-0.4, -0.4), (0.0, -0.4), (0.4, -0.4),
    (-0.4, 0.0), (0.4, 0.0),
    (-0.4, 0.4), (0.0, 0.4), (0.4, 0.4),
)


def _square(cx, cy, side=D):
    """CCW square footprint of `side`, centred on (cx, cy)."""
    h = side / 2.0
    return [
        (cx - h, cy - h),
        (cx + h, cy - h),
        (cx + h, cy + h),
        (cx - h, cy + h),
    ]


def cube_specs(config="1H"):
    """Return [(footprint, height), ...] for the given config (0H/1H/2H)."""
    out = []
    i = 0
    while i < len(_SURROUNDING):
        cx, cy = _SURROUNDING[i]
        out.append((_square(cx, cy), H))
        i += 1
    if config == "1H":
        out.append((_square(0.0, 0.0), H))
    elif config == "2H":
        out.append((_square(0.0, 0.0), 2.0 * H))
    elif config != "0H":
        raise ValueError("config must be 0H, 1H or 2H; got {!r}".format(config))
    return out


def n_cubes(config="1H"):
    """Number of solid cubes in the config (8 ring, +1 if a centre block)."""
    return 8 + (0 if config == "0H" else 1)


def build_mesh(config="1H"):
    """Merge the cubes into one TriMesh for snappyHexMesh."""
    specs = cube_specs(config)
    meshes = []
    i = 0
    while i < len(specs):
        fp, h = specs[i]
        meshes.append(extrude_footprint(fp, height=h))
        i += 1
    return merge(meshes)


def write_stl(path, config="1H"):
    """Write the Case C group as a binary STL and return its TriMesh."""
    mesh = build_mesh(config)
    write_binary(mesh, path)
    return mesh
