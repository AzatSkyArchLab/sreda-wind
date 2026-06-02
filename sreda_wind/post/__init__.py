"""Post-processing layer: sampling-dict generation and result parsing.

Pure Python (string generation + parsing); no OpenFOAM import. The actual
foamPostProcess invocation belongs to the solver layer / validation harness.
"""
from .sampling import (
    LineSample, PointSample, sets_dict, parse_raw, horizontal_speed,
)

__all__ = [
    "LineSample", "PointSample", "sets_dict", "parse_raw", "horizontal_speed",
]
