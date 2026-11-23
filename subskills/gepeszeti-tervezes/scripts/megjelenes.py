"""RealView-megjelenések összeállítás-komponensekre és nézőszög-képek a referenciakép-összevetéshez.

Kipróbálva: SolidWorks 2026. Buktatók, amelyeket ez a modul kezel:
- Az összeállítás-szintű megjelenés az `AddDisplayStateSpecificRenderMaterial` hívással megy.
  A 0-s opció ("minden konfiguráció") False-t ad; az 1-es (ez a megjelenítési állapot) működik.
- Az összeállítás-szintű megjelenés felülírja az alkatrész lapszíneit. A többszínű alkatrészeket
  (pl. ahol egy lap külön színt kapott) hagyd ki a szabályokból.
- `ViewDisplayRealView` állítható, `ViewDisplayAmbientOcclusion` COM-ból nem (hibát ad, elnyeljük).
- A referencia-jelölők (síkok, tengelyek, origók) a képen ⊕ jelként látszanak: a 198-as
  felhasználói kapcsolóval (swViewDisplayHideAllTypes) mind elrejthető.
- Egyedi nézőszög: `ShowNamedView2` egy szabványnézetre, majd `ActiveView.RotateAboutCenter`.
  A forgatás előjele a nézettől függ, ezért több szögből renderelj, és `osszevetes.racs` rácsban
  válaszd ki a referenciához legközelebbit.

A szabályok: [(névelőtag, megjelenés), ...], az első egyező nyer. A megjelenés lehet abszolút .p2m
útvonal, vagy a SolidWorks `data/graphics/Materials` mappájához relatív (pl. "metal/steel/machined steel.p2m").
"""
import math
import os

from swk import c0, sw

SZABVANY_NEZET = {"*Front": 1, "*Back": 2, "*Left": 3, "*Right": 4, "*Top": 5, "*Bottom": 6,
                  "*Isometric": 7, "*Trimetric": 8, "*Dimetric": 9}   # swStandardViews_e

def csoportosit(nevek, szabalyok):
    """{megjelenés: [név, ...]} az első egyező névelőtag szerint; ami nem egyezik, kimarad."""
    out = {}
    for n in nevek:
        for elotag, mat in szabalyok:
            if n.startswith(elotag):
                out.setdefault(mat, []).append(n)
                break
    return out


def materials_dir():
    """A SolidWorks telepítés megjelenés-könyvtára (data/graphics/Materials)."""
    return os.path.join(os.path.dirname(sw().GetExecutablePath()), "data", "graphics", "Materials")


def _p2m(mat):
    p = mat if os.path.isabs(mat) else os.path.join(materials_dir(), *mat.split("/"))
    if not os.path.exists(p):
        raise FileNotFoundError(f"Nincs ilyen megjelenés: {p}")
    return p


def alkalmaz(doc, szabalyok):
    """Összeállítás-szintű RealView-megjelenések a komponensekre. Visszaadja a kapott komponensek számát."""
    import pythoncom
    from win32com.client import VARIANT

    ext = doc.Extension
    komp = {c.Name2: c for c in doc.GetComponents(False)}
    n = 0
    for mat, nevek in csoportosit(list(komp), szabalyok).items():
        rm = ext.CreateRenderMaterial(_p2m(mat))
        if rm is None:
            raise RuntimeError(f"Megjelenés nem tölthető: {mat}")
        for nev in nevek:
            rm.AddEntity(komp[nev])
        e1 = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        e2 = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        if not ext.AddDisplayStateSpecificRenderMaterial(rm, 1, VARIANT(pythoncom.VT_DISPATCH, None), e1, e2):
            raise RuntimeError(f"Megjelenés hozzáadása sikertelen: {mat}")
        n += len(nevek)
        print(f"  {os.path.basename(mat)}: {len(nevek)} komponens", flush=True)
    return n


def realview(doc, be=True):
    """RealView (és ha lehet, árnyék) be/ki. Az ambient occlusion COM-ból nem állítható."""
    ext = doc.Extension
    try:
        ext.ViewDisplayRealView = be
    except Exception as e:  # noqa: BLE001 - régebbi verzió / grafikus kártya nélkül
        print(f"  RealView: {e}", flush=True)
    try:
        doc.ViewDisplayShadows = be
    except Exception:  # noqa: BLE001
        pass
    c0(doc, "GraphicsRedraw2")


def nezet_kep(out, ay_fok=0.0, ax_fok=0.0, alap="*Isometric", elrejt=(), doc=None):
    """Kép az aktív dokumentumról egyedi nézőszögből (PNG/JPG a kiterjesztés szerint).

    alap: szabványnézet neve (`*Front`, `*Left`, `*Isometric` ...), ebből forgat először az Y
    képernyőtengely körül `ay_fok`-kal, aztán az X körül `ax_fok`-kal. elrejt: komponens-névelőtagok,
    amelyek a kép idejére rejtve vannak (pl. burkolat, hogy a belső rész látsszon).
    """
    d = doc or sw().ActiveDoc
    rejtett = []
    if elrejt and c0(d, "GetType") == 2:
        for c in d.GetComponents(False):
            if c.Visible and any(c.Name2.startswith(p) for p in elrejt):
                c.Visible = 0
                rejtett.append(c)
    try:
        c0(d, "ViewDisplayShaded")
        d.Extension.SetUserPreferenceToggle(198, 0, True)   # swViewDisplayHideAllTypes
        d.ShowNamedView2(alap, SZABVANY_NEZET.get(alap, -1))   # az azonosító nyelvfüggetlen
        v = d.ActiveView
        if ay_fok:
            v.RotateAboutCenter(0.0, math.radians(ay_fok))
        if ax_fok:
            v.RotateAboutCenter(math.radians(ax_fok), 0.0)
        c0(d, "ViewZoomtofit2")
        d.ClearSelection2(True)
        c0(d, "GraphicsRedraw2")
        d.SaveAs3(out, 0, 2)
    finally:
        for c in rejtett:
            c.Visible = 1
    if not os.path.exists(out):
        raise RuntimeError(f"Kép mentése sikertelen: {out}")
    return out


def szogkereses(out_dir, szogek, alap="*Isometric", elrejt=(), prefix="szog"):
    """Több nézőszögből renderel (szogek = [(ay, ax), ...]); a fájlnév tartalmazza a szöget.
    Utána: `osszevetes.racs(kepek, ...)`, és a referenciához legközelebbi szöget választod."""
    os.makedirs(out_dir, exist_ok=True)
    return [nezet_kep(os.path.join(out_dir, f"{prefix}_{ay:g}_{ax:g}.png"), ay, ax, alap, elrejt)
            for ay, ax in szogek]
