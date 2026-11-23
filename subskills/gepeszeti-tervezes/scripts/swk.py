"""SolidWorks COM alapok, alkatrész-építő, összeállítás és illesztések (pywin32).

Kipróbálva: SolidWorks 2026, német felület. Minden méret mm-ben, a COM felé méterben megy.
Vázlatsíkok (vázlat x,y -> modell):
  elöl (front): (X, Y), normális +Z
  felül (top):  (X, -Z), normális +Y
  jobb (right): (-Z, Y), normális +X
"""
import math
import os
import sys
import time
from pathlib import Path

import pythoncom
import win32com.client
from win32com.client import VARIANT

PARENT_SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"
HERE = Path(__file__).resolve().parent
for _p in (str(PARENT_SCRIPT_DIR), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sw_assembly import (add_component, add_mate5_checked, create_math_transform,  # noqa: E402
                         get_assembly_entity, select_entities_for_mate)
from sw_connect import create_empty_dispatch_variant, get_com_member  # noqa: E402
from transzform import I3, transform_data  # noqa: E402

MATE_COINCIDENT, MATE_CONCENTRIC, MATE_PARALLEL, MATE_DISTANCE, MATE_LOCK = 0, 1, 3, 5, 16


# ---------------------------------------------------------------------------
#  COM alapok
# ---------------------------------------------------------------------------
def m(v):
    """mm -> m."""
    return v / 1000.0


def c0(obj, name):
    """Paraméter nélküli COM tag olvasása.

    A pywin32 egyes tagokat metódusként, másokat property-ként ad vissza, ugyanazon a
    típuson belül is változóan. Csak akkor hívjuk meg, ha hívható és nem CDispatch.
    """
    attr = getattr(obj, name)
    if callable(attr) and not isinstance(attr, win32com.client.CDispatch):
        return attr()
    return attr


def nv():
    """Üres callout / selection-data paraméter (VT_DISPATCH None)."""
    return create_empty_dispatch_variant()


def byref_int():
    """Kimeneti int paraméter (hiba/figyelmeztetés kódokhoz)."""
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


_SW = None


def sw():
    global _SW
    if _SW is None:
        pythoncom.CoInitialize()
        _SW = win32com.client.GetActiveObject("SldWorks.Application")
    return _SW


def close(title):
    try:
        sw().CloseDoc(title)
    except Exception:
        pass


def open_doc(path, doc_type=None):
    """Dokumentum megnyitása és aktiválása. doc_type: 1 alkatrész, 2 összeállítás, 3 rajz."""
    if doc_type is None:
        doc_type = {".SLDPRT": 1, ".SLDASM": 2, ".SLDDRW": 3}[os.path.splitext(path)[1].upper()]
    e, w = byref_int(), byref_int()
    d = sw().OpenDoc6(path, doc_type, 1, "", e, w)
    if d is None:
        raise RuntimeError(f"Megnyitás sikertelen ({e.value}): {path}")
    sw().ActivateDoc3(os.path.basename(path), False, 0, e)
    return d


def props(doc, **kw):
    """Egyéni tulajdonságok (szöveg, felülírással)."""
    mgr = doc.Extension.CustomPropertyManager("")
    for k, v in kw.items():
        mgr.Add3(k, 30, str(v), 2)


def set_color(doc, rgb, specular=0.5, transparency=0.0):
    """Alkatrész színe. A MaterialPropertyValues-t explicit VT_ARRAY|VT_R8 VARIANT-tal kell írni:
    sima Python-listával az értékek elcsúsznak (R a 2., G az 5., B a 8. = átlátszóság helyre kerül),
    és az alkatrész átlátszó, zöldes lesz. Sorrend: R, G, B, ambient, diffuse, specular, shininess,
    transparency, emission.
    """
    vals = [rgb[0], rgb[1], rgb[2], 0.6, 0.8, specular, 0.4, transparency, 0.0]
    doc.MaterialPropertyValues = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, vals)


_ANYAGNEVEK = {}


def _anyagnevek(nyelv):
    """Az anyagkönyvtár anyagnevei a megadott nyelven, a fájlbeli sorrendben (a nyelvi fájlok
    sorrendje azonos, így az index fordít)."""
    import re
    if nyelv not in _ANYAGNEVEK:
        path = os.path.join(c0(sw(), "GetExecutablePath"), "lang", nyelv, "sldmaterials",
                            "solidworks materials.sldmat")
        with open(path, encoding="utf-16") as f:
            _ANYAGNEVEK[nyelv] = re.findall(r'<material name="([^"]*)"', f.read())
    return _ANYAGNEVEK[nyelv]


