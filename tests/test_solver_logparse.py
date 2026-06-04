"""Unit tests for the solver log parsers (pure, no OpenFOAM)."""
import math

import pytest

from sreda_wind.solver import (
    parse_solver_log, parse_command_log, has_fatal,
)

CONVERGED_LOG = """\
sigFpe : Floating point exception trapping - not supported on this platform
Time = 1

smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.004, No Iterations 3
smoothSolver:  Solving for Uy, Initial residual = 0.8, Final residual = 0.003, No Iterations 3
GAMG:  Solving for p, Initial residual = 0.5, Final residual = 0.0004, No Iterations 4
GAMG:  Solving for p, Initial residual = 0.1, Final residual = 0.0003, No Iterations 3
time step continuity errors : sum local = 2.5e-06, global = 2e-07, cumulative = 4e-08
smoothSolver:  Solving for epsilon, Initial residual = 0.06, Final residual = 0.0002, No Iterations 2
smoothSolver:  Solving for k, Initial residual = 0.07, Final residual = 0.0003, No Iterations 2
ExecutionTime = 1 s  ClockTime = 1 s

Time = 2

smoothSolver:  Solving for Ux, Initial residual = 0.01, Final residual = 0.0001, No Iterations 4
GAMG:  Solving for p, Initial residual = 0.005, Final residual = 1e-06, No Iterations 4
time step continuity errors : sum local = 3e-07, global = 9e-08, cumulative = 4.5e-08
smoothSolver:  Solving for k, Initial residual = 0.001, Final residual = 1e-06, No Iterations 3
ExecutionTime = 2 s  ClockTime = 2 s

SIMPLE solution converged in 2 iterations

End
"""


def test_converged_log():
    log = parse_solver_log(CONVERGED_LOG)
    assert log.n_steps == 2
    assert log.last_time == pytest.approx(2.0)
    assert log.converged is True
    assert log.diverged is False
    assert log.fatal is False
    # p keeps the FIRST corrector's initial residual (0.5, not 0.1) at step 1.
    assert log.timesteps[0].residuals["p"][0] == pytest.approx(0.5)
    # continuity parsed.
    assert log.timesteps[0].continuity[2] == pytest.approx(4e-08)
    # final residuals are the last step's initial residuals.
    assert log.final_residuals["p"] == pytest.approx(0.005)
    assert log.final_residuals["Ux"] == pytest.approx(0.01)


def _grow_log():
    # >= _GROWTH_WINDOW (8) steps, rising, ending well above the 10.0 ceiling.
    steps = [0.01, 0.02, 0.08, 0.5, 2.0, 8.0, 25.0, 70.0, 150.0]
    out = []
    t = 1
    i = 0
    while i < len(steps):
        out.append("Time = {}\n".format(t))
        out.append("smoothSolver:  Solving for Ux, Initial residual = {}, Final residual = 0.1, No Iterations 5\n".format(steps[i] * 0.5))
        out.append("GAMG:  Solving for p, Initial residual = {}, Final residual = 0.01, No Iterations 5\n".format(steps[i]))
        out.append("time step continuity errors : sum local = 1e-3, global = 1e-4, cumulative = 1e-5\n")
        t += 1
        i += 1
    return "".join(out)


def test_diverging_growth():
    log = parse_solver_log(_grow_log())
    assert log.diverged is True
    assert "grow" in log.divergence_reason
    assert log.converged is False


def test_diverging_nan():
    text = (
        "Time = 1\nGAMG:  Solving for p, Initial residual = 0.1, Final residual = 0.01, No Iterations 3\n"
        "Time = 2\nGAMG:  Solving for p, Initial residual = nan, Final residual = nan, No Iterations 1000\n"
    )
    log = parse_solver_log(text)
    assert log.diverged is True
    assert "nan" in log.divergence_reason
    assert math.isnan(log.final_residuals["p"])


