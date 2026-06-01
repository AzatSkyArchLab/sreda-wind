"""Case layer: OpenFOAM 13 case generation.

Turns building footprints + a wind + settings into a complete, runnable case
directory (blockMeshDict, snappyHexMeshDict, 0/ fields, system/ and constant/
dicts, optional porous zones) plus a manifest.json for reproducibility. Pure
file I/O on top of core/ and geometry/; no OpenFOAM import, no solver run.
"""
from .settings import (
    CaseSettings, KAPPA, C_MU, NU_AIR,
    KE_MODELS, KOMEGA_MODELS, turbulence_family,
)
from .boundary import InletContext, classify_patches
from .porous import PorousZone, topo_set_dict, fv_options
from .generate import Building, GeneratedCase, generate_case, OPENFOAM_VERSION

__all__ = [
    "CaseSettings", "KAPPA", "C_MU", "NU_AIR",
    "KE_MODELS", "KOMEGA_MODELS", "turbulence_family",
    "InletContext", "classify_patches",
    "PorousZone", "topo_set_dict", "fv_options",
    "Building", "GeneratedCase", "generate_case", "OPENFOAM_VERSION",
]
