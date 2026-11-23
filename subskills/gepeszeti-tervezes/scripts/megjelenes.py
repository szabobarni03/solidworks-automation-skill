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
    return os.path.join(c0(sw(), "GetExecutablePath"), "data", "graphics", "Materials")   # = telepítési mappa


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


def rgb_szin(rgb):
    """(R, G, B) 0..255 -> a RenderMaterial.PrimaryColor egész értéke (COLORREF: R + G·256 + B·65536)."""
    r, g, b = (int(round(v)) for v in rgb)
    return r + 256 * g + 65536 * b


def alkatresz(doc, mat, szin=None):
    """RealView-megjelenés egy alkatrész összes testére (alkatrész szinten, a 3D képekhez és a
    rajzhoz). Az összeállítás-szintű `alkalmaz` felülírhatja. szin: (R, G, B) 0..255, a megjelenés
    alapszíne helyett (pl. festett felület a rajz 3D képének árnyalatában)."""
    _hozzaad(doc, mat, doc.GetBodies2(0, True) or [], szin)


def lapok(doc, faces, mat, szin=None):
    """RealView-megjelenés kijelölt lapokra (pl. a festett test megmunkált lapjai fémesek).
    A lap szintű megjelenés erősebb a test szintűnél, ezért a sorrend mindegy."""
    if not faces:
        raise ValueError(f"Nincs lap a megjelenéshez: {mat}")
    _hozzaad(doc, mat, faces, szin)


def _hozzaad(doc, mat, entitasok, szin=None):
    import pythoncom
    from win32com.client import VARIANT

    ext = doc.Extension
    rm = ext.CreateRenderMaterial(_p2m(mat))
    if rm is None:
        raise RuntimeError(f"Megjelenés nem tölthető: {mat}")
    if szin is not None:
        rm.PrimaryColor = rgb_szin(szin)
    for e in entitasok:
        rm.AddEntity(e)
    e1 = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    e2 = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    if not ext.AddDisplayStateSpecificRenderMaterial(rm, 1, VARIANT(pythoncom.VT_DISPATCH, None), e1, e2):
        raise RuntimeError(f"Megjelenés hozzáadása sikertelen: {mat}")


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


ARNYEKOLT_ELEKKEL = 5      # swViewDisplayMode_ShadedWithEdges


def elekkel(doc, be=True):
    """Árnyékolt nézet élekkel (be) vagy élek nélkül. A műhelyrajzok 3D képei (Inventor) így
    renderelnek: a fekete élkontúr nélkül a modell laposabb és kevésbé hasonlít a referenciára.
    A dokumentumba mentve megmarad, megnyitáskor is így látszik."""
    c0(doc, "ViewDisplayShaded")
    if be:
        doc.ActiveView.DisplayMode = ARNYEKOLT_ELEKKEL


def nezet_kep(out, ay_fok=0.0, ax_fok=0.0, alap="*Isometric", elrejt=(), doc=None, elek=True, forgatas=()):
    """Kép az aktív dokumentumról egyedi nézőszögből (PNG/JPG a kiterjesztés szerint).

    alap: szabványnézet neve (`*Front`, `*Left`, `*Isometric` ...), ebből forgat először az Y
    képernyőtengely körül `ay_fok`-kal, aztán az X körül `ax_fok`-kal. elrejt: komponens-névelőtagok,
    amelyek a kép idejére rejtve vannak (pl. burkolat, hogy a belső rész látsszon).
    elek: árnyékolt nézet fekete élekkel (mint a rajzok 3D képei), lásd `elekkel`.
    forgatas: további forgatások sorban, [("x" | "y", fok), ...] a képernyő tengelyei körül, az
    `ay_fok`/`ax_fok` után. Pl. Z tengelyű forgástest a rajzhoz hasonlóan függőlegesen:
    `alap="*Front", forgatas=[("x", -90), ("y", 45), ("x", 30)]`.
    """
    d = doc or sw().ActiveDoc
    rejtett = []
    if elrejt and c0(d, "GetType") == 2:
        for c in d.GetComponents(False):
            if c.Visible and any(c.Name2.startswith(p) for p in elrejt):
                c.Visible = 0
                rejtett.append(c)
    try:
        _nezet(d, alap, [("y", ay_fok), ("x", ax_fok), *forgatas], elek)
        c0(d, "GraphicsRedraw2")
        d.SaveAs3(out, 0, 2)
    finally:
        for c in rejtett:
            c.Visible = 1
    if not os.path.exists(out):
        raise RuntimeError(f"Kép mentése sikertelen: {out}")
    return out


