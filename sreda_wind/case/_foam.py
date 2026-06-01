"""FoamFile header helper.

Every OpenFOAM dictionary file starts with a banner comment and a FoamFile
sub-dictionary declaring its class and object. This module centralises that
boilerplate so the dict builders stay focused on content.
"""
from __future__ import annotations

BANNER = (
    "/*--------------------------------*- C++ -*----------------------------------*\\\n"
    "  =========                 |\n"
    "  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox\n"
    "   \\\\    /   O peration     | Website:  https://openfoam.org\n"
    "    \\\\  /    A nd           | Version:  13\n"
    "     \\\\/     M anipulation  |\n"
    "\\*---------------------------------------------------------------------------*/\n"
)

FOOTER = (
    "\n// ************************************************************************* //\n"
)


def header(cls, obj, location=None):
    """Return the banner plus FoamFile sub-dictionary for a given class/object.

    cls: OpenFOAM class (e.g. "dictionary", "volVectorField").
    obj: object name (e.g. "controlDict", "U").
    location: optional case-relative directory (e.g. "0", "system").
    """
    lines = []
    lines.append(BANNER)
    lines.append("FoamFile")
    lines.append("{")
    lines.append("    format      ascii;")
    lines.append("    class       {};".format(cls))
    if location is not None:
        lines.append('    location    "{}";'.format(location))
    lines.append("    object      {};".format(obj))
    lines.append("}")
    lines.append(
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n")
    return "\n".join(lines)
