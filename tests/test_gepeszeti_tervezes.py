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


# --- képösszevetés, megjelenés-szabályok, eval (SolidWorks nélkül) ---------------------------
def _kep(meret, doboz, hatter=(230, 230, 230), szin=(20, 20, 20)):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", meret, hatter)
    ImageDraw.Draw(img).rectangle(doboz, fill=szin)
    return img


def test_kivag_removes_background():
    osz = _load("osszevetes")
    k = osz.kivag(_kep((200, 100), (50, 20, 149, 79)))
    assert k.size == (100, 60)


def test_sziluett_identical_shapes_scale_invariant():
    osz = _load("osszevetes")
    a = _kep((200, 200), (40, 40, 159, 99))                         # 120 x 60
    b = _kep((400, 300), (100, 50, 339, 169), hatter=(255, 255, 255))  # 240 x 120, más háttér
    assert osz.sziluett_egyezes(a, b) > 0.98


def test_sziluett_different_shapes_lower():
    from PIL import ImageDraw
    osz = _load("osszevetes")
    a = _kep((200, 200), (20, 20, 179, 179))
    b = _kep((200, 200), (20, 20, 179, 179))
    ImageDraw.Draw(b).rectangle((20, 100, 99, 179), fill=(230, 230, 230))   # L alak
    iou = osz.sziluett_egyezes(a, b)
    assert 0.6 < iou < 0.9


def test_egymas_mellett_and_racs_write_files(tmp_path):
    osz = _load("osszevetes")
    r, s = tmp_path / "r.png", tmp_path / "s.png"
    _kep((300, 200), (10, 10, 200, 150)).save(r)
    _kep((300, 200), (50, 30, 250, 180)).save(s)
    out = osz.egymas_mellett(r, s, tmp_path / "o.png", crop=(0, 0, 250, 180), magassag=200)
    assert Path(out).is_file()
    assert Path(osz.racs([r, s, r], tmp_path / "g.png", szelesseg=100)).is_file()


def test_megjelenes_csoportosit_first_match_wins(monkeypatch):
    import sys as _sys
    import types
    # a megjelenes modul a swk-t importálja (pywin32); a csoportosításhoz nem kell, ezért csonk,
    # amit a monkeypatch a teszt végén visszavon
    monkeypatch.setitem(_sys.modules, "swk", types.SimpleNamespace(c0=None, sw=None))
    mj = _load("megjelenes")
    g = mj.csoportosit(["Ház-1", "Házfedél-1", "Tengely-1", "Egyéb-1"],
                       [("Házfedél", "muanyag"), ("Ház", "alu"), ("Tengely", "acel")])
    assert g == {"alu": ["Ház-1"], "muanyag": ["Házfedél-1"], "acel": ["Tengely-1"]}


def test_eval_cases_consistent():
    ev = _load("eval_ellenor")
    cfg = ev.betolt()
    ids = [e["id"] for e in cfg["esetek"]]
    assert len(ids) == len(set(ids)) >= 5
    for e in cfg["esetek"]:
        el = e["elvart"]
        assert el["testek"] == 1 and el["terfogat_mm3"] > 0
        a, b, c = el["meret_mm"]
        assert a <= b <= c
        assert el["terfogat_mm3"] <= a * b * c          # a térfogat befér a befoglalóba
        assert e["keres"].strip()


def test_eval_ertekel_and_summary():
    ev = _load("eval_ellenor")
    tures = {"terfogat_rel": 0.005, "meret_mm": 0.1}
    elv = {"testek": 1, "terfogat_mm3": 1000.0, "meret_mm": [5, 10, 20]}
    jo = ev.ertekel({"testek": 1, "terfogat_mm3": 1003.0, "meret_mm": [20, 5, 10.05]}, elv, tures)
    assert jo["ok"]
    rossz = ev.ertekel({"testek": 2, "terfogat_mm3": 900.0, "meret_mm": [5, 10, 21]}, elv, tures)
    assert not rossz["ok"] and len(rossz["hibak"]) == 3
    assert ev.ertekel(None, elv, tures)["hibak"] == ["hiányzik az alkatrész"]
    o = ev.osszegez({"a": jo, "b": rossz})
    assert o["sikeres"] == 1 and o["sikertelen"] == ["b"]
    assert ev.osszehasonlit({"a": jo, "b": rossz}, {"a": rossz, "b": rossz}) == {"a": "javult"}
