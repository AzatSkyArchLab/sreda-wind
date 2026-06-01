"""Solver- and case-level settings, plus shared physical constants.

CaseSettings carries everything the case generator needs that is not derived
from the geometry or the wind: turbulence model, iteration count, ABL roughness,
mesh budget, parallel decomposition, etc. All fields have AIJ-sane defaults so a
bare ``CaseSettings()`` produces a runnable case.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.domain import DomainFactors

# --- physical constants -----------------------------------------------------
KAPPA = 0.41        # von Karman constant
C_MU = 0.09         # k-epsilon model constant
NU_AIR = 1.5e-05    # kinematic viscosity of air [m2/s]

# --- supported turbulence models, grouped by transported variables ----------
# k-epsilon family transports (k, epsilon); k-omega family transports (k, omega).
KE_MODELS = ("kEpsilon", "realizableKE", "RNGkEpsilon")
KOMEGA_MODELS = ("kOmegaSST", "kOmega")


def turbulence_family(model):
    """Return "epsilon" or "omega" for the second transported variable."""
    if model in KE_MODELS:
        return "epsilon"
    if model in KOMEGA_MODELS:
        return "omega"
    raise ValueError(
        "Unsupported turbulence model '{}'. Supported: {}".format(
            model, KE_MODELS + KOMEGA_MODELS))


@dataclass
class CaseSettings:
    """Tunable parameters for one OpenFOAM case.

    AIJ guidelines advise against the standard k-epsilon model, so the default
    is realizable k-epsilon. k-omega SST is also supported.
    """
    # Turbulence
    turbulence_model: str = "realizableKE"

    # Time / convergence (steady SIMPLE: "time" == iteration index)
    iterations: int = 500
    write_interval: int = 0        # 0 -> write only the final iteration
    residual_control: float = 1e-4

    # ABL inflow (Richards & Hoxey)
    z0: float = 0.5                # aerodynamic roughness length [m]
    z_ref: float = 10.0            # reference height [m]
    nu: float = NU_AIR

    # Domain extent (COST 732 factors)
    domain_factors: DomainFactors = field(default_factory=DomainFactors)

    # Mesh sizing (adaptive; no hard cell-count clip)
    target_facade_cell: float = 2.0
    cell_budget: int = 3_000_000
    vertical_grading: float = 2.0  # blockMesh simpleGrading in z (fine near ground)

    # Post-processing
    sample_height: float = 1.75    # pedestrian height [m]

    # Parallel decomposition (0 -> auto: min(4, cpu_count))
    n_procs: int = 0

    def resolved_write_interval(self):
        """Write interval, defaulting to the final iteration only."""
        if self.write_interval and self.write_interval > 0:
            return self.write_interval
        return self.iterations