def test_floating_point_exception():
    text = (
        "Time = 1\nGAMG:  Solving for p, Initial residual = 0.1, Final residual = 0.01, No Iterations 3\n"
        "#0  Foam::error::printStack(...)\nFloating point exception (core dumped)\n"
    )
    log = parse_solver_log(text)
    assert log.diverged is True
    assert "floating point" in log.divergence_reason


def test_runaway_continuity():
    text = (
        "Time = 1\nGAMG:  Solving for p, Initial residual = 0.1, Final residual = 0.01, No Iterations 3\n"
        "time step continuity errors : sum local = 1, global = 1, cumulative = 50000\n"
    )
    log = parse_solver_log(text)
    assert log.diverged is True
    assert "continuity" in log.divergence_reason


def test_fatal_in_solver_log():
    text = (
        "Time = 1\n\n--> FOAM FATAL IO ERROR: \nUnknown patchField type atmFoo\n\nFOAM exiting\n"
    )
    log = parse_solver_log(text)
    assert log.fatal is True
    assert "FATAL" in log.fatal_message


def test_alive_run_with_pinit_1p0_not_diverged():
    # A live, slowly-converging RANS run: p initial residual STARTS at 1.0
    # (normal) and drifts down. Must NOT be flagged diverged (the false-positive
    # the global-minimum criterion would have triggered).
    ps = [1.0, 0.9, 0.85, 0.8, 0.78, 0.75, 0.72, 0.7, 0.69, 0.68]
    out = ["sigFpe : Floating point exception trapping - not supported on this platform\n"]
    t = 1
    i = 0
    while i < len(ps):
        out.append("Time = {}s\n".format(t))
        out.append("GAMG:  Solving for p, Initial residual = {}, Final residual = 0.01, No Iterations 4\n".format(ps[i]))
        out.append("time step continuity errors : sum local = 1e-6, global = 1e-7, cumulative = 1e-3\n")
        t += 1
        i += 1
    log = parse_solver_log("".join(out))
    assert log.n_steps == 10
    assert log.diverged is False      # p ~ 1.0 is healthy, not a blow-up
    assert log.converged is False     # but it did not reach residualControl


def test_empty_log():
    log = parse_solver_log("")
    assert log.n_steps == 0
    assert log.diverged is False and log.fatal is False
    assert log.final_residuals == {}
    assert log.last_time == 0.0


def test_truncated_mid_iteration():
    # foamRun killed by a timeout mid-step: partial residuals, no continuity.
    text = "Time = 5s\nsmoothSolver:  Solving for Ux, Initial residual = 0.5, Final residual = 0.001, No Iterations 3\n"
    log = parse_solver_log(text)
    assert log.n_steps == 1
    assert "Ux" in log.timesteps[0].residuals
    assert log.timesteps[0].continuity is None
    assert log.diverged is False and log.fatal is False


def test_no_iteration_log():
    # foamRun died during initialisation: header only, no "Time =".
    text = "Create time\nCreate mesh\nReading field U\n... (crashed reading) ...\n"
    log = parse_solver_log(text)
    assert log.n_steps == 0
    assert log.final_residuals == {}
    assert log.converged is False and log.diverged is False


# --- command (mesh utility) logs -------------------------------------------

def test_command_log_mesh_ok():
    text = "Create mesh\ncells:           463166\n...\nMesh OK.\nEnd\n"
    out = parse_command_log(text)
    assert out.ok is True
    assert out.mesh_ok is True
    assert out.cells == 463166


def test_command_log_fatal():
    text = "Creating block mesh\n--> FOAM FATAL ERROR: \nNegative volume\nFOAM exiting\n"
    out = parse_command_log(text)
    assert out.ok is False
    assert "FATAL" in out.fatal_message
    assert has_fatal(text) is True


def test_command_log_cells_after_refinement():
    text = "Initial mesh : cells:8100\nAfter refinement : cells:463166\n"
    out = parse_command_log(text)
    assert out.cells == 463166   # last reported count wins
