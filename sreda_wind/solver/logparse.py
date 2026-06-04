"""Pure parsers for OpenFOAM logs (foamRun and the mesh utilities).

No OpenFOAM, no I/O: every function takes log text and returns structured data.
The solver log parser extracts the per-iteration residuals and continuity errors,
detects the convergence message, and — importantly — detects divergence/blow-up
(nan/inf, floating point exception, growing residuals, runaway continuity) so a
batch run is never silently reported as fine when it actually exploded.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Divergence thresholds. Normalised initial residuals sit at ~1 at most for a
# healthy RANS run (p and k routinely start at 1.0), so growth is judged by a
# rising trend over the last window AND a clearly-unphysical magnitude, never by
# a global-minimum ratio (which false-flags a run whose residual sits near 1).
_GROWTH_WINDOW = 8         # last N initial residuals examined for a rising trend
_DIVERGE_RESIDUAL = 10.0   # an initial residual above this is a genuine blow-up
_CONTINUITY_CEILING = 1.0e3   # |cumulative continuity| above this -> runaway

_TIME_RE = re.compile(r"^Time = ([0-9.eE+\-]+)s?\s*$")
_SOLVE_RE = re.compile(
    r"Solving for (\w+),\s*Initial residual = (\S+),\s*Final residual = (\S+)")
_CONT_RE = re.compile(
    r"continuity errors : sum local = (\S+), global = (\S+), cumulative = (\S+)")
_CONVERGED_RE = re.compile(r"solution converged", re.IGNORECASE)
_FATAL_RE = re.compile(r"FOAM FATAL (IO )?ERROR")
# Match a genuine FPE crash, NOT the benign startup line
# "sigFpe : Floating point exception trapping - ...".
_FPE_RE = re.compile(r"Floating point exception \(core dumped\)|sigFpe::sigHandler")


@dataclass
class TimeStep:
    """One solver iteration (steady SIMPLE: one outer iteration)."""
    time: float
    residuals: dict = field(default_factory=dict)   # field -> (initial, final)
    continuity: tuple = None                         # (local, global, cumulative)


@dataclass
class SolverLog:
    """Parsed foamRun log."""
    timesteps: list = field(default_factory=list)
    converged: bool = False
    diverged: bool = False
    divergence_reason: str = ""
    fatal: bool = False
    fatal_message: str = ""
    last_time: float = 0.0
    n_steps: int = 0
    final_residuals: dict = field(default_factory=dict)


@dataclass
class CommandLog:
    """Parsed log of a mesh utility (blockMesh / snappyHexMesh / checkMesh / topoSet)."""
    ok: bool = True
    fatal_message: str = ""
    mesh_ok: bool = False
    cells: int = 0


def _to_float(token):
    """Parse a residual token to float, mapping nan/inf strings to floats."""
    t = token.strip().rstrip(",")
    low = t.lower()
    if "nan" in low:
        return float("nan")
    if "inf" in low:
        return float("inf")
    try:
        return float(t)
    except ValueError:
        return float("nan")


def _is_bad(x):
    """True if x is nan or inf."""
    return x != x or x == float("inf") or x == float("-inf")


def has_fatal(text):
    """True if the text contains a FOAM FATAL (IO) ERROR."""
    return _FATAL_RE.search(text) is not None


def fatal_message(text):
    """Return the first FATAL block (a few lines) or empty string."""
    m = _FATAL_RE.search(text)
    if m is None:
        return ""
    start = m.start()
    chunk = text[start:start + 400]
    return chunk.strip()


def parse_command_log(text):
    """Parse a mesh-utility log: FATAL state, 'Mesh OK', and cell count."""
    out = CommandLog()
    if has_fatal(text):
        out.ok = False
        out.fatal_message = fatal_message(text)
    if "Mesh OK" in text:
        out.mesh_ok = True
    cells = 0
    for m in re.finditer(r"cells:\s*(\d+)", text):
        cells = int(m.group(1))   # keep the last reported count (after refinement)
    out.cells = cells
    return out


def parse_solver_log(text):
    """Parse a foamRun log into a SolverLog (residuals, continuity, status)."""
    log = SolverLog()
    current = None
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        tm = _TIME_RE.match(line)
        if tm is not None:
            current = TimeStep(time=_to_float(tm.group(1)))
            log.timesteps.append(current)
            i += 1
            continue
        sm = _SOLVE_RE.search(line)
        if sm is not None and current is not None:
            fld = sm.group(1)
            if fld not in current.residuals:   # first solve of the field wins
                current.residuals[fld] = (_to_float(sm.group(2)), _to_float(sm.group(3)))
            i += 1
            continue
        cm = _CONT_RE.search(line)
        if cm is not None and current is not None:
            current.continuity = (_to_float(cm.group(1)),
                                  _to_float(cm.group(2)),
                                  _to_float(cm.group(3)))
            i += 1
            continue
        if _CONVERGED_RE.search(line):
            log.converged = True
        if _FATAL_RE.search(line):
            log.fatal = True
            log.fatal_message = fatal_message("\n".join(lines[i:i + 12]))
        if _FPE_RE.search(line):
            log.diverged = True
            log.divergence_reason = "floating point exception"
        i += 1

    log.n_steps = len(log.timesteps)
    if log.n_steps > 0:
        last = log.timesteps[-1]
        log.last_time = last.time
        out = {}
        for name in last.residuals:
            out[name] = last.residuals[name][0]
        log.final_residuals = out

    _detect_divergence(log)
    return log


def _detect_divergence(log):
    """Flag divergence from nan/inf, growing residuals, or runaway continuity."""
    if log.diverged:
        return   # already set (e.g. floating point exception)

    # nan/inf in any residual or continuity value.
    j = 0
    while j < len(log.timesteps):
        ts = log.timesteps[j]
        for name in ts.residuals:
            init, fin = ts.residuals[name]
            if _is_bad(init) or _is_bad(fin):
                log.diverged = True
                log.divergence_reason = "nan or inf residual ({})".format(name)
                return
        if ts.continuity is not None:
            k = 0
            while k < len(ts.continuity):
                if _is_bad(ts.continuity[k]):
                    log.diverged = True
                    log.divergence_reason = "nan or inf continuity error"
                    return
                k += 1
            if abs(ts.continuity[2]) > _CONTINUITY_CEILING:
                log.diverged = True
                log.divergence_reason = "runaway continuity error"
                return
        j += 1

    # Growing residuals: judge by the last window's trend, not a global minimum.
    # Flag only a rising window whose latest residual is clearly unphysical
    # (> _DIVERGE_RESIDUAL); a residual sitting near 1 (normal, even on a coarse
    # mesh) is never flagged.
    series = _field_series(log, "p")
    if len(series) < _GROWTH_WINDOW:
        series = _field_series(log, "Ux")
    if len(series) >= _GROWTH_WINDOW:
        window = series[len(series) - _GROWTH_WINDOW:]
        last = window[-1]
        rising = last > window[0]
        if rising and last > _DIVERGE_RESIDUAL:
            log.diverged = True
            log.divergence_reason = "residuals growing (diverging)"


def _field_series(log, name):
    """Initial-residual series for a field across timesteps (skipping gaps)."""
    series = []
    j = 0
    while j < len(log.timesteps):
        res = log.timesteps[j].residuals
        if name in res:
            series.append(res[name][0])
        j += 1
    return series
