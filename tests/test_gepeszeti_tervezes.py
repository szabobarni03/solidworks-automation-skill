"""gepeszeti-tervezes subskill: transzform-matematika és csomagszerkezet (SolidWorks nélkül)."""
import importlib.util
import math
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "subskills" / "gepeszeti-tervezes"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tf = _load("transzform")


def close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def test_rot_z_maps_x_to_y():
    assert close(tf.apply(tf.rot_z(math.pi / 2), (0, 0, 0), (1, 0, 0)), (0, 1, 0))


def test_mul_order_first_a_then_b():
    R = tf.mul(tf.rot_x(math.pi / 2), tf.rot_z(math.pi / 2))
    p = tf.apply(R, (0, 0, 0), (0, 1, 0))
    q = tf.apply(tf.rot_z(math.pi / 2), (0, 0, 0), tf.apply(tf.rot_x(math.pi / 2), (0, 0, 0), (0, 1, 0)))
    assert close(p, q)


def test_axes_rows_are_axis_images():
    R = tf.axes((0, 0, 1), (1, 0, 0))
    assert R[2] == (0, 1, 0)
    assert close(tf.apply(R, (5, 0, 0), (1, 0, 0)), (5, 0, 1))
    assert abs(tf.det(R) - 1) < 1e-12


def test_transform_data_layout_and_units():
    d = tf.transform_data(tf.I3, (10, -20, 30.5))
    assert len(d) == 16
    assert d[9:12] == [0.01, -0.02, 0.0305]
    assert d[12:] == [1.0, 0.0, 0.0, 0.0]


def test_transform_data_rejects_mirror():
    with pytest.raises(ValueError):
        tf.transform_data(((1, 0, 0), (0, 1, 0), (0, 0, -1)))


def test_map_points_board_style_rotation():
    # STEP x -> modell Z, STEP y -> modell X, STEP z -> modell Y (tükrözés nélküli forgatás)
    R = ((0, 0, 1), (1, 0, 0), (0, 1, 0))
    pts = tf.map_points([(50.0, 20.0, 0)], R, (-20.0, 0, -50.0))
    assert close(pts[0], (0, 0, 0))


def test_manifest_lists_existing_files():
    text = (SKILL / "manifest.yaml").read_text(encoding="utf-8")
    listed = [ln.strip()[2:] for ln in text.splitlines() if ln.strip().startswith("- ") and "/" in ln]
    assert listed, "üres manifest"
    for rel in listed:
        assert (SKILL / rel).is_file(), rel
    assert (SKILL / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: gepeszeti-tervezes\n")


def test_subskill_indexed():
    idx = (SKILL.parents[1] / "SUBSKILLS.md").read_text(encoding="utf-8")
    assert "`gepeszeti-tervezes`" in idx
