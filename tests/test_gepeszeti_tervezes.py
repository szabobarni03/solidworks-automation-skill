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


# --- kontúr érintő körökből -----------------------------------------------------------------
def test_kontur_stadium_area():
    k = _load("kontur")
    lanc = k.kontur([("kor", (0, 0), 5), ("kor", (20, 0), 5)])
    assert abs(k.terulet(lanc) - (20 * 10 + math.pi * 25)) < 1e-6


def test_kontur_tapered_link_area_positive_and_closed():
    k = _load("kontur")
    lanc = k.kontur([("kor", (0, 0), 10), ("kor", (0, -50), 6)])
    pts = [(s[1], s[2]) if s[0] == "vonal" else (s[2], s[3]) for s in lanc]
    for (a, b), (c, _) in zip(pts, pts[1:] + pts[:1]):
        assert math.dist(b, c) < 1e-9          # a lánc folytonos
    assert k.terulet(lanc) > 50 * 12


def test_kontur_inner_fillet_on_l_shape():
    # L alak 0-s sugarú "körökkel": 40x10 vízszintes + 10x40 függőleges szár, belső sarok R5
    k = _load("kontur")
    el = [("kor", (0, 40), 0), ("kor", (0, 0), 0), ("kor", (40, 0), 0), ("kor", (40, 10), 0),
          ("sarok", 5, ((10, 10), 0)), ("kor", (10, 40), 0)]
    A = k.terulet(k.kontur(el))
    vart = 40 * 10 + 10 * 30 + (25 - math.pi * 25 / 4)     # belső lekerekítés anyagot ad
    assert abs(A - vart) < 1e-6


def test_kontur_fillet_too_big_raises():
    k = _load("kontur")
    el = [("kor", (0, 40), 0), ("kor", (0, 0), 0), ("kor", (40, 0), 0), ("kor", (40, 10), 0),
          ("sarok", 50, ((10, 10), 0)), ("kor", (10, 40), 0)]
    with pytest.raises(ValueError):
        k.kontur(el)


def test_forgastest_cylinder_volume():
    f = _load("forgastest")
    assert abs(f.terfogat(f.profil([(20, 10)])) - math.pi * 25 * 20) < 1e-9


def test_forgastest_chamfer_and_groove_volume():
    f = _load("forgastest")
    # Ø8 x 3, 1 mm wide Ø6 groove in the middle, 0.5x45 chamfer on the left end
    pts = f.profil([(1, 8), (1, 6), (1, 8)], letores={0: (0.5, 0)})
    kup = math.pi * 0.5 / 3 * (3.5 ** 2 + 3.5 * 4 + 4 ** 2)      # frustum of the chamfer
    vart = kup + math.pi * 16 * 0.5 + math.pi * 9 + math.pi * 16
    assert abs(f.terfogat(pts) - vart) < 1e-9


def test_forgastest_bore_with_countersinks():
    f = _load("forgastest")
    pts = f.profil([(10, 8)], furat=4, sullyesztes=(6, 0))
    sully = math.pi * 1 / 3 * (3 ** 2 + 3 * 2 + 2 ** 2)          # 90 deg countersink, depth 1
    vart = math.pi * 16 * 10 - math.pi * 4 * 9 - sully
    assert abs(f.terfogat(pts) - vart) < 1e-9
    assert min(r for _, r in pts) == 2


def test_forgastest_concave_chamfer_raises():
    f = _load("forgastest")
    with pytest.raises(ValueError):
        f.profil([(5, 6), (5, 10)], letores={0: (0, 0.5)})


def test_osszevetes_kivag_keeps_yellow_on_grey():
    from PIL import Image
    o = _load("osszevetes")
    img = Image.new("RGB", (100, 100), (215, 215, 215))
    img.paste((217, 204, 30), (20, 30, 80, 70))     # yellow: same luminance as the grey background
    assert o.kivag(img).size == (60, 40)


