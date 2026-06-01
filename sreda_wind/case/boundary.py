"""Boundary-condition logic: patch typing by flow direction, BC snippets.

The four lateral patches (xMin, xMax, yMin, yMax) are classified as inlet or
outlet from the horizontal flow vector. The streamwise upwind patch is the
inlet; everything else is treated as an outlet (inletOutlet), which also covers
the cross-stream patches for diagonal winds. The top is slip, the ground and
building walls use wall functions.

The velocity inlet uses a Richards & Hoxey logarithmic ABL profile imposed via
codedFixedValue, exactly as in the proven monolith.
"""
from __future__ import annotations

from dataclasses import dataclass

# Threshold on the unit flow component below which a patch is not a clear
# streamwise inlet/outlet. Such (cross-stream) patches are treated as outlets.
_FLOW_THRESHOLD = 0.3


def classify_patches(flow_x, flow_y):
    """Map each lateral patch to "inlet" or "outlet" from the flow vector.

    Convention: flow_x > 0 means the flow travels toward +x, so it enters the
    domain at xMin. Cross-stream patches (|component| below threshold) become
    outlets so inletOutlet handles recirculation gracefully.
    """
    types = {}

    if flow_x > _FLOW_THRESHOLD:
        types["xMin"] = "inlet"
        types["xMax"] = "outlet"
    elif flow_x < -_FLOW_THRESHOLD:
        types["xMin"] = "outlet"
        types["xMax"] = "inlet"
    else:
        types["xMin"] = "outlet"
        types["xMax"] = "outlet"

    if flow_y > _FLOW_THRESHOLD:
        types["yMin"] = "inlet"
        types["yMax"] = "outlet"
    elif flow_y < -_FLOW_THRESHOLD:
        types["yMin"] = "outlet"
        types["yMax"] = "inlet"
    else:
        types["yMin"] = "outlet"
        types["yMax"] = "outlet"

    return types


@dataclass(frozen=True)
class InletContext:
    """Everything the inlet/outlet BC snippets need."""
    ux: float          # reference velocity x-component [m/s]
    uy: float          # reference velocity y-component [m/s]
    flow_x: float      # unit flow direction x
    flow_y: float      # unit flow direction y
    speed: float       # reference wind speed at z_ref [m/s]
    z_ref: float       # reference height [m]
    z0: float          # roughness length [m]
    k: float           # turbulent kinetic energy [m2/s2]
    epsilon: float     # dissipation rate [m2/s3]
    omega: float       # specific dissipation rate [1/s]


def _abl_coded_inlet(patch, ctx):
    """codedFixedValue block imposing the log-law ABL velocity profile."""
    lines = []
    lines.append("    {}".format(patch))
    lines.append("    {")
    lines.append("        type            codedFixedValue;")
    lines.append("        value           uniform ({} {} 0);".format(ctx.ux, ctx.uy))
    lines.append("        name            ABLInletVelocity;")
    lines.append("        code")
    lines.append("        #{")
    lines.append("            const vectorField& Cf = patch().Cf();")
    lines.append("            vectorField& field = *this;")
    lines.append("")
    lines.append("            // Richards & Hoxey (1993) neutral ABL")
    lines.append("            scalar Uref = {};".format(ctx.speed))
    lines.append("            scalar Zref = {};".format(ctx.z_ref))
    lines.append("            scalar z0   = {};".format(ctx.z0))
    lines.append("            scalar kappa = 0.41;")
    lines.append("            scalar flowX = {:.6f};".format(ctx.flow_x))
    lines.append("            scalar flowY = {:.6f};".format(ctx.flow_y))
    lines.append("")
    lines.append("            scalar ustar = Uref * kappa / Foam::log((Zref + z0) / z0);")
    lines.append("")
    lines.append("            forAll(Cf, faceI)")
    lines.append("            {")
    lines.append("                scalar z = max(Cf[faceI].z(), 0.01);")
    lines.append("                scalar Umag = (ustar / kappa) * Foam::log((z + z0) / z0);")
    lines.append("                field[faceI] = vector(flowX * Umag, flowY * Umag, 0);")
    lines.append("            }")
    lines.append("        #};")
    lines.append("    }")
    return "\n".join(lines)


def _simple_block(patch, entries):
    """Render a patch block from a list of (key, value) entry strings."""
    lines = []
    lines.append("    {}".format(patch))
    lines.append("    {")
    i = 0
    while i < len(entries):
        key, value = entries[i]
        lines.append("        {:<15} {};".format(key, value))
        i += 1
    lines.append("    }")
    return "\n".join(lines)


def u_patch(patch, bc_type, ctx):
    """Velocity BC for a lateral patch."""
    if bc_type == "inlet":
        return _abl_coded_inlet(patch, ctx)
    value = "uniform ({} {} 0)".format(ctx.ux, ctx.uy)
    return _simple_block(patch, (
        ("type", "inletOutlet"),
        ("inletValue", value),
        ("value", value),
    ))


def p_patch(patch, bc_type, ctx):
    """Pressure BC for a lateral patch."""
    if bc_type == "inlet":
        return _simple_block(patch, (("type", "zeroGradient"),))
    return _simple_block(patch, (
        ("type", "fixedValue"),
        ("value", "uniform 0"),
    ))


def scalar_patch(patch, bc_type, value):
    """fixedValue at inlet, inletOutlet elsewhere, for k/epsilon/omega."""
    if bc_type == "inlet":
        return _simple_block(patch, (
            ("type", "fixedValue"),
            ("value", "uniform {}".format(value)),
        ))
    return _simple_block(patch, (
        ("type", "inletOutlet"),
        ("inletValue", "uniform {}".format(value)),
        ("value", "uniform {}".format(value)),
    ))


def nut_patch(patch):
    """nut BC for a lateral patch (always calculated)."""
    return _simple_block(patch, (
        ("type", "calculated"),
        ("value", "uniform 0"),
    ))
