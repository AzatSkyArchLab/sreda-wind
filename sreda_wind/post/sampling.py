"""Result extraction: sampling-dict builders and raw-output parsers.

This module is pure string generation and parsing -- it does not invoke
OpenFOAM. It builds the `sets` function-object dictionary that foamPostProcess
consumes (line samples for reattachment, point clouds for probing measurement
points) and parses the resulting raw `.xy` files. Running foamPostProcess is the
caller's job (solver layer / run_validation).
"""
from __future__ import annotations

from dataclasses import dataclass

_BANNER = (
    "/*--------------------------------*- C++ -*----------------------------------*\\\n"
    "\\*---------------------------------------------------------------------------*/\n"
)


@dataclass(frozen=True)
class LineSample:
    """A uniformly-sampled straight line from start to end."""
    name: str
    start: tuple
    end: tuple
    n_points: int


@dataclass(frozen=True)
class PointSample:
    """A named, ordered set of discrete probe points."""
    name: str
    points: tuple   # ((x, y, z), ...)


def _vec(p):
    return "({} {} {})".format(p[0], p[1], p[2])


def sets_dict(samples, fields=("U",)):
    """Build the `sets` function-object dict text for foamPostProcess.

    samples: a list of LineSample and/or PointSample. fields: field names to
    sample. Output is raw format, cellPoint interpolation, ordered points.
    """
    field_list = " ".join(fields)
    parts = []
    parts.append(_BANNER)
    parts.append("type            sets;")
    parts.append('libs            ("libsampling.so");')
    parts.append("interpolationScheme cellPoint;")
    parts.append("setFormat       raw;")
    parts.append("fields          ({});".format(field_list))
    parts.append("sets")
    parts.append("(")
    i = 0
    while i < len(samples):
        s = samples[i]
        parts.append("    {}".format(s.name))
        parts.append("    {")
        if isinstance(s, LineSample):
            parts.append("        type    lineUniform;")
            parts.append("        axis    x;")
            parts.append("        start   {};".format(_vec(s.start)))
            parts.append("        end     {};".format(_vec(s.end)))
            parts.append("        nPoints {};".format(s.n_points))
        else:
            parts.append("        type    points;")
            parts.append("        axis    xyz;")
            parts.append("        ordered yes;")
            parts.append("        points")
            parts.append("        (")
            j = 0
            while j < len(s.points):
                parts.append("            {}".format(_vec(s.points[j])))
                j += 1
            parts.append("        );")
        parts.append("    }")
        i += 1
    parts.append(");")
    return "\n".join(parts) + "\n"


def parse_raw(text):
    """Parse a raw `.xy` sample file into a list of rows of floats.

    Comment (`#`) and blank lines are skipped. Each returned row is the list of
    numeric columns on that line (e.g. [x, Ux, Uy, Uz] for a line sample of U).
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split()
        values = []
        i = 0
        while i < len(cols):
            values.append(float(cols[i]))
            i += 1
        rows.append(values)
    return rows


def horizontal_speed(u, v):
    """Horizontal scalar speed sqrt(u^2 + v^2) (AIJ ratio convention)."""
    return (u * u + v * v) ** 0.5