def _metszet_csonk(monkeypatch, tmp_path, ment_hiba=False):
    """Fake SolidWorks doc for ellenorzes.section_image: records the section data and the removal."""
    import sys as _sys
    import types
    allapot = {"torolve": 0, "sd": None}

    class Mvm:
        def CreateSectionViewData(self):
            return types.SimpleNamespace()

        def CreateSectionView(self, sd):
            allapot["sd"] = sd
            return True

        def RemoveSectionView(self):
            allapot["torolve"] += 1

    class Doc:
        ModelViewManager = Mvm()

        def GetType(self):
            return 2

        def GetComponents(self, top):
            return []

        def ShowNamedView2(self, nev, kod):
            allapot["nezet"] = kod

        def ClearSelection2(self, x):
            pass

        def ViewZoomtofit2(self):
            pass

        def GraphicsRedraw2(self):
            pass

        def SaveAs3(self, out, a, b):
            if ment_hiba:
                raise RuntimeError("mentés")
            Path(out).write_bytes(b"png")

    def c0(o, n):
        a = getattr(o, n)
        return a() if callable(a) else a

    swk = types.SimpleNamespace(c0=c0, nv=lambda: None, sw=None, m=lambda v: v / 1000.0,
                                std_planes=lambda d: ["elol", "felul", "jobb"])
    monkeypatch.setitem(_sys.modules, "swk", swk)
    monkeypatch.setitem(_sys.modules, "sw_measure", types.SimpleNamespace(inspect_interference=None))
    return _load("ellenorzes"), Doc(), allapot


def test_section_image_sets_plane_and_part_colored_caps(monkeypatch, tmp_path):
    e, doc, allapot = _metszet_csonk(monkeypatch, tmp_path)
    out = e.section_image(str(tmp_path / "m.png"), plane="felul", offset_mm=-100.0, view=5, doc=doc)
    sd = allapot["sd"]
    assert Path(out).is_file()
    assert sd.FirstPlane == "felul" and abs(sd.FirstOffset + 0.1) < 1e-12
    assert sd.ShowSectionCap is True and sd.KeepCapColor is False   # part-colored caps show overlap
    assert allapot["nezet"] == 5 and allapot["torolve"] == 1


def test_section_image_removes_section_on_failure(monkeypatch, tmp_path):
    e, doc, allapot = _metszet_csonk(monkeypatch, tmp_path, ment_hiba=True)
    with pytest.raises(RuntimeError):
        e.section_image(str(tmp_path / "m.png"), doc=doc)
    assert allapot["torolve"] == 1


def test_mass_check_flags_deviation(monkeypatch, tmp_path):
    e, doc, _ = _metszet_csonk(monkeypatch, tmp_path)
    monkeypatch.setattr(e, "part_report", lambda d: {"bodies": 1, "mass_g": 103.0, "ok": True})
    r = e.mass_check(doc, 100.0, 0.05)
    assert r["ok"] and abs(r["deviation"] - 0.03) < 1e-9
    r = e.mass_check(doc, 100.0, 0.02)
    assert not r["ok"] and not r["mass_ok"]


def test_plane_edges_keeps_outline_and_filters_hole_circles():
    pytest.importorskip("win32com")
    swk = _load("swk")
    from types import SimpleNamespace as NS

    def vonal(root, d):
        return NS(GetCurve=lambda: NS(IsLine=lambda: True, IsCircle=lambda: False, LineParams=(*root, *d)))

    def kor(c, ax, r):
        return NS(GetCurve=lambda: NS(IsLine=lambda: False, IsCircle=lambda: True, CircleParams=(*c, *ax, r)))

    z = 0.006
    elek = [vonal((0, 0, z), (1, 0, 0)),          # fedőlap éle
            vonal((0, 0, z), (0, 0, 1)),          # függőleges él: nem a síkban fekszik
            vonal((0, 0, 0), (1, 0, 0)),          # alsó lap éle
            kor((0, 0, z), (0, 0, 1), 0.004),     # sarokív R4
            kor((0, 0, z), (0, 0, -1), 0.0035),   # furat Ø7
            kor((0, 0, z), (1, 0, 0), 0.004)]     # más irányú kör
    p = object.__new__(swk.Part)
    p.doc = NS(GetBodies2=lambda a, b: [NS(GetEdges=lambda: elek)])
    assert p.plane_edges(2, 6.0, circle_radii=[4]) == [elek[0], elek[3]]
    assert p.plane_edges(2, 6.0) == [elek[0], elek[3], elek[4]]


