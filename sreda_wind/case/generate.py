"""Top-level case generation: tie geometry + core physics into an OpenFOAM case.

generate_case() takes building footprints, a wind (direction + speed) and a
CaseSettings, and writes a complete, runnable OpenFOAM 13 case directory plus a
manifest.json for reproducibility. It performs file I/O only; it imports no
OpenFOAM and runs no solver.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

from ..core.abl import abl_parameters
from ..core.domain import BBox, compute_domain
from ..core.mesh import compute_mesh_spec
from ..core.wind import flow_vector, inflow_velocity
from ..geometry import extrude_footprint, merge, validate_polygon, write_ascii
from . import constant_dicts, fields, mesh_dicts, porous, system_dicts
from .boundary import InletContext, classify_patches
from .settings import C_MU, CaseSettings

OPENFOAM_VERSION = "13"


@dataclass(frozen=True)
class Building:
    """A building footprint with an extrusion height."""
    footprint: list   # list of (x, y); open or closed ring
    height: float


@dataclass
class GeneratedCase:
    """Summary of a generated case (paths and the derived physics objects)."""
    case_dir: str
    domain: object
    mesh_spec: object
    abl: object
    patch_types: dict
    inflow: tuple
    n_procs: int
    files: list
    manifest_path: str


def _point_in_poly(px, py, poly):
    """Ray-casting point-in-polygon test (poly: list of (x, y))."""
    n = len(poly)
    inside = False
    j = n - 1
    i = 0
    while i < n:
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
        i += 1
    return inside


def _geometry_hash(cleaned):
    """Deterministic hash of the cleaned footprints and heights."""
    h = hashlib.sha256()
    i = 0
    while i < len(cleaned):
        b = cleaned[i]
        h.update("h={};".format(b["height"]).encode("utf-8"))
        ring = b["coords"]
        j = 0
        while j < len(ring):
            x, y = ring[j]
            h.update("{:.6f},{:.6f};".format(x, y).encode("utf-8"))
            j += 1
        i += 1
    return h.hexdigest()


def _validate_buildings(buildings, min_area=1.0):
    """Validate footprints; return (cleaned list, bbox, max_height)."""
    cleaned = []
    all_x = []
    all_y = []
    max_height = 0.0
    i = 0
    while i < len(buildings):
        b = buildings[i]
        result = validate_polygon(b.footprint, b.height, min_area=min_area)
        if result is not None:
            cleaned.append(result)
            ring = result["coords"]
            j = 0
            while j < len(ring):
                all_x.append(ring[j][0])
                all_y.append(ring[j][1])
                j += 1
            if b.height > max_height:
                max_height = b.height
        i += 1

    if not cleaned:
        raise ValueError("No valid buildings to mesh")

    bbox = BBox(xmin=min(all_x), xmax=max(all_x),
                ymin=min(all_y), ymax=max(all_y))
    return cleaned, bbox, max_height


def _location_in_mesh(cleaned, bbox, domain, max_height):
    """A point in the fluid region for snappyHexMesh.

    Default to the footprint-bbox centre, lifted above the tallest building.
    If that (x, y) falls inside a footprint, fall back to a near-inlet corner.
    """
    cx = (bbox.xmin + bbox.xmax) / 2.0
    cy = (bbox.ymin + bbox.ymax) / 2.0
    # Lift midway between the building top and the domain top, so the point is
    # always inside the fluid region regardless of scale.
    if domain.zmax > max_height:
        cz = max_height + 0.5 * (domain.zmax - max_height)
    else:
        cz = 0.5 * domain.zmax

    inside = False
    i = 0
    while i < len(cleaned):
        if _point_in_poly(cx, cy, cleaned[i]["coords"]):
            inside = True
            break
        i += 1

    if inside:
        cx = domain.xmin + (domain.xmax - domain.xmin) * 0.1
        cy = domain.ymin + (domain.ymax - domain.ymin) * 0.1
    return (cx, cy, cz)


def _write(case_dir, rel_path, text, written):
    """Write text to case_dir/rel_path and record the relative path."""
    path = os.path.join(case_dir, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    written.append(rel_path)


def generate_case(case_dir, buildings, direction_deg, speed,
                  settings=None, porous_zones=None, inlet_profile=None):
    """Write a complete OpenFOAM 13 case and return a GeneratedCase summary.

    case_dir: target directory (created if missing).
    buildings: list of Building.
    direction_deg: wind direction (meteorological, FROM).
    speed: reference wind speed at settings.z_ref [m/s].
    settings: CaseSettings (defaults applied if None).
    porous_zones: optional list of porous.PorousZone (trees).
    inlet_profile: optional measured inflow as ((z, u, k, eps), ...); when given
        the inlet uses tabulated profiles instead of Richards & Hoxey.
    """
    if settings is None:
        settings = CaseSettings()
    if porous_zones is None:
        porous_zones = []

    cleaned, bbox, max_height = _validate_buildings(buildings, settings.min_building_area)
    H = max_height

    domain = compute_domain(bbox, H, direction_deg, settings.domain_factors)
    mesh_spec = compute_mesh_spec(
        domain, bbox, H,
        target_facade_cell=settings.target_facade_cell,
        cell_budget=settings.cell_budget,
        min_base_cell=settings.min_base_cell)

    abl = abl_parameters(speed, settings.z_ref, settings.z0)
    omega = abl.epsilon / (C_MU * abl.k)

    ux, uy, _ = inflow_velocity(direction_deg, speed)
    flow_x, flow_y = flow_vector(direction_deg)
    patch_types = classify_patches(flow_x, flow_y, symmetry_sides=settings.side_top_symmetry)
    top_bc = "symmetry" if settings.side_top_symmetry else "slip"

    profile = tuple(inlet_profile) if inlet_profile is not None else None
    ctx = InletContext(
        ux=ux, uy=uy, flow_x=flow_x, flow_y=flow_y, speed=speed,
        z_ref=settings.z_ref, z0=settings.z0,
        k=abl.k, epsilon=abl.epsilon, omega=omega, profile=profile)

    location = _location_in_mesh(cleaned, bbox, domain, max_height)

    # Build and write the building STL via the geometry layer.
    meshes = []
    i = 0
    while i < len(cleaned):
        b = cleaned[i]
        meshes.append(extrude_footprint(b["coords"], b["height"]))
        i += 1
    tri_mesh = merge(meshes)
    written = []
    os.makedirs(os.path.join(case_dir, "constant", "triSurface"), exist_ok=True)
    stl_path = os.path.join(case_dir, "constant", "triSurface", "buildings.stl")
    write_ascii(tri_mesh, stl_path, name="buildings")
    written.append("constant/triSurface/buildings.stl")

    # blockMesh patch types: symmetry where confined, patch for inlet/outlet.
    boundary_types = {}
    name_i = 0
    lateral = ("xMin", "xMax", "yMin", "yMax")
    while name_i < len(lateral):
        name = lateral[name_i]
        boundary_types[name] = "symmetry" if patch_types[name] == "symmetry" else "patch"
        name_i += 1
    boundary_types["top"] = "symmetry" if settings.side_top_symmetry else "patch"

    # system/
    _write(case_dir, "system/blockMeshDict",
           mesh_dicts.block_mesh_dict(domain, mesh_spec, settings.vertical_grading,
                                      boundary_types=boundary_types), written)
    _write(case_dir, "system/snappyHexMeshDict",
           mesh_dicts.snappy_hex_mesh_dict(
               mesh_spec, location, settings.cell_budget,
               surface_layers=settings.surface_layers,
               layer_expansion=settings.layer_expansion,
               final_layer_thickness=settings.final_layer_thickness), written)
    _write(case_dir, "system/controlDict",
           system_dicts.control_dict(settings), written)
    _write(case_dir, "system/fvSchemes",
           system_dicts.fv_schemes(settings.turbulence_model), written)
    _write(case_dir, "system/fvSolution",
           system_dicts.fv_solution(settings), written)
    decompose_text, n_procs = system_dicts.decompose_par_dict(settings.n_procs)
    _write(case_dir, "system/decomposeParDict", decompose_text, written)

    # constant/
    _write(case_dir, "constant/physicalProperties",
           constant_dicts.physical_properties(settings.nu), written)
    _write(case_dir, "constant/momentumTransport",
           constant_dicts.momentum_transport(settings.turbulence_model), written)
    # fvOptions is only written when there are porous zones (trees). OpenFOAM
    # treats it as optional; omitting it for the base pipeline avoids the OF13
    # "legacy fvOptions" warning. Trees move to constant/fvModels in elements/.
    if porous_zones:
        _write(case_dir, "system/topoSetDict", porous.topo_set_dict(porous_zones), written)
        _write(case_dir, "constant/fvOptions", porous.fv_options(porous_zones), written)

    # 0/
    field_files = fields.all_fields(patch_types, ctx, settings.turbulence_model,
                                    top_bc=top_bc, ground_z0=settings.ground_z0)
    for name in sorted(field_files):
        _write(case_dir, "0/{}".format(name), field_files[name], written)

    manifest_path = _write_manifest(
        case_dir, cleaned, direction_deg, speed, domain, mesh_spec, abl,
        settings, n_procs, written, profile is not None)

    return GeneratedCase(
        case_dir=case_dir, domain=domain, mesh_spec=mesh_spec, abl=abl,
        patch_types=patch_types, inflow=(ux, uy, 0.0), n_procs=n_procs,
        files=written, manifest_path=manifest_path)


def _write_manifest(case_dir, cleaned, direction_deg, speed, domain, mesh_spec,
                    abl, settings, n_procs, written, tabulated_inlet=False):
    """Write manifest.json capturing everything needed to reproduce the run."""
    manifest = {
        "openfoam_version": OPENFOAM_VERSION,
        "geometry_hash": _geometry_hash(cleaned),
        "n_buildings": len(cleaned),
        "wind": {"direction_deg": direction_deg, "speed": speed},
        "abl": {
            "z0": abl.z0, "z_ref": abl.z_ref, "u_ref": abl.u_ref,
            "ustar": abl.ustar, "k": abl.k, "epsilon": abl.epsilon,
        },
        "domain": {
            "xmin": domain.xmin, "xmax": domain.xmax,
            "ymin": domain.ymin, "ymax": domain.ymax,
            "zmin": domain.zmin, "zmax": domain.zmax,
            "streamwise_axis": domain.streamwise_axis,
        },
        "mesh": {
            "base_cell": mesh_spec.base_cell,
            "nx": mesh_spec.nx, "ny": mesh_spec.ny, "nz": mesh_spec.nz,
            "surface_level": mesh_spec.surface_level,
            "region_level": mesh_spec.region_level,
            "estimated_cells": mesh_spec.estimated_cells,
            "warnings": list(mesh_spec.warnings),
        },
        "solver": {
            "turbulence_model": settings.turbulence_model,
            "iterations": settings.iterations,
            "residual_control": settings.residual_control,
            "nu": settings.nu,
            "n_procs": n_procs,
        },
        "boundary": {
            "ground_z0": settings.ground_z0,
            "side_top_symmetry": settings.side_top_symmetry,
            "surface_layers": settings.surface_layers,
            "tabulated_inlet": tabulated_inlet,
        },
        "output": {"sample_height": settings.sample_height},
    }
    path = os.path.join(case_dir, "manifest.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    written.append("manifest.json")
    return path
