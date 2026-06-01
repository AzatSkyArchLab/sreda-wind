"""system/ dictionaries: controlDict, fvSchemes, fvSolution, decomposeParDict.

Steady-state SIMPLE for the modular OpenFOAM 13 incompressibleFluid solver.
The control dict declares the solver inline (``solver incompressibleFluid;``);
the foamRun invocation lives in the solver/ layer.
"""
from __future__ import annotations

import os

from ._foam import FOOTER, header
from .settings import turbulence_family


def control_dict(settings):
    """system/controlDict for a steady SIMPLE run."""
    parts = []
    parts.append(header("dictionary", "controlDict", location="system"))
    parts.append("")
    parts.append("solver          incompressibleFluid;")
    parts.append("startFrom       startTime;")
    parts.append("startTime       0;")
    parts.append("stopAt          endTime;")
    parts.append("endTime         {};".format(settings.iterations))
    parts.append("deltaT          1;")
    parts.append("writeControl    timeStep;")
    parts.append("writeInterval   {};".format(settings.resolved_write_interval()))
    parts.append("purgeWrite      1;")
    parts.append("writeFormat     ascii;")
    parts.append("writePrecision  8;")
    parts.append("writeCompression off;")
    parts.append("timeFormat      general;")
    parts.append("timePrecision   6;")
    parts.append("runTimeModifiable true;")
    return "\n".join(parts) + FOOTER


def fv_schemes(turbulence_model):
    """system/fvSchemes; turbulence divergence terms depend on the model."""
    second = turbulence_family(turbulence_model)  # "epsilon" or "omega"

    parts = []
    parts.append(header("dictionary", "fvSchemes", location="system"))
    parts.append("")
    parts.append("ddtSchemes")
    parts.append("{")
    parts.append("    default         steadyState;")
    parts.append("}")
    parts.append("")
    parts.append("gradSchemes")
    parts.append("{")
    parts.append("    default         Gauss linear;")
    parts.append("    limited         cellLimited Gauss linear 1;")
    parts.append("    grad(U)         $limited;")
    parts.append("    grad(k)         $limited;")
    parts.append("    grad({})        $limited;".format(second))
    parts.append("}")
    parts.append("")
    parts.append("divSchemes")
    parts.append("{")
    parts.append("    default         none;")
    parts.append("    div(phi,U)      bounded Gauss linearUpwind limited;")
    parts.append("    turbulence      bounded Gauss limitedLinear 1;")
    parts.append("    div(phi,k)      $turbulence;")
    parts.append("    div(phi,{}) $turbulence;".format(second))
    parts.append("    div((nuEff*dev2(T(grad(U))))) Gauss linear;")
    parts.append("}")
    parts.append("")
    parts.append("laplacianSchemes")
    parts.append("{")
    parts.append("    default         Gauss linear corrected;")
    parts.append("}")
    parts.append("")
    parts.append("interpolationSchemes")
    parts.append("{")
    parts.append("    default         linear;")
    parts.append("}")
    parts.append("")
    parts.append("snGradSchemes")
    parts.append("{")
    parts.append("    default         corrected;")
    parts.append("}")
    parts.append("")
    parts.append("wallDist")
    parts.append("{")
    parts.append("    method          meshWave;")
    parts.append("}")
    return "\n".join(parts) + FOOTER


def fv_solution(settings):
    """system/fvSolution for SIMPLE with consistent (SIMPLEC) coupling."""
    rc = settings.residual_control
    parts = []
    parts.append(header("dictionary", "fvSolution", location="system"))
    parts.append("")
    parts.append("solvers")
    parts.append("{")
    parts.append("    p")
    parts.append("    {")
    parts.append("        solver          GAMG;")
    parts.append("        tolerance       1e-06;")
    parts.append("        relTol          0.01;")
    parts.append("        smoother        GaussSeidel;")
    parts.append("    }")
    parts.append('    "(U|k|epsilon|omega)"')
    parts.append("    {")
    parts.append("        solver          smoothSolver;")
    parts.append("        smoother        symGaussSeidel;")
    parts.append("        tolerance       1e-06;")
    parts.append("        relTol          0.01;")
    parts.append("    }")
    parts.append("}")
    parts.append("")
    parts.append("SIMPLE")
    parts.append("{")
    parts.append("    nNonOrthogonalCorrectors 1;")
    parts.append("    consistent      yes;")
    parts.append("    pRefCell        0;")
    parts.append("    pRefValue       0;")
    parts.append("    residualControl")
    parts.append("    {")
    parts.append("        p               {};".format(rc))
    parts.append("        U               {};".format(rc))
    parts.append('        "(k|epsilon|omega)" {};'.format(rc))
    parts.append("    }")
    parts.append("}")
    parts.append("")
    parts.append("relaxationFactors")
    parts.append("{")
    parts.append("    fields")
    parts.append("    {")
    parts.append("        p               0.3;")
    parts.append("    }")
    parts.append("    equations")
    parts.append("    {")
    parts.append("        U               0.7;")
    parts.append('        "(k|epsilon|omega)" 0.5;')
    parts.append("    }")
    parts.append("}")
    return "\n".join(parts) + FOOTER


def decompose_par_dict(n_procs=0):
    """system/decomposeParDict. n_procs<=0 -> auto min(4, cpu_count)."""
    if n_procs and n_procs > 0:
        procs = n_procs
    else:
        procs = min(4, os.cpu_count() or 1)
    parts = []
    parts.append(header("dictionary", "decomposeParDict", location="system"))
    parts.append("")
    parts.append("numberOfSubdomains {};".format(procs))
    parts.append("method          scotch;")
    return "\n".join(parts) + FOOTER, procs
