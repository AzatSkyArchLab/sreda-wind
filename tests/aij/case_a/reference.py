"""Loader and validator for the AIJ Case A reference_data.json.

The file mixes data that is already in hand (approximate inflow profile,
reattachment targets, measurement grid) with data that is still missing (the 60
measured pedestrian wind-speed ratios needed for the hit rate). The loader
exposes both and reports clearly which parts are populated, so the harness can
run the reattachment check now and defer the q check until the xls data lands.
"""
from __future__ import annotations

import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "reference_data.json")

_REQUIRED_TOP_KEYS = (
    "case", "b", "h", "wind_direction_deg",
    "inflow_profile", "reattachment_targets", "pedestrian_ratios_z0125",
)


def load_reference(path=None):
    """Load and validate the reference data; return the parsed dict."""
    if path is None:
        path = _DEFAULT_PATH
    with open(path) as f:
        data = json.load(f)

    i = 0
    while i < len(_REQUIRED_TOP_KEYS):
        key = _REQUIRED_TOP_KEYS[i]
        if key not in data:
            raise ValueError("reference_data.json missing required key '{}'".format(key))
        i += 1

    if data["case"] != "A":
        raise ValueError("expected case 'A', got '{}'".format(data["case"]))
    if data["b"] <= 0.0:
        raise ValueError("b must be positive")

    points = data["inflow_profile"].get("points", [])
    if len(points) < 2:
        raise ValueError("inflow profile needs at least two points")
    return data


def inflow_points(data):
    """Return the inflow profile as a list of (z, u, k) tuples, sorted by z."""
    raw = data["inflow_profile"]["points"]
    out = []
    i = 0
    while i < len(raw):
        p = raw[i]
        out.append((p["z"], p["u"], p["k"]))
        i += 1
    out.sort(key=_first)
    return out


def _first(item):
    return item[0]


def reattachment_targets(data):
    """Return the reattachment targets sub-dictionary."""
    return data["reattachment_targets"]


def has_pedestrian_ratios(data):
    """True if the 60 measured pedestrian ratios are populated."""
    pts = data.get("pedestrian_ratios_z0125", {}).get("points", [])
    return len(pts) > 0


def pedestrian_ratios(data):
    """Return the pedestrian-plane reference points (possibly empty)."""
    return data.get("pedestrian_ratios_z0125", {}).get("points", [])


def secondary_ratios(data):
    """Return the z/b=1.25 secondary-plane reference points (possibly empty)."""
    return data.get("secondary_ratios_z125", {}).get("points", [])


def u_ref(data, plane="pedestrian"):
    """Reference inflow speed for normalising ratios.

    plane="pedestrian" -> U at z/b=0.125 (2.935 m/s); plane="secondary" ->
    U at z/b=1.25 (4.021 m/s). From Table 1 (primary source).
    """
    ur = data["u_ref"]
    if plane == "secondary":
        return ur["z_over_b_125"]
    return ur["z_over_b_0125"]