def test_hexagon_vertex_gives_across_flats():
    """A CreatePolygon pontja csúcs: s laptávolsághoz a csúcs s/√3-on van, a csúcskör d-hez d/2-n."""
    pytest.importorskip("win32com")
    swk = _load("swk")
    from types import SimpleNamespace as NS
    hivas = []
    p = object.__new__(swk.Part)
    p.sm = NS(CreatePolygon=lambda *a: hivas.append(a))
    p.hexagon(0, 0, 10)
    p.hexagon_corner(0, 0, 10)
    (xc, yc, _, xp, yp, _, n, _), (_, _, _, xq, yq, _, _, _) = hivas
    csucs = math.hypot(xp - xc, yp - yc)
    assert n == 6 and abs(2 * csucs * math.cos(math.radians(30)) - 0.010) < 1e-12   # laptávolság 10
    assert abs(math.hypot(xq, yq) - 0.005) < 1e-12                                  # csúcskör Ø10


def test_circular_pattern_marks_seeds_and_axis():
    pytest.importorskip("win32com")
    swk = _load("swk")
    from types import SimpleNamespace as NS
    jel, hivas = [], []

    def feat(nev):
        return NS(Name=nev, Select2=lambda app, mark: jel.append((nev, app, mark)) or True)

    p = object.__new__(swk.Part)
    p.name = "proba"
    p.doc = NS(ClearSelection2=lambda b: None)
    p.fm = NS(FeatureCircularPattern4=lambda *a: hivas.append(a) or "minta")
    assert p.circular_pattern([feat("Vagas1"), feat("Vagas2")], feat("Tengely"), 6) == "minta"
    assert jel == [("Vagas1", True, 4), ("Vagas2", True, 4), ("Tengely", True, 1)]
    n, szog, *_ = hivas[0]
    assert n == 6 and abs(szog - 2 * math.pi) < 1e-12


def test_rgb_szin_is_colorref(monkeypatch):
    import sys as _sys
    import types
    monkeypatch.setitem(_sys.modules, "swk", types.SimpleNamespace(c0=None, sw=None))
    mj = _load("megjelenes")
    assert mj.rgb_szin((60, 78, 96)) == 60 + 78 * 256 + 96 * 65536
    with pytest.raises(ValueError):
        mj.lapok(None, [], "x.p2m")


def test_plane_and_cylinder_faces_filter_by_axis_and_radius():
    pytest.importorskip("win32com")
    swk = _load("swk")
    from types import SimpleNamespace as NS

    def sik(n, pt):
        return NS(GetSurface=lambda: NS(IsPlane=lambda: True, IsCylinder=lambda: False, PlaneParams=(*n, *pt)))

    def henger(ax, r):
        return NS(GetSurface=lambda: NS(IsPlane=lambda: False, IsCylinder=lambda: True,
                                        CylinderParams=(0, 0, 0, *ax, r)))

    lapok = [sik((0, 0, 1), (0, 0, 0.06)), sik((0, 0, -1), (0, 0, 0)), sik((1, 0, 0), (0.022, 0, 0)),
             henger((0, 0, 1), 0.016), henger((0, 0, -1), 0.004), henger((1, 0, 0), 0.003)]
    p = object.__new__(swk.Part)
    p.doc = NS(GetBodies2=lambda a, b: [NS(GetFaces=lambda: lapok)])
    assert p.plane_faces(2) == lapok[:2]
    assert p.plane_faces(2, 60) == [lapok[0]]
    assert p.cylinder_faces(2, exclude_radii=[4]) == [lapok[3]]
    assert p.cylinder_faces(radii=[3]) == [lapok[5]]
