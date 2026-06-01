"""Unit tests for the AIJ validation metrics (pure math, no OpenFOAM)."""
import math

import pytest

from aij.metrics import (
    compute_metrics, hit_rate, fac2, nmse, fractional_bias, pearson_r,
)


def test_perfect_prediction():
    o = [0.41, 0.55, 1.20, 0.80]
    p = list(o)
    m = compute_metrics(o, p)
    assert m.n == 4
    assert m.q == 1.0
    assert m.fac2 == 1.0
    assert m.nmse == pytest.approx(0.0)
    assert m.fb == pytest.approx(0.0)
    assert m.r == pytest.approx(1.0)


def test_known_offset_doubled():
    # P = 2 O. Hand-computed: q=0, FAC2=1, NMSE=9/14, FB=-2/3, R=1.
    o = [1.0, 2.0, 4.0]
    p = [2.0, 4.0, 8.0]
    m = compute_metrics(o, p)
    assert m.q == pytest.approx(0.0)
    assert m.fac2 == pytest.approx(1.0)
    assert m.nmse == pytest.approx(9.0 / 14.0)
    assert m.fb == pytest.approx(-2.0 / 3.0)
    assert m.r == pytest.approx(1.0)


def test_hit_rate_relative_and_absolute():
    # D=0.25, W=0.06. Points 1 and 3 hit; 2 and 4 miss -> q = 0.5.
    o = [1.0, 1.0, 1.0, 1.0]
    p = [1.1, 1.3, 1.0, 2.0]
    assert hit_rate(o, p) == pytest.approx(0.5)


def test_hit_rate_absolute_rescues_small_values():
    # Large relative error but tiny absolute error -> hit via W.
    o = [0.01]
    p = [0.05]
    assert hit_rate(o, p, d=0.25, w=0.06) == 1.0
    assert hit_rate(o, p, d=0.25, w=0.03) == 0.0


def test_hit_rate_zero_observed_uses_absolute_only():
    assert hit_rate([0.0], [0.05]) == 1.0
    assert hit_rate([0.0], [0.5]) == 0.0


def test_fac2_bounds():
    o = [1.0, 1.0, 1.0]
    p = [0.5, 2.0, 2.5]   # third is out of [0.5, 2]
    assert fac2(o, p) == pytest.approx(2.0 / 3.0)


def test_fractional_bias_sign():
    # Over-prediction -> negative FB.
    assert fractional_bias([1.0, 1.0], [2.0, 2.0]) < 0.0
    # Under-prediction -> positive FB.
    assert fractional_bias([2.0, 2.0], [1.0, 1.0]) > 0.0


def test_pearson_constant_series_is_nan():
    assert math.isnan(pearson_r([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]))


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        compute_metrics([1.0, 2.0], [1.0])