def _nezet(d, alap, forgatas, elek=True):
    """Nézet beállítása: szabványnézet, forgatások sorban a képernyő tengelyei körül, nagyítás."""
    elekkel(d, elek)
    d.Extension.SetUserPreferenceToggle(198, 0, True)   # swViewDisplayHideAllTypes
    d.ShowNamedView2(alap, SZABVANY_NEZET.get(alap, -1))   # az azonosító nyelvfüggetlen
    v = d.ActiveView
    for tengely, fok in forgatas:
        if not fok:
            continue
        if tengely == "x":
            v.RotateAboutCenter(math.radians(fok), 0.0)
        else:
            v.RotateAboutCenter(0.0, math.radians(fok))
    c0(d, "ViewZoomtofit2")
    d.ClearSelection2(True)


def mozgas_kepkockak(out_dir, beallit, ertekek, doc=None, alap="*Isometric", forgatas=(), metszet=None,
                     prefix="kocka"):
    """Mozgásvideó képkockái: a nézetet egyszer állítja be (így a kép nem ugrál), aztán minden
    értékre meghívja a `beallit(v)`-t (pl. a hajtó illesztés értéke + újraépítés), és PNG-t ment.

    metszet: (sík, eltolás_mm), sík = 'elol'/'felul'/'jobb': metszetnézet az egész sorozatra, hogy
    a belső mozgás (dugattyú, hajtórúd) látsszon. Kimenet: <out_dir>/<prefix>_000.png ...
    Utána: `video(os.path.join(out_dir, prefix + "_%03d.png"), "mozgas.mp4")`.
    """
    d = doc or sw().ActiveDoc
    os.makedirs(out_dir, exist_ok=True)
    mvm = None
    beallit(ertekek[0])
    if metszet:
        from swk import m, std_planes
        mvm = c0(d, "ModelViewManager")
        sd = c0(mvm, "CreateSectionViewData")
        sd.FirstPlane = std_planes(d)[("elol", "felul", "jobb").index(metszet[0])]
        sd.FirstOffset = m(metszet[1])
        sd.ShowSectionCap = True
        sd.KeepCapColor = False
        if not mvm.CreateSectionView(sd):
            raise RuntimeError("Metszetnézet sikertelen")
    kepek = []
    try:
        _nezet(d, alap, forgatas)
        for i, v in enumerate(ertekek):
            beallit(v)
            c0(d, "GraphicsRedraw2")
            out = os.path.join(out_dir, f"{prefix}_{i:03d}.png")
            d.SaveAs3(out, 0, 2)
            if not os.path.exists(out):
                raise RuntimeError(f"Kép mentése sikertelen: {out}")
            kepek.append(out)
    finally:
        if mvm is not None:
            c0(mvm, "RemoveSectionView")
    return kepek


def tartalom_doboz(kepek, hatter_kuszob=200, telitettseg=40, margo=20):
    """A képsorozat közös tartalomdoboza (x0, y0, x1, y1): ami nem a világos, szürke SolidWorks-
    háttér (minden csatorna >= hatter_kuszob és kis telítettség). Az összes kocka uniója, hogy a
    mozgó rész egyik kockán se lógjon ki; margo képpont ráhagyással."""
    from PIL import Image, ImageChops
    doboz = None
    for f in kepek:
        im = Image.open(f).convert("RGB")
        r, g, b = im.split()
        sotet = Image.eval(ImageChops.darker(ImageChops.darker(r, g), b), lambda v: 255 if v < hatter_kuszob else 0)
        szines = Image.eval(ImageChops.subtract(ImageChops.lighter(ImageChops.lighter(r, g), b),
                                                ImageChops.darker(ImageChops.darker(r, g), b)),
                            lambda v: 255 if v > telitettseg else 0)
        bb = ImageChops.lighter(sotet, szines).getbbox()
        if bb:
            doboz = bb if doboz is None else (min(doboz[0], bb[0]), min(doboz[1], bb[1]),
                                               max(doboz[2], bb[2]), max(doboz[3], bb[3]))
    if doboz is None:
        return None
    w, h = Image.open(kepek[0]).size
    return (max(0, doboz[0] - margo), max(0, doboz[1] - margo), min(w, doboz[2] + margo), min(h, doboz[3] + margo))