def set_material(doc, name, database="SOLIDWORKS Materials"):
    """Anyag hozzárendelése az aktív konfigurációhoz, visszaolvasással ellenőrizve.

    A név az angol anyagnév (pl. "AISI 1020 Steel, Cold Rolled", "AISI 304", "POM Acetal Copolymer").
    Buktató: a `SetMaterialPropertyName2` csak a felület nyelvén megadott névvel működik (német
    felületen "AISI 1020 Kaltgewalzter Stahl"), angol névvel hiba nélkül nem csinál semmit. Ezért
    az angol nevet a nyelvi anyagkönyvtárak azonos indexe alapján lefordítjuk.
    """
    nyelv = c0(sw(), "GetCurrentLanguage")
    helyi = name
    if nyelv != "english":
        angol = _anyagnevek("english")
        if name in angol:
            helyi = _anyagnevek(nyelv)[angol.index(name)]
    cfg = c0(c0(doc, "ConfigurationManager"), "ActiveConfiguration").Name
    doc.SetMaterialPropertyName2(cfg, database, helyi)
    db = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")   # kimeneti paraméter: az adatbázis neve
    got = doc.GetMaterialPropertyName2(cfg, db)
    got = got[0] if isinstance(got, tuple) else got
    if got != helyi:
        raise RuntimeError(f"Anyag nem állítható be: {name} / {helyi} (kapott: {got!r})")
    return helyi


def std_planes(model):
    """Az első három referenciasík: elöl, felül, jobb (nyelvfüggetlen, nem név alapján)."""
    out = []
    f = c0(model, "FirstFeature")
    while f is not None and len(out) < 3:
        if c0(f, "GetTypeName2") == "RefPlane":
            out.append(f)
        f = c0(f, "GetNextFeature")
    return out


