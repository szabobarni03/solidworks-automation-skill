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

    def plane_pn(self, p, n, name=None):
        """Sík a `p` ponton át (mm), `n` normálissal: ferde síkokhoz (szögben álló fül, ferde furat).

        Egy 3D vázlatban `p`-ből `n` irányú segédvonal készül, a sík erre merőleges és átmegy a
        kezdőpontján (InsertRefPlane: merőleges 2 + egybeeső 4). A vázlat x/y iránya ilyen síkon a
        SolidWorks döntése: a vázlatba modellkoordinátából a `to_sketch` számol át.
        """
        L = math.sqrt(sum(c * c for c in n))
        q = [p[i] + 10 * n[i] / L for i in range(3)]
        self.doc.ClearSelection2(True)
        self.sm.Insert3DSketch(True)
        ln = self.sm.CreateLine(m(p[0]), m(p[1]), m(p[2]), m(q[0]), m(q[1]), m(q[2]))
        self.sm.Insert3DSketch(True)
        vazlat = self.doc.FeatureByPositionReverse(0)
        self.doc.ClearSelection2(True)
        sm = self.doc.SelectionManager
        d0, d1 = c0(sm, "CreateSelectData"), c0(sm, "CreateSelectData")
        d0.Mark, d1.Mark = 0, 1            # az InsertRefPlane a hivatkozásokat Mark szerint olvassa
        ln.Select4(False, d0)
        c0(ln, "GetStartPoint2").Select4(True, d1)
        pl = self.fm.InsertRefPlane(2, 0, 4, 0, 0, 0)
        self.doc.ClearSelection2(True)
        if pl is None:
            raise RuntimeError(f"{self.name}: sík (pont + normális) sikertelen")
        if name:
            pl.Name = name
        vazlat.Select2(False, 0)
        c0(self.doc, "BlankSketch")
        self.doc.ClearSelection2(True)
        self.ref_geom.append(pl)
        return pl

    def to_sketch(self, x, y, z=0.0):
        """Modellpont (mm) -> az éppen nyitott vázlat (x, y) koordinátái (mm). Rajzoló függvényben
        használd ferde vagy eltolt síkon, ahol a vázlattengelyek iránya nem nyilvánvaló."""
        tr = c0(self.sm.ActiveSketch, "ModelToSketchTransform")
        mu = c0(sw(), "GetMathUtility")
        if hasattr(mu, "_FlagAsMethod"):
            mu._FlagAsMethod("CreatePoint")
        pt = mu.CreatePoint(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [m(x), m(y), m(z)]))
        d = c0(pt.MultiplyTransform(tr), "ArrayData")
        return d[0] * 1000.0, d[1] * 1000.0

    def plane_map(self, o, U, W):
        """Síkbeli (u, w) koordináta -> vázlat (x, y), a nyitott vázlatban. o: a sík egy pontja,
        U és W: két merőleges egységvektor a síkban (modell, mm). Visszaad (f, ccw): f(u, w) a
        vázlatpont, ccw pedig az `arc` irányjelzője, ami (u, w)-ben pozitív körüljárást ad (a
        vázlat tükrözve is állhat a síkhoz képest)."""
        def f(u, w):
            return self.to_sketch(*[o[i] + u * U[i] + w * W[i] for i in range(3)])
        a, b, c = f(0, 0), f(1, 0), f(0, 1)
        ccw = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0
        return f, ccw

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
        """Vázlat a síkon; draw(self) rajzol. Utána a vázlat ki van jelölve a következő feature-höz.
        Visszaadja a vázlat feature-t (sweephez profil és pálya)."""
        self.doc.ClearSelection2(True)
        plane.Select2(False, 0)
        self.sm.InsertSketch(True)
        draw(self)
        self.sm.InsertSketch(True)
        self.doc.ClearSelection2(True)
        f = self.doc.FeatureByPositionReverse(0)
        f.Select2(False, 0)
        return f

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

    def fillet_path(self, pts, r):
        """Nyitott töröttvonal a belső csúcsokban r sugarú érintő ívekkel (sweep pályája, hajlított
        lemez vagy huzal középvonala). A csúcsok a lekerekítés nélküli metszéspontok; az ív a
        vázlatban számolt érintési pontok közé kerül, így nem kell SketchFillet."""
        n = len(pts)
        ki = [pts[0]]                         # szakaszonként a kezdő- és végpont
        ivek = []
        for i in range(1, n - 1):
            (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
            l1, l2 = math.hypot(x1 - x0, y1 - y0), math.hypot(x2 - x1, y2 - y1)
            u = ((x1 - x0) / l1, (y1 - y0) / l1)
            v = ((x2 - x1) / l2, (y2 - y1) / l2)
            kereszt = u[0] * v[1] - u[1] * v[0]
            th = abs(math.atan2(kereszt, u[0] * v[0] + u[1] * v[1]))
            t = r * math.tan(th / 2)
            a = (x1 - u[0] * t, y1 - u[1] * t)
            b = (x1 + v[0] * t, y1 + v[1] * t)
            sg = 1 if kereszt > 0 else -1     # balra fordul: a középpont a bal oldalon
            c = (a[0] - u[1] * r * sg, a[1] + u[0] * r * sg)
            ki.append(a)
            ivek.append((c, a, b, kereszt > 0))
            ki.append(b)
        ki.append(pts[-1])
        for i in range(0, len(ki), 2):
            self.line(*ki[i], *ki[i + 1])
        for c, a, b, ccw in ivek:
            self.arc(*c, *a, *b, ccw=ccw)

    def slot(self, x1, y1, x2, y2, w):
        """Egyenes hosszú horony (két félkör végű): a két ívközéppont (x1, y1) és (x2, y2), szélesség w.
        A teljes hossz = a középpontok távolsága + w."""
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * w / 2, dx / L * w / 2          # normális félszélességnyi hosszal
        self.line(x1 + nx, y1 + ny, x2 + nx, y2 + ny)
        self.arc(x2, y2, x2 + nx, y2 + ny, x2 - nx, y2 - ny, ccw=False)
        self.line(x2 - nx, y2 - ny, x1 - nx, y1 - ny)
        self.arc(x1, y1, x1 - nx, y1 - ny, x1 + nx, y1 + ny, ccw=False)

    def circle_hull(self, centers, r):
        """Egyforma sugarú körök konvex burka (fülekkel lekerekített sokszög, pl. háromszög alakú
        talp a furatok körül). centers: a középpontok pozitív (óramutatóval ellentétes) sorrendben,
        konvex sokszöget alkotva; a köríveket a szomszédos élek külső érintői zárják."""
        n = len(centers)
        ki = []                                   # élenként a két érintési pont
        for i in range(n):
            (x1, y1), (x2, y2) = centers[i], centers[(i + 1) % n]
            L = math.hypot(x2 - x1, y2 - y1)
            nx, ny = (y2 - y1) / L * r, -(x2 - x1) / L * r     # kifelé mutató normális
            ki.append(((x1 + nx, y1 + ny), (x2 + nx, y2 + ny)))
        for i in range(n):
            a, b = ki[i]
            self.line(*a, *b)
            c = centers[(i + 1) % n]
            self.arc(c[0], c[1], *b, *ki[(i + 1) % n][0], ccw=True)

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

    def circular_pattern(self, features, axis, count, angle_deg=360.0):
        """Körminta: a `features` feature-ök `count` példányban, egyenletesen az `angle_deg` szögön.

        axis: referenciatengely feature (pl. `self.axis(...)` eredménye). A minta feature-ök 4-es,
        a tengely 1-es jelöléssel kerül a kijelölésbe (`FeatureCircularPattern4`). Hatszög vagy
        csillag alakú test oldalain ismétlődő furatcsoporthoz: egy oldalt kell megépíteni.
        """
        self.doc.ClearSelection2(True)
        for f in features:
            if not f.Select2(True, 4):
                raise RuntimeError(f"{self.name}: a minta feature nem jelölhető ki: {f.Name}")
        if not axis.Select2(True, 1):
            raise RuntimeError(f"{self.name}: a minta tengelye nem jelölhető ki")
        f = self.fm.FeatureCircularPattern4(int(count), math.radians(angle_deg), False, "", False, True, False)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: körminta sikertelen")
        return f

    def cbore_holes(self, face_plane, points, d_mm, cbore_d_mm, cbore_depth_mm, reverse=False):
        """Süllyesztett furatok egy furatlistából: Ø d átmenő furat és Ø cbore_d x cbore_depth
        süllyesztés a `face_plane` síkjáról (a lap síkja, pl. `plane(front, vastagság)`).
        Egy pontlista hajtja mindkét vágást, így a furat és a süllyesztése nem válik el egymástól.
        A süllyesztés vakvágása az alap iránnyal (reverse=False) megy az anyagba a felső lap
        síkjáról (élőben ellenőrizve); reverse=True kifelé vágna, és a vágás sikertelen.
        A Hole Wizard (`HoleWizard5`) helyett: annak Value1..12 paraméterei furattípusonként mást
        jelentenek, és saját vázlatpontot kér."""
        self.sketch(face_plane, lambda s: [s.circle(x, y, d_mm) for x, y in points])
        a = self.cut()
        self.sketch(face_plane, lambda s: [s.circle(x, y, cbore_d_mm) for x, y in points])
        b = self.cut(cbore_depth_mm, mid=False, reverse=reverse)
        return a, b

    def linear_pattern(self, features, direction, count, spacing_mm, flip=False):
        """Lineáris minta: a `features` `count` példányban, `spacing_mm` osztással a `direction`
        mentén (referenciatengely vagy egyenes él). A feature-ök 4-es, az irány 1-es jelöléssel
        kerül a kijelölésbe (`FeatureLinearPattern5`). Ha a minta a test mellé kerülne (rossz irány),
        flip=True. A darabszámot az osztásból és a hosszból számold, ne rögzítsd.
        """
        self.doc.ClearSelection2(True)
        for f in features:
            if not f.Select2(True, 4):
                raise RuntimeError(f"{self.name}: a minta feature nem jelölhető ki: {f.Name}")
        if not direction.Select2(True, 1):
            raise RuntimeError(f"{self.name}: a minta iránya nem jelölhető ki")
        f = self.fm.FeatureLinearPattern5(int(count), m(spacing_mm), 1, 0.0, flip, False, "", "",
                                          False, False, False, False, False, False, False, False,
                                          False, False, 0.0, 0.0, False, False)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: lineáris minta sikertelen")
        return f

    def mirror(self, features, plane):
        """Feature-ök tükrözése síkra (`InsertMirrorFeature2`): a feature-ök 1-es, a sík (referenciasík
        vagy sík lap) 2-es jelöléssel kerül a kijelölésbe. Kettős tükrözéshez (két szimmetriasík)
        hívd kétszer: másodszor az eredeti és az első tükörkép feature-ökkel."""
        self.doc.ClearSelection2(True)
        for f in features:
            if not f.Select2(True, 1):
                raise RuntimeError(f"{self.name}: a tükrözendő feature nem jelölhető ki: {f.Name}")
        if not plane.Select2(True, 2):
            raise RuntimeError(f"{self.name}: a tükörsík nem jelölhető ki")
        f = self.fm.InsertMirrorFeature2(False, False, False, False, 0)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: tükrözés sikertelen")
        return f

    def loft(self, profiles, merge=True):
        """Loft (átmenet) a `profiles` vázlatok között, a lista sorrendjében
        (`InsertProtrusionBlend2`, profilok 1-es jelöléssel). A profilokat egymással szemben álló,
        párhuzamos síkokra rajzold, a sarkokat azonos körüljárással, mert a loft a vázlatpontokat
        a kijelölés helye szerint párosítja. Sík lapra futó loftnál a lap helyén is vázlat legyen."""
        self.doc.ClearSelection2(True)
        for i, pr in enumerate(profiles):
            if not pr.Select2(i > 0, 1):
                raise RuntimeError(f"{self.name}: a loft profilja nem jelölhető ki")
        f = self.fm.InsertProtrusionBlend2(False, True, False, 1.0, 0, 0, 1.0, 1.0, True, True,
                                           False, 0.0, 0.0, 0, merge, True, True, 0)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: loft sikertelen")
        return f

    def sweep(self, profile, path):
        """Sweep (kihúzás pálya mentén): `profile` zárt vázlat (pl. két koncentrikus kör = cső),
        `path` nyitott vázlat (egyenesek és érintő ívek). A profil síkja a pálya kezdőpontján legyen,
        a pályára merőlegesen. Kijelölés: profil 1-es, pálya 4-es jelöléssel
        (`InsertProtrusionSwept4`)."""
        self.doc.ClearSelection2(True)
        if not (profile.Select2(False, 1) and path.Select2(True, 4)):
            raise RuntimeError(f"{self.name}: sweep profil/pálya nem jelölhető ki")
        f = self.fm.InsertProtrusionSwept4(False, False, 0, False, False, 0, 0, False, 0.0, 0.0, 0, 0,
                                           True, True, True, 0.0, True, False, 0.0, 0)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: sweep sikertelen")
        return f

    def shell(self, faces, thickness_mm, outward=False):
        """Héj (Shell): a `faces` lapok nyitva maradnak, a falvastagság befelé `thickness_mm`
        (outward=True: kifelé; akkor a modell méretei a belső méretek).
        A lapokat geometriából keresd (`plane_faces`), ne koordinátás kijelöléssel.
        Az `InsertFeatureShell` nem ad vissza semmit: a létrejöttét a fa utolsó eleme mutatja."""
        self.doc.ClearSelection2(True)
        sel = c0(self.doc.SelectionManager, "CreateSelectData")
        if sum(1 for f in faces if f.Select4(True, sel)) != len(faces):
            raise RuntimeError(f"{self.name}: héj lapjai nem jelölhetők ki")
        n0 = c0(self.doc, "GetFeatureCount")
        self.doc.InsertFeatureShell(m(thickness_mm), outward)
        self.doc.ClearSelection2(True)
        if c0(self.doc, "GetFeatureCount") <= n0:
            raise RuntimeError(f"{self.name}: héj sikertelen")
        return self.doc.FeatureByPositionReverse(0)

    def sheet_metal_base_flange(self, sketch, thickness_mm, radius_mm, depth_mm, k_factor, flip_thicken=False):
        """Lemezalkatrész alapperem nyitott vázlatból (pl. L-profil a külső mérettel). A vázlat
        vonala a lemez egyik oldala; flip_thicken a SW alapértelmezett vastagítási oldalát fordítja
        (az origóba futó L-vázlatnál az alap befelé vastagít, a vázlat így a külső méret). radius_mm: belső hajlítási sugár, depth_mm: a lemez szélessége
        (vakon, a vázlatsík egyik oldalára). Ellenőrzés: `flat_size()`.

        Az `InsertSheetMetalBaseFlange2` elavult, SW 2026-ban None-t ad: helyette
        `CreateDefinition(swFmBaseFlange = 34)` + `CreateFeature`. A K-tényezőt sem az alapperem,
        sem a Sheet-Metal feature adata nem veszi át (a beállítás csendben elveszik, vagy tárolódik,
        de a kiterítés nem változik). Ami hat: a hajlítás-alfeature-ök (`SketchBend`) definíciója,
        `UseDefaultBendAllowance = False` + `SetCustomBendAllowance` + `ModifyDefinition`."""
        self.doc.ClearSelection2(True)
        data = self.fm.CreateDefinition(34)          # swFmBaseFlange
        data.Thickness = m(thickness_mm)
        data.BendRadius = m(radius_mm)
        data.D1EndConditionType = 0                  # swEndCondBlind
        data.D1EndConditionDistance = m(depth_mm)
        if flip_thicken:                             # a SW alapértelmezett oldalához képest
            data.ReverseThickness = not data.ReverseThickness
        sketch.Select2(False, 0)
        f = self.fm.CreateFeature(data)
        self.doc.ClearSelection2(True)
        if f is None:
            raise RuntimeError(f"{self.name}: lemez alapperem sikertelen")
        sub = c0(f, "GetFirstSubFeature")
        while sub is not None:
            if c0(sub, "GetTypeName2") == "SketchBend":
                od = c0(sub, "GetDefinition")
                od.AccessSelections(self.doc, nv())
                od.UseDefaultBendAllowance = False
                ba = c0(od, "GetCustomBendAllowance")
                ba.Type = 2                          # swBendAllowanceKFactor
                ba.KFactor = k_factor
                od.SetCustomBendAllowance(ba)
                if not sub.ModifyDefinition(od, self.doc, nv()):
                    raise RuntimeError(f"{self.name}: K-tényező beállítása sikertelen ({sub.Name})")
            sub = c0(sub, "GetNextSubFeature")
        self.doc.ForceRebuild3(False)
        return f

    def flat_size(self):
        """A lemezalkatrész kiterített befoglaló mérete (mm, nagyság szerint rendezve): a
        `Flat-Pattern` (FlatPattern típusú) feature elnyomását feloldja, méri, majd visszanyomja."""
        fp = None
        f = c0(self.doc, "FirstFeature")
        while f is not None:
            if c0(f, "GetTypeName2") == "FlatPattern":
                fp = f
            f = c0(f, "GetNextFeature")
        if fp is None:
            raise RuntimeError(f"{self.name}: nincs kiterítés (FlatPattern) feature")
        fp.SetSuppression2(1, 2, None)   # feloldás (swUnSuppressFeature), ebben a konfigurációban
        self.doc.ForceRebuild3(False)
        try:
            b = self.doc.GetBodies2(0, True)[0].GetBodyBox()
            meret = sorted(round((b[3 + i] - b[i]) * 1000, 3) for i in range(3))
        finally:
            fp.SetSuppression2(0, 2, None)
            self.doc.ForceRebuild3(False)
        return meret

    def revolve(self, cut=False, angle_deg=360.0, reverse=False, mid=False):
        """Forgatás a vázlat középvonala körül. angle_deg < 360: részleges (reverse: a másik
        irányba, mid: a vázlatsíktól szimmetrikusan, swEndCondMidPlane = 6)."""
        f = self.fm.FeatureRevolve2(True, True, False, cut, reverse, False, 6 if mid else 0, 0,
                                    math.radians(angle_deg), 0,
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

    def line_edges(self, axis_index, pts_mm, tol_mm=0.01):
        """Egyenes élek a megadott tengely irányában (0 = X, 1 = Y, 2 = Z), a megadott pontokon át.

        pts_mm: a másik két koordináta párjai növekvő tengelysorrendben (X tengelynél (y, z),
        Y-nál (x, z), Z-nél (x, y)). A `corner_edges` általánosítása, például egy alulról
        kimart lépcső belső élének lekerekítéséhez.
        """
        tol = m(tol_mm)
        masik = [i for i in range(3) if i != axis_index]
        cel = [(m(a), m(b)) for a, b in pts_mm]
        edges = []
        for body in self.doc.GetBodies2(0, True) or []:
            for edge in c0(body, "GetEdges") or []:
                curve = c0(edge, "GetCurve")
                if not c0(curve, "IsLine"):
                    continue
                p = curve.LineParams          # rootx, rooty, rootz, dirx, diry, dirz
                if any(abs(p[3 + i]) > 1e-9 for i in masik):
                    continue
                if any(abs(p[masik[0]] - a) < tol and abs(p[masik[1]] - b) < tol for a, b in cel):
                    edges.append(edge)
        return edges

    def edges_at(self, pts_mm, tol_mm=0.01):
        """Élek (bármilyen görbe), amelyek a megadott modellpontok (mm) valamelyikén átmennek.
        Ferde éleknél, metszésgörbéknél, ahol a tengelyirányú keresők (`corner_edges`,
        `line_edges`) nem használhatók. Élenként egy pont elég, a végpontok helyett a közepéből."""
        tol = m(tol_mm)
        cel = [tuple(m(v) for v in p) for p in pts_mm]
        edges = []
        for body in self.doc.GetBodies2(0, True) or []:
            for edge in c0(body, "GetEdges") or []:
                for p in cel:
                    q = edge.GetClosestPointOn(*p)
                    if q and math.dist(p, q[:3]) < tol:
                        edges.append(edge)
                        break
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

    def plane_faces(self, axis_index, value_mm=None, tol_mm=0.01):
        """Sík lapok, amelyek normálisa a megadott tengellyel párhuzamos (0 = X, 1 = Y, 2 = Z);
        value_mm esetén csak az ezen a koordinátán fekvők. Megmunkált lapok színezéséhez."""
        out = []
        for body in self.doc.GetBodies2(0, True) or []:
            for f in c0(body, "GetFaces") or []:
                srf = c0(f, "GetSurface")
                if not c0(srf, "IsPlane"):
                    continue
                p = srf.PlaneParams              # nx, ny, nz, px, py, pz
                if abs(abs(p[axis_index]) - 1) > 1e-9:
                    continue
                if value_mm is None or abs(p[3 + axis_index] - m(value_mm)) < m(tol_mm):
                    out.append(f)
        return out

    def cylinder_faces(self, axis_index=None, radii=None, exclude_radii=(), tol_mm=0.01):
        """Hengeres lapok (furat, csap, csonk). axis_index: csak a tengellyel párhuzamosak;
        radii: csak ezek a sugarak (mm); exclude_radii: ezek nélkül (pl. a sarok-lekerekítések)."""
        tol = m(tol_mm)
        out = []
        for body in self.doc.GetBodies2(0, True) or []:
            for f in c0(body, "GetFaces") or []:
                srf = c0(f, "GetSurface")
                if not c0(srf, "IsCylinder"):
                    continue
                p = srf.CylinderParams           # ox, oy, oz, ax, ay, az, r
                if axis_index is not None and abs(abs(p[3 + axis_index]) - 1) > 1e-9:
                    continue
                if radii is not None and not any(abs(p[6] - m(r)) < tol for r in radii):
                    continue
                if any(abs(p[6] - m(r)) < tol for r in exclude_radii):
                    continue
                out.append(f)
        return out

    def faces_in_box(self, lo_mm, hi_mm, tol_mm=0.01):
        """Lapok, amelyek befoglaló doboza teljesen a (lo, hi) dobozon belül van (mm, modellkoordináta).
        Zseb vagy horony összes lapjához (fenék, fal, lekerekítés), pl. külön színhez: a doboz a zseb
        térfogata, a test külső lapjai kilógnak belőle."""
        tol = m(tol_mm)
        lo = [m(v) - tol for v in lo_mm]
        hi = [m(v) + tol for v in hi_mm]
        out = []
        for body in self.doc.GetBodies2(0, True) or []:
            for f in c0(body, "GetFaces") or []:
                b = f.GetBox
                b = b() if callable(b) else b
                if all(lo[i] <= b[i] and b[3 + i] <= hi[i] for i in range(3)):
                    out.append(f)
        return out

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
        c0(self.doc, "EditRebuild3")      # pywin32: néha property-ként jön (bool), nem hívható

    def save(self):
        self.doc.ForceRebuild3(False)
        self.doc.ShowNamedView2("*Isometric", 7)
        c0(self.doc, "ViewZoomtofit2")
        self.doc.SaveAs3(self.path, 0, 1)
        if not os.path.exists(self.path):
            raise RuntimeError(f"Mentés sikertelen: {self.path}")
        print(f"  összeállítás {self.name}: {self.count} komponens")
        return self.path
