"""blockMeshDict and snappyHexMeshDict builders.

The background block mesh comes straight from the (adaptive) Domain and
MeshSpec computed in core/. snappyHexMesh then carves the buildings out of it,
refining the surfaces and an optional refinement region. There is no hard
cell-count clip: the only ceiling is MeshSpec's budget (maxGlobalCells).
"""
from __future__ import annotations

from ._foam import FOOTER, header

# Vertex ordering for the axis-aligned background block (see boundary faces).
#   0:(xmin,ymin,0) 1:(xmax,ymin,0) 2:(xmax,ymax,0) 3:(xmin,ymax,0)
#   4:(xmin,ymin,zmax) ... 7:(xmin,ymax,zmax)
_FACES = (
    ("xMin", "patch", "(0 4 7 3)"),
    ("xMax", "patch", "(1 2 6 5)"),
    ("yMin", "patch", "(0 1 5 4)"),
    ("yMax", "patch", "(3 7 6 2)"),
    ("ground", "wall", "(0 1 2 3)"),
    ("top", "patch", "(4 5 6 7)"),
)


def block_mesh_dict(domain, mesh_spec, vertical_grading=2.0):
    """blockMeshDict text for the background hex mesh."""
    x0, x1 = domain.xmin, domain.xmax
    y0, y1 = domain.ymin, domain.ymax
    z0, z1 = domain.zmin, domain.zmax

    parts = []
    parts.append(header("dictionary", "blockMeshDict", location="system"))
    parts.append("")
    parts.append("convertToMeters 1;")
    parts.append("")
    parts.append("vertices")
    parts.append("(")
    parts.append("    ({} {} {})".format(x0, y0, z0))
    parts.append("    ({} {} {})".format(x1, y0, z0))
    parts.append("    ({} {} {})".format(x1, y1, z0))
    parts.append("    ({} {} {})".format(x0, y1, z0))
    parts.append("    ({} {} {})".format(x0, y0, z1))
    parts.append("    ({} {} {})".format(x1, y0, z1))
    parts.append("    ({} {} {})".format(x1, y1, z1))
    parts.append("    ({} {} {})".format(x0, y1, z1))
    parts.append(");")
    parts.append("")
    parts.append("blocks")
    parts.append("(")
    parts.append("    hex (0 1 2 3 4 5 6 7) ({} {} {}) simpleGrading (1 1 {})".format(
        mesh_spec.nx, mesh_spec.ny, mesh_spec.nz, vertical_grading))
    parts.append(");")
    parts.append("")
    parts.append("boundary")
    parts.append("(")
    i = 0
    while i < len(_FACES):
        name, patch_type, face = _FACES[i]
        parts.append("    {}".format(name))
        parts.append("    {")
        parts.append("        type {};".format(patch_type))
        parts.append("        faces (({}));".format(face.strip("()")))
        parts.append("    }")
        i += 1
    parts.append(");")
    return "\n".join(parts) + FOOTER


def snappy_hex_mesh_dict(mesh_spec, location_in_mesh, cell_budget,
                         stl_file="buildings.stl"):
    """snappyHexMeshDict text. Buildings are snapped; trees are NOT here.

    location_in_mesh: (x, y, z) point known to be in the fluid region.
    """
    box = mesh_spec.refinement_box
    lx, ly, lz = location_in_mesh
    s = mesh_spec.surface_level
    r = mesh_spec.region_level

    parts = []
    parts.append(header("dictionary", "snappyHexMeshDict", location="system"))
    parts.append("")
    parts.append("castellatedMesh true;")
    parts.append("snap            true;")
    parts.append("addLayers       false;")
    parts.append("")
    parts.append("geometry")
    parts.append("{")
    parts.append("    buildings")
    parts.append("    {")
    parts.append("        type triSurface;")
    parts.append('        file "{}";'.format(stl_file))
    parts.append("    }")
    parts.append("    refinementBox")
    parts.append("    {")
    parts.append("        type box;")
    parts.append("        min ({} {} {});".format(box.xmin, box.ymin, box.zmin))
    parts.append("        max ({} {} {});".format(box.xmax, box.ymax, box.zmax))
    parts.append("    }")
    parts.append("}")
    parts.append("")
    parts.append("castellatedMeshControls")
    parts.append("{")
    parts.append("    maxLocalCells       {};".format(int(cell_budget / 5)))
    parts.append("    maxGlobalCells      {};".format(int(cell_budget)))
    parts.append("    minRefinementCells  10;")
    parts.append("    nCellsBetweenLevels 2;")
    parts.append("    resolveFeatureAngle 30;")
    parts.append("    features ();")
    parts.append("    refinementSurfaces")
    parts.append("    {")
    parts.append("        buildings")
    parts.append("        {")
    parts.append("            level ({} {});".format(s, s))
    parts.append("            patchInfo { type wall; }")
    parts.append("        }")
    parts.append("    }")
    parts.append("    refinementRegions")
    parts.append("    {")
    if r > 0:
        parts.append("        refinementBox")
        parts.append("        {")
        parts.append("            mode    inside;")
        parts.append("            level   {};".format(r))
        parts.append("        }")
    parts.append("    }")
    parts.append("    insidePoint ({} {} {});".format(lx, ly, lz))
    parts.append("    allowFreeStandingZoneFaces true;")
    parts.append("}")
    parts.append("")
    parts.append("snapControls")
    parts.append("{")
    parts.append("    nSmoothPatch    3;")
    parts.append("    tolerance       2.0;")
    parts.append("    nSolveIter      50;")
    parts.append("    nRelaxIter      5;")
    parts.append("}")
    parts.append("")
    parts.append("addLayersControls")
    parts.append("{")
    parts.append("    layers {}")
    parts.append("}")
    parts.append("")
    parts.append("meshQualityControls")
    parts.append("{")
    parts.append("    maxNonOrtho 65;")
    parts.append("    maxBoundarySkewness 20;")
    parts.append("    maxInternalSkewness 4;")
    parts.append("    maxConcave 80;")
    parts.append("    minFlatness 0.5;")
    parts.append("    minVol 1e-13;")
    parts.append("    minArea -1;")
    parts.append("    minTwist 0.01;")
    parts.append("    minDeterminant 0.001;")
    parts.append("    minFaceWeight 0.02;")
    parts.append("    minVolRatio 0.01;")
    parts.append("    minTriangleTwist -1;")
    parts.append("    minTetQuality 1e-30;")
    parts.append("    nSmoothScale 4;")
    parts.append("    errorReduction 0.75;")
    parts.append("}")
    parts.append("")
    parts.append("mergeTolerance 1e-6;")
    return "\n".join(parts) + FOOTER
