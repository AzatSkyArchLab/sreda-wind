"""constant/ dictionaries: physicalProperties and momentumTransport.

OpenFOAM 13 split the old transportProperties/turbulenceProperties into
constant/physicalProperties (viscosity) and constant/momentumTransport (the
RAS model). The RAS dict object is named RASProperties, matching the tutorials.
"""
from __future__ import annotations

from ._foam import FOOTER, header


def physical_properties(nu):
    """constant/physicalProperties with a constant kinematic viscosity."""
    parts = []
    parts.append(header("dictionary", "physicalProperties", location="constant"))
    parts.append("")
    parts.append("viscosityModel  constant;")
    parts.append("nu              [0 2 -1 0 0 0 0] {};".format(nu))
    return "\n".join(parts) + FOOTER


def momentum_transport(turbulence_model):
    """constant/momentumTransport selecting the RAS model."""
    parts = []
    parts.append(header("dictionary", "RASProperties", location="constant"))
    parts.append("")
    parts.append("simulationType  RAS;")
    parts.append("")
    parts.append("RAS")
    parts.append("{")
    parts.append("    model           {};".format(turbulence_model))
    parts.append("    turbulence      on;")
    parts.append("    printCoeffs     on;")
    parts.append("}")
    return "\n".join(parts) + FOOTER