def video(kepek_minta, out, fps=24, vag=True):
    """Képsorozatból MP4 (H.264, yuv420p: telefonon és böngészőben is lejátszható) ffmpeg-gel.
    kepek_minta: ffmpeg minta, pl. `.../kocka_%03d.png`. vag: az üres háttér levágása a közös
    tartalomdobozra (`tartalom_doboz`). A páratlan képméretet párosra vágja."""
    import glob
    import shutil
    import subprocess
    exe = shutil.which("ffmpeg")
    if exe is None:
        raise RuntimeError("Nincs ffmpeg a PATH-on (Windows: winget install Gyan.FFmpeg)")
    szuro = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if vag:
        bb = tartalom_doboz(sorted(glob.glob(kepek_minta.replace("%03d", "[0-9][0-9][0-9]"))))
        if bb:
            szuro = f"crop={bb[2] - bb[0]}:{bb[3] - bb[1]}:{bb[0]}:{bb[1]}," + szuro
    subprocess.run([exe, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", kepek_minta,
                    "-vf", szuro, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                   check=True)
    return out


def szogkereses(out_dir, szogek, alap="*Isometric", elrejt=(), prefix="szog"):
    """Több nézőszögből renderel (szogek = [(ay, ax), ...]); a fájlnév tartalmazza a szöget.
    Utána: `osszevetes.racs(kepek, ...)`, és a referenciához legközelebbi szöget választod."""
    os.makedirs(out_dir, exist_ok=True)
    return [nezet_kep(os.path.join(out_dir, f"{prefix}_{ay:g}_{ax:g}.png"), ay, ax, alap, elrejt)
            for ay, ax in szogek]


def alkatresz_osszevetes(part_path, ref_png, fo_crop, iso_crop, out_dir, alap="*Front", iso_alap="*Isometric",
                         iso_forgatas=()):
    """Egy alkatrész összevetése a rajzával: a rajz fő nézete és 3D képe a SolidWorks fő nézete és
    izometrikus RealView-képe mellett, egy rácsban. Kimenet: <out_dir>/<név>_osszevetes.png

    fo_crop, iso_crop: (x0, y0, x1, y1) kivágás a rajz PNG-jéből (a fő nézet és a 3D kép).
    alap: a SolidWorks szabványnézet, amely a rajz fő nézetének felel meg (`*Front`, `*Top` ...).
    iso_alap, iso_forgatas: a 3D kép nézőiránya, ha a rajz 3D képe nem a SolidWorks izometrikus
    irányából néz (pl. függőleges tengelyű forgástest), lásd `nezet_kep` `forgatas`.
    A dokumentumot a végén bezárja, hogy a következő alkatrész építését ne zavarja.
    """
    import osszevetes
    from swk import open_doc
    nev = os.path.splitext(os.path.basename(part_path))[0]
    d = open_doc(part_path)
    try:
        realview(d)
        f = nezet_kep(os.path.join(out_dir, f"{nev}_sw_fo.png"), alap=alap, doc=d)
        i = nezet_kep(os.path.join(out_dir, f"{nev}_sw_iso.png"), alap=iso_alap, doc=d, forgatas=iso_forgatas)
    finally:
        sw().CloseDoc(os.path.basename(c0(d, "GetPathName")))
    a = osszevetes.egymas_mellett(ref_png, f, os.path.join(out_dir, f"{nev}_fo.png"), crop=fo_crop,
                                  cimkek=("Rajz", "SolidWorks"), magassag=700)
    b = osszevetes.egymas_mellett(ref_png, i, os.path.join(out_dir, f"{nev}_iso.png"), crop=iso_crop,
                                  cimkek=("Rajz 3D", "SolidWorks RealView"), magassag=700)
    return osszevetes.racs([a, b], os.path.join(out_dir, f"{nev}_osszevetes.png"), szelesseg=800)
