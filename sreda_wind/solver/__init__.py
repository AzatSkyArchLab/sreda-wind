"""Solver layer: run OpenFOAM and judge the result.

logparse/convergence are pure (no OpenFOAM, testable on synthetic logs); runner
is the only module that invokes the shell/OpenFOAM.
"""
from .logparse import (
    TimeStep, SolverLog, CommandLog,
    parse_solver_log, parse_command_log, has_fatal, fatal_message,
)
from .convergence import (
    ConvergenceReport, WindowStat, is_converged, is_stationary, window_stat, evaluate,
)
from .runner import RunConfig, RunResult, run

__all__ = [
    "TimeStep", "SolverLog", "CommandLog",
    "parse_solver_log", "parse_command_log", "has_fatal", "fatal_message",
    "ConvergenceReport", "WindowStat", "is_converged", "is_stationary",
    "window_stat", "evaluate",
    "RunConfig", "RunResult", "run",
]
