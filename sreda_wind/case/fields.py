"""Initial/boundary field files in 0/ (U, p, k, epsilon|omega, nut).

Each builder returns the full text of one field file. The four lateral patches
are filled from the patch-type map; ground/top/buildings are fixed. The set of
turbulence fields depends on the model family (epsilon vs omega).
"""
from __future__ import annotations

from . import boundary
from ._foam import FOOTER, header
from .settings import turbulence_family

_LATERAL = ("xMin", "xMax", "yMin", "yMax")


def _field_file(cls, obj, dimensions, internal, boundary_text):
    """Assemble a volField file from its parts."""
    parts = []
    parts.append(header(cls, obj, location="0"))
    parts.append("")
    parts.append("dimensions      {};".format(dimensions))
    parts.append("internalField   {};".format(internal))
    parts.append("")
    parts.append("boundaryField")
    parts.append("{")
    parts.append(boundary_text)
    parts.append("}")
    return "\n".join(parts) + FOOTER


def _lateral_blocks(patch_types, builder):
    """Render the four lateral patch blocks in a stable order."""
    blocks = []
    i = 0
    while i < len(_LATERAL):
        patch = _LATERAL[i]
        blocks.append(builder(patch, patch_types[patch]))
        i += 1
    return "\n".join(blocks)


def velocity_field(patch_types, ctx):
    """0/U with the ABL coded inlet and inletOutlet outlets."""
    def builder(patch, bc_type):
        return boundary.u_patch(patch, bc_type, ctx)

    fixed = "\n".join((
        "    ground\n    {\n        type            noSlip;\n    }",
        "    top\n    {\n        type            slip;\n    }",
        "    buildings\n    {\n        type            noSlip;\n    }",
    ))
    boundary_text = _lateral_blocks(patch_types, builder) + "\n" + fixed
    internal = "uniform ({} {} 0)".format(ctx.ux, ctx.uy)
    return _field_file("volVectorField", "U", "[0 1 -1 0 0 0 0]", internal, boundary_text)


def pressure_field(patch_types, ctx):
    """0/p with zeroGradient inlet and fixedValue outlet."""
    def builder(patch, bc_type):
        return boundary.p_patch(patch, bc_type, ctx)

    fixed = "\n".join((
        "    ground\n    {\n        type            zeroGradient;\n    }",
        "    top\n    {\n        type            slip;\n    }",
        "    buildings\n    {\n        type            zeroGradient;\n    }",
    ))
    boundary_text = _lateral_blocks(patch_types, builder) + "\n" + fixed
    return _field_file("volScalarField", "p", "[0 2 -2 0 0 0 0]", "uniform 0", boundary_text)


def tke_field(patch_types, ctx):
    """0/k with fixedValue inlet and kqRWallFunction at walls."""
    def builder(patch, bc_type):
        return boundary.scalar_patch(patch, bc_type, ctx.k)

    wall = "    {{\n        type            kqRWallFunction;\n        value           uniform {};\n    }}".format(ctx.k)
    fixed = "\n".join((
        "    ground\n" + wall,
        "    top\n    {\n        type            zeroGradient;\n    }",
        "    buildings\n" + wall,
    ))
    boundary_text = _lateral_blocks(patch_types, builder) + "\n" + fixed
    internal = "uniform {}".format(ctx.k)
    return _field_file("volScalarField", "k", "[0 2 -2 0 0 0 0]", internal, boundary_text)


def epsilon_field(patch_types, ctx):
    """0/epsilon with fixedValue inlet and epsilonWallFunction at walls."""
    def builder(patch, bc_type):
        return boundary.scalar_patch(patch, bc_type, ctx.epsilon)

    wall = "    {{\n        type            epsilonWallFunction;\n        value           uniform {};\n    }}".format(ctx.epsilon)
    fixed = "\n".join((
        "    ground\n" + wall,
        "    top\n    {\n        type            zeroGradient;\n    }",
        "    buildings\n" + wall,
    ))
    boundary_text = _lateral_blocks(patch_types, builder) + "\n" + fixed
    internal = "uniform {}".format(ctx.epsilon)
    return _field_file("volScalarField", "epsilon", "[0 2 -3 0 0 0 0]", internal, boundary_text)


def omega_field(patch_types, ctx):
    """0/omega with fixedValue inlet and omegaWallFunction at walls."""
    def builder(patch, bc_type):
        return boundary.scalar_patch(patch, bc_type, ctx.omega)

    wall = "    {{\n        type            omegaWallFunction;\n        value           uniform {};\n    }}".format(ctx.omega)
    fixed = "\n".join((
        "    ground\n" + wall,
        "    top\n    {\n        type            zeroGradient;\n    }",
        "    buildings\n" + wall,
    ))
    boundary_text = _lateral_blocks(patch_types, builder) + "\n" + fixed
    internal = "uniform {}".format(ctx.omega)
    return _field_file("volScalarField", "omega", "[0 0 -1 0 0 0 0]", internal, boundary_text)


def nut_field(patch_types):
    """0/nut with calculated lateral patches and nutkWallFunction at walls."""
    def builder(patch, bc_type):
        return boundary.nut_patch(patch)

    wall = "    {\n        type            nutkWallFunction;\n        value           uniform 0;\n    }"
    fixed = "\n".join((
        "    ground\n" + wall,
        "    top\n    {\n        type            calculated;\n        value           uniform 0;\n    }",
        "    buildings\n" + wall,
    ))
    boundary_text = _lateral_blocks(patch_types, builder) + "\n" + fixed
    return _field_file("volScalarField", "nut", "[0 2 -1 0 0 0 0]", "uniform 0", boundary_text)


def all_fields(patch_types, ctx, turbulence_model):
    """Return a dict {filename: content} of all 0/ fields for the model family."""
    out = {}
    out["U"] = velocity_field(patch_types, ctx)
    out["p"] = pressure_field(patch_types, ctx)
    out["k"] = tke_field(patch_types, ctx)
    out["nut"] = nut_field(patch_types)
    if turbulence_family(turbulence_model) == "omega":
        out["omega"] = omega_field(patch_types, ctx)
    else:
        out["epsilon"] = epsilon_field(patch_types, ctx)
    return out
