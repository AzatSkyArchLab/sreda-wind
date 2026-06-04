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


def classify_patches(flow_x, flow_y, symmetry_sides=False):
    """Map each lateral patch to "inlet", "outlet" or "symmetry".

    Convention: flow_x > 0 means the flow travels toward +x, so it enters the
    domain at xMin. Cross-stream patches (|component| below threshold) become
    outlets so inletOutlet handles recirculation gracefully; with
    symmetry_sides they become symmetry planes instead (AIJ confinement).
    """
    cross = "symmetry" if symmetry_sides else "outlet"
    types = {}

    if flow_x > _FLOW_THRESHOLD:
        types["xMin"] = "inlet"
        types["xMax"] = "outlet"
    elif flow_x < -_FLOW_THRESHOLD:
        types["xMin"] = "outlet"
        types["xMax"] = "inlet"
    else:
        types["xMin"] = cross
        types["xMax"] = cross

    if flow_y > _FLOW_THRESHOLD:
        types["yMin"] = "inlet"
        types["yMax"] = "outlet"
    elif flow_y < -_FLOW_THRESHOLD:
        types["yMin"] = "outlet"
        types["yMax"] = "inlet"
    else:
        types["yMin"] = cross
        types["yMax"] = cross

    return types


@dataclass(frozen=True)
class InletContext:
    """Everything the inlet/outlet BC snippets need.

    When ``profile`` is given (a list of (z, u, k, epsilon) tuples), the inlet
    uses tabulated codedFixedValue profiles interpolated by height; otherwise it
    uses the Richards & Hoxey log-law coded inlet with uniform k/epsilon.
    """
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
    profile: tuple = None   # optional ((z, u, k, eps), ...) measured inflow
    inlet_mode: str = "coded"   # "coded" (Richards-Hoxey/tabulated) | "equilibrium"


def symmetry_block(patch):
    """A symmetry patch block (identical for every field)."""
    return "    {}\n    {{\n        type            symmetry;\n    }}".format(patch)


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


def abl_conditions(ctx):
    """Text of 0/include/ABLConditions for the equilibrium atmospheric inlet.

    The atmBoundaryLayerInlet* boundary conditions (OpenFOAM 13
    libatmosphericModels) read these keywords: a reference speed at a reference
    height, the vertical and flow directions, the roughness length and the ground
    datum. This reproduces the proven Case A equilibrium inlet, parameterised by
    the run's wind and roughness.
    """
    lines = []
    lines.append("Uref            {};".format(ctx.speed))
    lines.append("Zref            {};".format(ctx.z_ref))
    lines.append("zDir            (0 0 1);")
    lines.append("flowDir         ({:.6f} {:.6f} 0);".format(ctx.flow_x, ctx.flow_y))
    lines.append("z0              uniform {};".format(ctx.z0))
    lines.append("zGround         uniform 0;")
    return "\n".join(lines) + "\n"


def _atm_inlet(patch, kind):
    """An atmBoundaryLayerInlet{Velocity|K|Epsilon} block pulling ABLConditions."""
    lines = []
    lines.append("    {}".format(patch))
    lines.append("    {")
    lines.append("        type            atmBoundaryLayerInlet{};".format(kind))
    lines.append('        #include        "include/ABLConditions"')
    lines.append("    }")
    return "\n".join(lines)


def _carray(values):
    """Format a Python sequence as a C++ scalar array initialiser."""
    parts = []
    i = 0
    while i < len(values):
        parts.append("{:.8g}".format(float(values[i])))
        i += 1
    return "{" + ", ".join(parts) + "}"


def _profile_columns(profile):
    """Split the profile tuples into parallel z / u / k / eps lists."""
    zs = []
    us = []
    ks = []
    es = []
    i = 0
    while i < len(profile):
        z, u, k, e = profile[i]
        zs.append(z)
        us.append(u)
        ks.append(k)
        es.append(e)
        i += 1
    return zs, us, ks, es


def _interp_body(zs, vs):
    """C++ lines computing `val` = piecewise-linear interp of vs(zs) at z."""
    n = len(zs)
    lines = []
    lines.append("            const label N = {};".format(n))
    lines.append("            scalar zt[{}] = {};".format(n, _carray(zs)))
    lines.append("            scalar vt[{}] = {};".format(n, _carray(vs)))
    lines.append("            forAll(Cf, faceI)")
    lines.append("            {")
    lines.append("                scalar z = Cf[faceI].z();")
    lines.append("                scalar val;")
    lines.append("                if (z <= zt[0]) { val = vt[0]; }")
    lines.append("                else if (z >= zt[N-1]) { val = vt[N-1]; }")
    lines.append("                else")
    lines.append("                {")
    lines.append("                    val = vt[N-1];")
    lines.append("                    for (label i = 0; i < N - 1; i++)")
    lines.append("                    {")
    lines.append("                        if (z >= zt[i] && z <= zt[i+1])")
    lines.append("                        {")
    lines.append("                            scalar t = (z - zt[i]) / (zt[i+1] - zt[i]);")
    lines.append("                            val = vt[i] + t * (vt[i+1] - vt[i]);")
    lines.append("                            break;")
    lines.append("                        }")
    lines.append("                    }")
    lines.append("                }")
    return "\n".join(lines)