# ---------------------------------------------------------------------------
#  Alkatrész
# ---------------------------------------------------------------------------
class Part:
    """Alkatrész építése vázlat + kihúzás/vágás/forgatás lépésekkel. Mentéskor testszám-ellenőrzés."""

    def __init__(self, name, out_dir):
        self.name = name
        self.path = os.path.join(out_dir, name + ".SLDPRT")
        os.makedirs(out_dir, exist_ok=True)
        close(name + ".SLDPRT")
        self.doc = sw().NewDocument(sw().GetUserPreferenceStringValue(8), 0, 0, 0)
        if self.doc is None:
            raise RuntimeError("Új alkatrész sikertelen")
        self.sm = self.doc.SketchManager
        self.fm = self.doc.FeatureManager
        self.front, self.top, self.right = std_planes(self.doc)
        self.ref_geom = []
        self.sm.AddToDB = True

    # --- síkok, tengelyek, pontok (illesztésekhez) --------------------------
    def plane(self, base, dist, name=None, flip=False):
        """Párhuzamos sík `dist` távolságra. flip=True: a másik oldalra (swRefPlaneReferenceConstraint
        _OptionFlip = 256); negatív távolság helyett ezt használd."""
        self.doc.ClearSelection2(True)
        base.Select2(False, 0)
        p = self.fm.InsertRefPlane(8 + (256 if flip else 0), m(dist), 0, 0, 0, 0)
        if p is None:
            raise RuntimeError(f"{self.name}: sík sikertelen")
        if name:
            p.Name = name
        self.ref_geom.append(p)
        return p

    def axis(self, p1, p2, name):
        """Referenciatengely két sík metszeteként."""
        self.doc.ClearSelection2(True)
        p1.Select2(False, 0)
        p2.Select2(True, 0)
        if not self.doc.InsertAxis2(True):
            raise RuntimeError(f"{self.name}: tengely sikertelen")
        f = self.doc.FeatureByPositionReverse(0)
        f.Name = name
        self.ref_geom.append(f)
        self.doc.ClearSelection2(True)
        return f

    def hole_axis(self, x, y, z, name):
        """Referenciatengely egy hengeres lapon (furat, csap) át. (x, y, z): a lap egy pontja (mm),
        pl. furatnál a fal egy pontja. Illesztéshez megbízhatóbb, mint a lapot az összeállításban
        kijelölni: ott a csap és a furat lapja egybeesik."""
        self.doc.ClearSelection2(True)
        lap = self._henger_lap(m(x), m(y), m(z))
        if lap is None:
            raise RuntimeError(f"{self.name}: nincs hengeres lap ezen a ponton: {(x, y, z)}")
        lap.Select4(False, nv())
        if not self.doc.InsertAxis2(True):
            raise RuntimeError(f"{self.name}: tengely sikertelen ({name})")
        f = self.doc.FeatureByPositionReverse(0)
        f.Name = name
        self.ref_geom.append(f)
        self.doc.ClearSelection2(True)
        return f

    def _henger_lap(self, x, y, z, tol=1e-6):
        """Az a hengeres lap, amelynek felülete átmegy a ponton (m). A koordinátás SelectByID2
        nézetfüggő és néha nem talál; ez a geometriából keres."""
        for body in self.doc.GetBodies2(0, True) or []:
            for f in c0(body, "GetFaces") or []:
                srf = c0(f, "GetSurface")
                if not c0(srf, "IsCylinder"):
                    continue
                ox, oy, oz, ax, ay, az, r = srf.CylinderParams
                vx, vy, vz = x - ox, y - oy, z - oz
                t = vx * ax + vy * ay + vz * az
                d = math.sqrt(max(0.0, vx * vx + vy * vy + vz * vz - t * t))
                if abs(d - r) < tol:
                    return f
        return None

    def point(self, axis, plane, name):
        """Referenciapont tengely és sík metszetében (swRefPointType 6).

        Távolság-illesztéshez pont-sík párt használj: tengely-sík és sík-sík távolság
        párhuzamos geometriánál túlhatároz (hiba 5).
        """
        self.doc.ClearSelection2(True)
        axis.Select2(False, 0)
        plane.Select2(True, 0)
        r = self.fm.InsertReferencePoint(6, 0, 0.0, 1)
        f = [x for x in (r or []) if x is not None]
        if not f:
            raise RuntimeError(f"{self.name}: pont sikertelen")
        f[0].Name = name
        self.ref_geom.append(f[0])
        self.doc.ClearSelection2(True)
        return f[0]

    def sketch(self, plane, draw):
        """Vázlat a síkon; draw(self) rajzol. Utána a vázlat ki van jelölve a következő feature-höz."""
        self.doc.ClearSelection2(True)
        plane.Select2(False, 0)
        self.sm.InsertSketch(True)
        draw(self)
        self.sm.InsertSketch(True)
        self.doc.ClearSelection2(True)
        self.doc.FeatureByPositionReverse(0).Select2(False, 0)

    # --- vázlatelemek (mm) ---------------------------------------------------
    def line(self, x1, y1, x2, y2):
        return self.sm.CreateLine(m(x1), m(y1), 0, m(x2), m(y2), 0)

    def centerline(self, x1, y1, x2, y2):
        return self.sm.CreateCenterLine(m(x1), m(y1), 0, m(x2), m(y2), 0)

    def poly(self, pts):
        n = len(pts)
        for i in range(n):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
            self.line(x1, y1, x2, y2)

    def rect(self, x0, y0, x1, y1):
        self.sm.CreateCornerRectangle(m(x0), m(y0), 0, m(x1), m(y1), 0)

    def crect(self, cx, cy, w, h):
        self.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    def circle(self, x, y, d):
        self.sm.CreateCircleByRadius(m(x), m(y), 0, m(d / 2))

    def arc(self, cx, cy, x1, y1, x2, y2, ccw=True):
        self.sm.CreateArc(m(cx), m(cy), 0, m(x1), m(y1), 0, m(x2), m(y2), 0, 1 if ccw else -1)

    def hexagon(self, x, y, s):
        """Hatszög s laptávolsággal (kulcsnyílás), csúcsok az y tengelyen.

        A `CreatePolygon` második pontja a SolidWorks 2026-ban mindig csúcs, az Inscribed kapcsolótól
        függetlenül (élőben mérve). Ezért a csúcs s/√3 távolságra kerül, nem s/2-re.
        """
        self.sm.CreatePolygon(m(x), m(y), 0, m(x), m(y + s / math.sqrt(3)), 0, 6, True)

    def hexagon_corner(self, x, y, d_corner):
        """Hatszög csúcskör-átmérővel, csúcs a +x tengelyen (préscsap: csúcs = furat + túlfedés)."""
        self.sm.CreatePolygon(m(x), m(y), 0, m(x + d_corner / 2), m(y), 0, 6, False)

    def rrect(self, cx, cy, w, h, r):
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        if r <= 0:
            self.rect(x0, y0, x1, y1)
            return
        self.line(x0 + r, y0, x1 - r, y0)
        self.arc(x1 - r, y0 + r, x1 - r, y0, x1, y0 + r)
        self.line(x1, y0 + r, x1, y1 - r)
        self.arc(x1 - r, y1 - r, x1, y1 - r, x1 - r, y1)
        self.line(x1 - r, y1, x0 + r, y1)
        self.arc(x0 + r, y1 - r, x0 + r, y1, x0, y1 - r)
        self.line(x0, y1 - r, x0, y0 + r)
        self.arc(x0 + r, y0 + r, x0, y0 + r, x0 + r, y0)

    # --- feature-ök ------------------------------------------------------------
    def extrude(self, depth, mid=False, reverse=False, draft=0.0, merge=True):
        f = self.fm.FeatureExtrusion3(
            True, False, reverse, 6 if mid else 0, 0, m(depth), 0.0,
            draft > 0, False, False, False, math.radians(draft), 0.0,
            False, False, False, False, merge, True, True, 0, 0.0, False)
        if f is None:
            raise RuntimeError(f"{self.name}: kihúzás sikertelen")
        return f

    def cut(self, depth=4000.0, mid=True, reverse=False, draft=0.0):
        f = self.fm.FeatureCut4(
            True, False, reverse, 6 if mid else 0, 0, m(depth), 0.0,
            draft > 0, False, False, False, math.radians(draft), 0.0,
            False, False, False, False, False,
            True, True, False, False, False, 0, 0.0, False, False)
        if f is None:
            raise RuntimeError(f"{self.name}: vágás sikertelen")
        return f

    def revolve(self, cut=False):
        f = self.fm.FeatureRevolve2(True, True, False, cut, False, False, 0, 0, 2 * math.pi, 0,
                                    False, False, 0, 0, 0, 0, 0, True, True, True)
        if f is None:
            raise RuntimeError(f"{self.name}: forgatás sikertelen")
        return f

    def revolve_profile(self, pts, cut=False):
        """Forgástest a modell X tengelye körül; pts = [(x, r), ...] zárt profil, r >= 0."""
        def draw(p):
            p.centerline(min(x for x, _ in pts) - 5, 0, max(x for x, _ in pts) + 5, 0)
            p.poly(pts)
        self.sketch(self.front, draw)
        return self.revolve(cut)

    def circle_edges(self, radius_mm, height_mm, axis_index=1):
        """Körélek adott sugárral, adott magasságban (axis_index 1 = Y: felül síkkal párhuzamos körök)."""
        edges = []
        for body in self.doc.GetBodies2(0, True) or []:
            for edge in c0(body, "GetEdges") or []:
                curve = c0(edge, "GetCurve")
                if not c0(curve, "IsCircle"):
                    continue
                p = curve.CircleParams          # cx, cy, cz, ax, ay, az, r
                if abs(p[6] - m(radius_mm)) < 1e-6 and abs(p[axis_index] - m(height_mm)) < 1e-6:
                    edges.append(edge)
        return edges

    def corner_edges(self, pts_mm, tol_mm=0.01):
        """Egyenes élek Z irányban (az elölnézeti vázlat kihúzásának élei) a megadott (x, y) pontokban.

        Kihúzott lemez sarkainak lekerekítéséhez: a vázlat sarokpontjait adod meg, nem kell a
        lekerekítést a vázlatban kiszámolni. Egy ponthoz több él is tartozhat (pl. zseb két oldalon).
        """
        tol = m(tol_mm)
        cel = [(m(x), m(y)) for x, y in pts_mm]
        edges = []
        for body in self.doc.GetBodies2(0, True) or []:
            for edge in c0(body, "GetEdges") or []:
                curve = c0(edge, "GetCurve")
                if not c0(curve, "IsLine"):
                    continue
                p = curve.LineParams          # rootx, rooty, rootz, dirx, diry, dirz
                if abs(p[3]) > 1e-9 or abs(p[4]) > 1e-9:
                    continue
                if any(abs(p[0] - x) < tol and abs(p[1] - y) < tol for x, y in cel):
                    edges.append(edge)
        return edges

    def plane_edges(self, axis_index, value_mm, circle_radii=None, tol_mm=0.01):
        """Élek, amelyek teljesen egy tengelyre merőleges síkban fekszenek (pl. a fedőlap kontúrja).

        axis_index: 0 = X, 1 = Y, 2 = Z; value_mm: a sík helye ezen a tengelyen. Az egyenes élek
        mind benne vannak; a körélek (ívek is) csak akkor, ha a sugaruk a `circle_radii` listában
        van (None = mind). Így a lap külső kontúrja (egyenesek + sarokívek) a furatok nélkül
        kijelölhető, például egy körbefutó lekerekítéshez.
        """
        tol = m(tol_mm)
        sugarak = None if circle_radii is None else [m(r) for r in circle_radii]
        edges = []
        for body in self.doc.GetBodies2(0, True) or []:
            for edge in c0(body, "GetEdges") or []:
                curve = c0(edge, "GetCurve")
                if c0(curve, "IsLine"):
                    p = curve.LineParams
                    if abs(p[axis_index] - m(value_mm)) < tol and abs(p[3 + axis_index]) < 1e-9:
                        edges.append(edge)
                elif c0(curve, "IsCircle"):
                    p = curve.CircleParams
                    if (abs(p[axis_index] - m(value_mm)) < tol and abs(abs(p[3 + axis_index]) - 1) < 1e-9
                            and (sugarak is None or any(abs(p[6] - r) < tol for r in sugarak))):
                        edges.append(edge)
        return edges

    def fillet_edges(self, edges, r_mm, expected):
        """Állandó sugarú lekerekítés pontosan `expected` élen; eltérésnél hibát dob.

        `FeatureFillet(195, r, 0, 0)`: négy argumentum. Üres kijelölésnél a SolidWorks a teljes
        kontúrt kerekítené, ezért a darabszámot előtte ellenőrizzük.
        """
        self.doc.ClearSelection2(True)
        sel = c0(self.doc.SelectionManager, "CreateSelectData")
        picked = sum(1 for e in edges if e.Select4(True, sel))
        if picked != expected:
            self.doc.ClearSelection2(True)
            raise RuntimeError(f"{self.name}: lekerekítéshez {picked} él kijelölve, várt {expected}")
        f = self.fm.FeatureFillet(195, m(r_mm), 0, 0)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: lekerekítés R{r_mm} sikertelen")
        return f

    def chamfer_edges(self, edges, dist_mm, expected):
        """45°-os élletörés pontosan `expected` élen; eltérésnél kihagyja és False-t ad."""
        self.doc.ClearSelection2(True)
        sel = c0(self.doc.SelectionManager, "CreateSelectData")
        picked = sum(1 for e in edges if e.Select4(True, sel))
        if picked != expected:
            print(f"  FIGYELEM: {self.name}: {picked}/{expected} él, élletörés kihagyva")
            self.doc.ClearSelection2(True)
            return False
        self.fm.InsertFeatureChamfer(4, 1, m(dist_mm), math.radians(45), 0, 0, 0, 0)
        self.doc.ClearSelection2(True)
        return True

    # --- lezárás ---------------------------------------------------------------
    def save(self, expect_bodies=1, step=False, stl=False, **properties):
        """Mentés SLDPRT-be (opcionálisan STEP/STL is). Hibát dob, ha a testszám nem a várt."""
        if properties:
            props(self.doc, **properties)
        for g in self.ref_geom:
            g.Select2(False, 0)
            c0(self.doc, "BlankRefGeom")
        self.doc.ClearSelection2(True)
        self.doc.ForceRebuild3(False)
        nb = len(self.doc.GetBodies2(0, True) or [])
        if expect_bodies is not None and nb != expect_bodies:
            raise RuntimeError(f"{self.name}: {nb} test, várt {expect_bodies}")
        self.doc.ShowNamedView2("*Isometric", 7)
        c0(self.doc, "ViewZoomtofit2")
        t0 = time.time() - 2.0
        self.doc.SaveAs3(self.path, 0, 1)
        # Ha egy nyitott összeállítás hivatkozik a fájlra, a SaveAs3 csendben nem ír: a régi fájl marad.
        if not os.path.exists(self.path) or os.path.getmtime(self.path) < t0:
            raise RuntimeError(f"Mentés sikertelen (a fájlt nyitott dokumentum fogja?): {self.path}")
        base = os.path.splitext(self.path)[0]
        if step:
            self.doc.SaveAs3(base + ".STEP", 0, 1)
        if stl:
            self.doc.SaveAs3(base + ".STL", 0, 1)
        print(f"  alkatrész {self.name}: {nb} test")
        sw().CloseDoc(self.name + ".SLDPRT")
        return self.path


