"""Unit tests for the post layer (pure dict generation + parsing)."""
import pytest

from sreda_wind.post import (
    LineSample, PointSample, sets_dict, parse_raw, horizontal_speed,
)


def test_sets_dict_line_and_points():
    samples = [
        LineSample(name="wake", start=(0.04, 0.0, 0.003), end=(0.6, 0.0, 0.003), n_points=400),
        PointSample(name="ped", points=((-0.06, 0.0, 0.01), (0.0, -0.05, 0.01))),
    ]
    text = sets_dict(samples, fields=("U",))
    assert "type            sets;" in text
    assert "libsampling.so" in text
    assert "setFormat       raw;" in text
    assert "fields          (U);" in text
    assert "type    lineUniform;" in text
    assert "start   (0.04 0.0 0.003);" in text
    assert "type    points;" in text
    assert "ordered yes;" in text
    assert "(-0.06 0.0 0.01)" in text


def test_parse_raw_skips_comments():
    text = (
        "# x U_x U_y U_z\n"
        "-0.04 3.8 -0.1 1.5\n"
        "\n"
        "0.0 -0.5 0.2 0.0\n"
    )
    rows = parse_raw(text)
    assert len(rows) == 2
    assert rows[0] == [-0.04, 3.8, -0.1, 1.5]
    assert rows[1][1] == -0.5


def test_horizontal_speed():
    assert horizontal_speed(3.0, 4.0) == pytest.approx(5.0)
    assert horizontal_speed(0.0, 0.0) == pytest.approx(0.0)
