"""Porous-zone case dictionaries for vegetation (topoSetDict + fvOptions).

Trees are modelled as DarcyForchheimer porous zones rather than solid STL: a
cylinderToCell topoSet carves a cellZone for each crown, and fvOptions applies
an inertial (Forchheimer) resistance f = LAD * Cd there. Viscous (Darcy)
resistance is negligible for air and set to zero.

The actual extraction of trees from input geometry belongs to a later elements/
layer; these builders just take a list of PorousZone specs.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._foam import FOOTER, header


@dataclass(frozen=True)
class PorousZone:
    """A cylindrical porous crown."""
    id: str
    center_x: float
    center_y: float
    z_min: float
    z_max: float
    radius: float
    lad: float          # leaf area density [m2/m3]
    cd: float           # leaf drag coefficient
    tree_type: str = "medium"


def topo_set_dict(zones):
    """system/topoSetDict creating a cylinder cellZone per porous crown."""
    parts = []
    parts.append(header("dictionary", "topoSetDict", location="system"))
    parts.append("")
    parts.append("actions")
    parts.append("(")
    i = 0
    while i < len(zones):
        z = zones[i]
        set_name = "treeSet_{}".format(i)
        zone_name = "treeZone_{}".format(i)
        parts.append("    {")
        parts.append("        name    {};".format(set_name))
        parts.append("        type    cellSet;")
        parts.append("        action  new;")
        parts.append("        source  cylinderToCell;")
        parts.append("        // Tree: {} ({})".format(z.id, z.tree_type))
        parts.append("        p1      ({} {} {});".format(z.center_x, z.center_y, z.z_min))
        parts.append("        p2      ({} {} {});".format(z.center_x, z.center_y, z.z_max))
        parts.append("        radius  {};".format(z.radius))
        parts.append("    }")
        parts.append("    {")
        parts.append("        name    {};".format(zone_name))
        parts.append("        type    cellZoneSet;")
        parts.append("        action  new;")
        parts.append("        source  setToCellZone;")
        parts.append("        set     {};".format(set_name))
        parts.append("    }")
        i += 1
    parts.append(");")
    return "\n".join(parts) + FOOTER


def _porous_source(index, zone):
    """One explicitPorositySource block for a crown cellZone."""
    zone_name = "treeZone_{}".format(index)
    f_coef = zone.lad * zone.cd     # Forchheimer (inertial) resistance
    d_coef = 0.0                    # Darcy (viscous) resistance ~ 0 for air
    parts = []
    parts.append("    porosity_{}".format(zone_name))
    parts.append("    {")
    parts.append("        type            explicitPorositySource;")
    parts.append("        active          true;")
    parts.append("        explicitPorositySourceCoeffs")
    parts.append("        {")
    parts.append("            selectionMode   cellZone;")
    parts.append("            cellZone        {};".format(zone_name))
    parts.append("            type            DarcyForchheimer;")
    parts.append("            coordinateSystem")
    parts.append("            {")
    parts.append("                type    cartesian;")
    parts.append("                origin  (0 0 0);")
    parts.append("                coordinateRotation")
    parts.append("                {")
    parts.append("                    type    axesRotation;")
    parts.append("                    e1      (1 0 0);")
    parts.append("                    e2      (0 1 0);")
    parts.append("                }")
    parts.append("            }")
    parts.append("            // {}: LAD={} m2/m3, Cd={}, f=LAD*Cd={:.4f}".format(
        zone.tree_type, zone.lad, zone.cd, f_coef))
    parts.append("            d   ({} {} {});".format(d_coef, d_coef, d_coef))
    parts.append("            f   ({:.4f} {:.4f} {:.4f});".format(f_coef, f_coef, f_coef))
    parts.append("        }")
    parts.append("    }")
    return "\n".join(parts)


def fv_options(zones):
    """constant/fvOptions with one porous source per crown."""
    parts = []
    parts.append(header("dictionary", "fvOptions", location="constant"))
    parts.append("")
    i = 0
    while i < len(zones):
        parts.append(_porous_source(i, zones[i]))
        parts.append("")
        i += 1
    return "\n".join(parts) + FOOTER