# ---------------------------------------------------------------------------
#  Összeállítás
# ---------------------------------------------------------------------------
class Assembly:
    def __init__(self, name, out_dir):
        self.name = name
        self.path = os.path.join(out_dir, name + ".SLDASM")
        os.makedirs(out_dir, exist_ok=True)
        close(name + ".SLDASM")
        self.doc = sw().NewDocument(sw().GetUserPreferenceStringValue(9), 0, 0, 0)
        if self.doc is None:
            raise RuntimeError("Új összeállítás sikertelen")
        self.count = 0

    def _fix(self, c, fixed):
        self.doc.ClearSelection2(True)
        c.Select4(False, nv(), False)
        get_com_member(self.doc, "FixComponent" if fixed else "UnfixComponent")
        self.doc.ClearSelection2(True)

    def add(self, path, R=I3, t=(0, 0, 0), fix=True):
        """Komponens beszúrása R forgatással és t eltolással (mm); alapból rögzítve."""
        c = add_component(self.doc, path, sw=sw())
        if c is None:
            raise RuntimeError(f"Komponens sikertelen: {path}")
        self._fix(c, False)
        c.Transform2 = create_math_transform(sw(), transform_data(R, t))
        if fix:
            self._fix(c, True)
        self.count += 1
        return c

    def component(self, name):
        for c in self.doc.GetComponents(False):
            if c.Name2 == name:
                return c
        raise RuntimeError(f"Nincs ilyen komponens: {name}")

    def entity(self, comp_name, feat_name):
        """Komponens feature-je összeállítás-szintű entitásként. 'elol'/'felul'/'jobb' = alap síkok.

        Alösszeállításon belüli komponens: "Alossz-1/Alkatresz-1".
        """
        c = self.component(comp_name)
        md = c0(c, "GetModelDoc2")
        std = ("elol", "felul", "jobb")
        f = std_planes(md)[std.index(feat_name)] if feat_name in std else md.FeatureByName(feat_name)
        if f is None:
            raise RuntimeError(f"Nincs {feat_name} ebben: {comp_name}")
        return get_assembly_entity(c, f)

    def mate(self, e1, e2, typ, dist_mm=0.0, name=None):
        select_entities_for_mate(self.doc, e1, e2)
        return add_mate5_checked(self.doc, typ, align=2, distance=m(dist_mm), name=name)

    def plane(self, name):
        """Az összeállítás saját alapsíkja: 'elol', 'felul' vagy 'jobb'."""
        return std_planes(self.doc)[("elol", "felul", "jobb").index(name)]

    def lock(self, comp1, comp2, name=None):
        """Merev illesztés (swMateLOCK = 16) két komponens közt a mostani helyzetükben. A mozgó
        részhez kötött kötőelemekhez (csavar, biztosítótárcsa): így együtt mozognak vele."""
        self.doc.ClearSelection2(True)
        self.component(comp1).Select4(False, nv(), False)
        self.component(comp2).Select4(True, nv(), False)
        return add_mate5_checked(self.doc, 16, align=2, name=name)

    def set_driving(self, dim_full_name, value_mm):
        """Hajtó méret (pl. 'D1@Magassag') állítása és újraépítés."""
        p = self.doc.Parameter(dim_full_name)
        if p is None:
            raise RuntimeError(f"Nincs ilyen méret: {dim_full_name}")
        p.SystemValue = m(value_mm)
        self.doc.EditRebuild3()

    def save(self):
        self.doc.ForceRebuild3(False)
        self.doc.ShowNamedView2("*Isometric", 7)
        c0(self.doc, "ViewZoomtofit2")
        self.doc.SaveAs3(self.path, 0, 1)
        if not os.path.exists(self.path):
            raise RuntimeError(f"Mentés sikertelen: {self.path}")
        print(f"  összeállítás {self.name}: {self.count} komponens")
        return self.path
