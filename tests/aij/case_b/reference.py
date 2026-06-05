"""Loader and accessors for the AIJ Case B reference data.

Reads validation_data/caseB_data.json (copy of the AIJ xls) and exposes the
pedestrian section (115 points, z/b=0.25), the y=0 vertical section (109 points)
and the 1/4-power inflow profile (12 levels). The reference velocity is U_H at
building height (z=200 mm); it is verified against the data itself in
reference_velocity().
"""
from __future__ import annotations

import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "validation_data", "caseB_data.json")

_REQUIRED_TOP_KEYS = (
    "case", "geometry", "reference_velocity",
    "pedestrian_section", "vertical_section", "inflow_profile",
)


def load_reference(path=None):
    """Load and validate the reference dict (counts, keys, geometry)."""
    if path is None:
        path = _DEFAULT_PATH
    with open(path) as f:
        data = json.load(f)

    i = 0
    while i < len(_REQUIRED_TOP_KEYS):
        key = _REQUIRED_TOP_KEYS[i]
        if key not in data:
            raise ValueError("caseB_data.json missing required key '{}'".format(key))
        i += 1

    if "Case B" not in data["case"]:
        raise ValueError("expected Case B, got '{}'".format(data["case"]))
    if data["geometry"]["b_mm"] <= 0.0:
        raise ValueError("b must be positive")
    if len(pedestrian_points(data)) != 115:
        raise ValueError("expected 115 pedestrian points")
    if len(vertical_points(data)) != 109:
        raise ValueError("expected 109 vertical points")
    if len(inflow_levels(data)) != 12:
        raise ValueError("expected 12 inflow levels")
    return data


def pedestrian_points(data):
    """The 115 pedestrian-plane (z/b=0.25) measured points."""
    return data["pedestrian_section"]["points"]


def vertical_points(data):
    """The 109 y=0 vertical-plane measured points."""
    return data["vertical_section"]["points"]


def inflow_levels(data):
    """Raw inflow levels (dicts with z_mm, z_over_b, U, k)."""
    return data["inflow_profile"]["levels"]


def inflow_points(data):
    """Inflow profile as (z [m], U, k) tuples, sorted by z."""
    out = []
    raw = inflow_levels(data)
    i = 0
    while i < len(raw):
        lv = raw[i]
        out.append((lv["z_mm"] / 1000.0, lv["U"], lv["k"]))
        i += 1
    out.sort(key=_first)
    return out


def _first(item):
    return item[0]


def reference_velocity(data):
    """U_H = inflow U at building height (z=200 mm). The AIJ Case B reference."""
    return data["reference_velocity"]["primary_U_H_mms"]


def solve_reference_from_data(data):
    """Recover the reference velocity X = |Uh|_exp / ratio_UH_exp from the points.

    A self-check that the data really normalises by a single constant. Returns
    (mean, spread) over all points with a non-trivial ratio; mean should equal
    reference_velocity(data) (~5.133) and spread should be tiny.
    """
    xs = []
    pts = pedestrian_points(data)
    i = 0
    while i < len(pts):
        p = pts[i]
        if p["ratio_UH"] > 1.0e-6:
            xs.append(p["Uh"] / p["ratio_UH"])
        i += 1
    lo = min(xs)
    hi = max(xs)
    return sum(xs) / len(xs), hi - lo


def observed_ratios(data):
    """The 115 measured pedestrian ratios (ratio_UH = |Uh|/U_H)."""
    out = []
    pts = pedestrian_points(data)
    i = 0
    while i < len(pts):
        out.append(pts[i]["ratio_UH"])
        i += 1
    return out


def pedestrian_coords(data, z_m=0.0125):
    """The 115 pedestrian sample coordinates as (x, y, z) tuples in metres."""
    out = []
    pts = pedestrian_points(data)
    i = 0
    while i < len(pts):
        p = pts[i]
        out.append((p["x_mm"] / 1000.0, p["y_mm"] / 1000.0, z_m))
        i += 1
    return out