def _tabulated_inlet_vector(patch, ctx):
    """codedFixedValue imposing a tabulated U(z) magnitude along the flow."""
    zs, us, ks, es = _profile_columns(ctx.profile)
    lines = []
    lines.append("    {}".format(patch))
    lines.append("    {")
    lines.append("        type            codedFixedValue;")
    lines.append("        value           uniform ({} {} 0);".format(ctx.ux, ctx.uy))
    lines.append("        name            tabulatedInletVelocity;")
    lines.append("        code")
    lines.append("        #{")
    lines.append("            const vectorField& Cf = patch().Cf();")
    lines.append("            vectorField& field = *this;")
    lines.append("            scalar flowX = {:.6f};".format(ctx.flow_x))
    lines.append("            scalar flowY = {:.6f};".format(ctx.flow_y))
    lines.append(_interp_body(zs, us))
    lines.append("                field[faceI] = vector(flowX * val, flowY * val, 0);")
    lines.append("            }")
    lines.append("        #};")
    lines.append("    }")
    return "\n".join(lines)


def _tabulated_inlet_scalar(patch, ctx, name, which):
    """codedFixedValue imposing a tabulated scalar profile (k or epsilon)."""
    zs, us, ks, es = _profile_columns(ctx.profile)
    vs = ks if which == "k" else es
    lines = []
    lines.append("    {}".format(patch))
    lines.append("    {")
    lines.append("        type            codedFixedValue;")
    lines.append("        value           uniform {};".format(vs[0]))
    lines.append("        name            {};".format(name))
    lines.append("        code")
    lines.append("        #{")
    lines.append("            const vectorField& Cf = patch().Cf();")
    lines.append("            scalarField& field = *this;")
    lines.append(_interp_body(zs, vs))
    lines.append("                field[faceI] = val;")
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
    if bc_type == "symmetry":
        return symmetry_block(patch)
    if bc_type == "inlet":
        if ctx.inlet_mode == "equilibrium":
            return _atm_inlet(patch, "Velocity")
        if ctx.profile is not None:
            return _tabulated_inlet_vector(patch, ctx)
        return _abl_coded_inlet(patch, ctx)
    value = "uniform ({} {} 0)".format(ctx.ux, ctx.uy)
    return _simple_block(patch, (
        ("type", "inletOutlet"),
        ("inletValue", value),
        ("value", value),
    ))


def p_patch(patch, bc_type, ctx):
    """Pressure BC for a lateral patch."""
    if bc_type == "symmetry":
        return symmetry_block(patch)
    if bc_type == "inlet":
        return _simple_block(patch, (("type", "zeroGradient"),))
    return _simple_block(patch, (
        ("type", "fixedValue"),
        ("value", "uniform 0"),
    ))


def scalar_patch(patch, bc_type, value, ctx=None, which=None):
    """fixedValue/tabulated at inlet, inletOutlet elsewhere; symmetry passthrough.

    For k/epsilon/omega. If a tabulated profile is present in ctx and `which`
    selects k or epsilon, the inlet uses the measured profile.
    """
    if bc_type == "symmetry":
        return symmetry_block(patch)
    if bc_type == "inlet":
        if ctx is not None and ctx.inlet_mode == "equilibrium" and which in ("k", "epsilon"):
            kind = "K" if which == "k" else "Epsilon"
            return _atm_inlet(patch, kind)
        if ctx is not None and ctx.profile is not None and which in ("k", "epsilon"):
            name = "tabulatedInlet_{}".format(which)
            return _tabulated_inlet_scalar(patch, ctx, name, "k" if which == "k" else "eps")
        return _simple_block(patch, (
            ("type", "fixedValue"),
            ("value", "uniform {}".format(value)),
        ))
    return _simple_block(patch, (
        ("type", "inletOutlet"),
        ("inletValue", "uniform {}".format(value)),
        ("value", "uniform {}".format(value)),
    ))


def nut_patch(patch, bc_type="outlet"):
    """nut BC for a lateral patch (symmetry passthrough, else calculated)."""
    if bc_type == "symmetry":
        return symmetry_block(patch)
    return _simple_block(patch, (
        ("type", "calculated"),
        ("value", "uniform 0"),
    ))


def ground_nut_block(z0):
    """nut wall block for the ground: rough (atm) if z0 > 0, else smooth."""
    if z0 and z0 > 0.0:
        # Foundation OF13 name (z0-based); needs libatmosphericModels.so loaded.
        return ("    ground\n    {{\n"
                "        type            nutkAtmRoughWallFunction;\n"
                "        z0              uniform {};\n"
                "        value           uniform 0;\n    }}".format(z0))
    return ("    ground\n    {\n"
            "        type            nutkWallFunction;\n"
            "        value           uniform 0;\n    }")
