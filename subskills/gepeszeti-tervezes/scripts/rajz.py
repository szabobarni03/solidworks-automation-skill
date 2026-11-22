"""Rajzkészítés COM-on: lap méretaránnyal, nézetek, darabjegyzék, tételszámok, metszet, törött nézet,
forgástest-méretezés átmérőkkel és illesztésekkel, középvonal, megjegyzés, PDF/PNG kimenet.

Minden itt lévő megoldás egy hibán át lett kipróbálva; a docstring írja le, mi nem működött.
Pozíciók mm-ben a lap bal alsó sarkától.
"""
import os

import pythoncom
from win32com.client import VARIANT

from swk import c0, m, nv, sw


# ---------------------------------------------------------------------------
#  Lap és nézetek
# ---------------------------------------------------------------------------
def new_drawing(sheet_format, size_code, w_mm, h_mm, s1, s2):
    """Új rajz lapkerettel és s1:s2 méretaránnyal.

    A SetupSheet5 a méretarányt nem veszi át: utána az aktuális lapot újra le kell kérni és
    SetScale-lel beállítani. size_code: swDwgPaperSizes_e (pl. 8 = A3, 10 = A1).
    """
    tpl = sw().GetUserPreferenceStringValue(10)
    d = sw().NewDocument(tpl, size_code, m(w_mm), m(h_mm))
    if d is None:
        raise RuntimeError("Új rajz sikertelen")
    sheet = c0(d, "GetCurrentSheet")
    d.SetupSheet5(c0(sheet, "GetName"), size_code, 12, s1, s2, True, sheet_format,
                  m(w_mm), m(h_mm), "Standard", True)
    c0(d, "GetCurrentSheet").SetScale(s1, s2, True, False)
    return d


def sheet_scale(d):
    """(s1, s2) az aktuális lapról. A GetProperties2 property (tuple), nem metódus."""
    bp = list(c0(d, "GetCurrentSheet").GetProperties2)
    return (bp[2], bp[3])


def view(d, model_path, view_name, x_mm, y_mm, scale=None):
    """Modellnézet. A nézet a lap méretarányát sem mindig veszi át: scale-t mindig add meg explicit.

    view_name a felület nyelvén: német SW-ben "*Vorderseite", "*Oben", "*Links", "*Isometrisch".
    Az első nézet beszúrása a LAP méretarányát is átírja (automatikus méretarány; 1:2-ből 2:1 lett),
    ezért a lap méretarányát előtte kiolvassuk és utána visszaállítjuk.
    """
    s1, s2 = sheet_scale(d)
    v = d.CreateDrawViewFromModelView3(model_path, view_name, m(x_mm), m(y_mm), 0)
    if v is None:
        raise RuntimeError(f"Nézet sikertelen: {view_name}")
    if sheet_scale(d) != (s1, s2):
        c0(d, "GetCurrentSheet").SetScale(s1, s2, True, False)
    if scale is not None:
        v.UseSheetScale = False
        v.ScaleDecimal = float(scale)
    return v


def move_view(v, x_mm, y_mm):
    v.Position = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [m(x_mm), m(y_mm)])


def select_view(d, v):
    d.ClearSelection2(True)
    d.ActivateView(c0(v, "GetName2"))
    d.Extension.SelectByID2(c0(v, "GetName2"), "DRAWINGVIEW", 0, 0, 0, False, 0, nv(), 0)


def save_drawing(d, path_no_ext, pdf=True):
    """SLDDRW + PDF mentés; visszaadja a PDF útvonalát (vagy None)."""
    d.ForceRebuild3(False)
    d.SaveAs3(path_no_ext + ".SLDDRW", 0, 1)
    if not pdf:
        return None
    out = path_no_ext + ".pdf"
    d.SaveAs3(out, 0, 1)
    if not os.path.exists(out):
        raise RuntimeError(f"PDF mentés sikertelen: {out}")
    return out


# ---------------------------------------------------------------------------
#  Darabjegyzék, tételszám, metszet
# ---------------------------------------------------------------------------
def set_table_text(tab, row, col, text):
    """ITableAnnotation.Text(row, col) írása (paraméteres property, pywin32-ből csak Invoke-kal)."""
    dispid = tab._oleobj_.GetIDsOfNames("Text")
    tab._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, 0, row, col, text)


def bom(d, v, template, x_right_mm, y_top_mm, extra_props=(), description_prop=None):
    """Darabjegyzék a nézethez, jobb felső sarka (x, y)-on.

    extra_props: egyéni tulajdonságok új oszlopként a végére (InsertColumn2(4, n-1, ...)).
    Az Anchored=False nélkül a SetPosition2 nem mozdítja a táblát.
    """
    t = v.InsertBomTable4(True, m(x_right_mm), m(y_top_mm), 2, 1, "Standard", template, False, 0, False)
    if t is None:
        raise RuntimeError("Darabjegyzék sikertelen")
    bta = (c0(c0(t, "BomFeature"), "GetTableAnnotations") or [None])[0]
    if description_prop:
        for c in range(c0(bta, "ColumnCount")):
            if bta.Text(0, c).lower().startswith(("beschreib", "descr")):
                bta.SetColumnCustomProperty(c, description_prop)
    for p in extra_props:
        n = c0(bta, "ColumnCount")
        bta.InsertColumn2(4, n - 1, p.upper(), 0)
        if not bta.SetColumnCustomProperty(n, p):
            print("  oszlop-tulajdonság nem állt be:", p)
    try:
        bta.Anchored = False
    except Exception as exc:
        print("  horgony:", exc)
    c0(bta, "GetAnnotation").SetPosition2(m(x_right_mm), m(y_top_mm), 0)
    return bta


def balloons(d, v):
    """Automatikus tételszámok a nézet körül (téglalap elrendezés, kör, tételszám)."""
    select_view(d, v)
    opt = c0(d, "CreateAutoBalloonOptions")
    opt.Layout = 1
    opt.IgnoreMultiple = True
    opt.InsertMagneticLine = True
    opt.Style = 1
    opt.Size = 2
    opt.UpperTextContent = 1
    res = d.AutoBalloon5(opt)
    d.ClearSelection2(True)
    return len(res) if res else 0


def section_horizontal(d, v, x_mm, y_mm, label="A", y_frac=0.5, margin_mm=8.0):
    """Vízszintes metszővonal a nézet magasságának y_frac részénél, metszet (x, y)-ra.

    Aktív nézet vázlatkoordinátája = (lapkoordináta - nézetpozíció) / nézet méretarány.
    """
    d.ActivateView(c0(v, "GetName2"))
    out, pos, sc = v.GetOutline, v.Position, v.ScaleDecimal
    ys = (out[1] + (out[3] - out[1]) * y_frac - pos[1]) / sc
    x0 = (out[0] - m(margin_mm) - pos[0]) / sc
    x1 = (out[2] + m(margin_mm) - pos[0]) / sc
    d.ClearSelection2(True)
    line = d.SketchManager.CreateLine(x1, ys, 0, x0, ys, 0)
    line.Select4(False, nv())
    sv = d.CreateSectionViewAt5(m(x_mm), m(y_mm), 0, label, 0, None, 0)
    if sv is None:
        raise RuntimeError("Metszet sikertelen")
    return sv


# ---------------------------------------------------------------------------
#  Törött (megszakított) nézet hosszú tengelyhez
# ---------------------------------------------------------------------------
def broken_view(d, v, model_x0, model_x1, break_from, break_to, gap_style=1, line_style=3):
    """Vízszintes törés a modell X [break_from, break_to] tartományán.

    Feltételek, különben InsertBreak2 None-t ad: a nézet 1:1 (ScaleDecimal = 1), és a pozíciók
    a nézet KÖZEPÉHEZ mért eltolások méterben. A modell X tartománya [model_x0, model_x1].
    A törés csak a nézet kijelölése után a d.BreakView()-val lép életbe.
    """
    mid = (model_x0 + model_x1) / 2
    d.ClearSelection2(True)
    if v.InsertBreak2(0, m(break_from - mid), m(break_to - mid), gap_style, line_style) is None:
        raise RuntimeError("Törésvonal sikertelen (nézet 1:1? eltolás a nézetközéphez?)")
    select_view(d, v)
    d.BreakView()
    d.ClearSelection2(True)


# ---------------------------------------------------------------------------
#  Forgástest vázlat-méretezése (alkatrészben, a rajz előtt)
# ---------------------------------------------------------------------------
def first_sketch(model, type_name="ProfileFeature"):
    f = c0(model, "FirstFeature")
    while f is not None:
        if c0(f, "GetTypeName2") == type_name:
            return f
        f = c0(f, "GetNextFeature")
    raise RuntimeError("Nincs vázlat")


def delete_sketch_dims(model, sketch_feat):
    """Vázlat összes méretének törlése. Select3(True, nv()) nem jelöl; annotation Select2(True, 0) igen."""
    dims = []
    dd = c0(sketch_feat, "GetFirstDisplayDimension")
    while dd is not None:
        dims.append(dd)
        dd = sketch_feat.GetNextDisplayDimension(dd)
    model.ClearSelection2(True)
    for dd in dims:
        c0(dd, "GetAnnotation").Select2(True, 0)
    if dims:
        model.EditDelete()
    return len(dims)


def radial_to_diameter(sketch_feat, fits=None, texts=None):
    """Forgásvázlat sugár-méreteit (AddDimension2 ezt adja, Type2 = 5) átmérőnek mutatja.

    - A Diametric=True csak a vázlatból kilépés UTÁN, a feature-ből lekért méreten hat.
    - Az értéket az átkapcsolás ELŐTT kell olvasni (akkor még sugár).
    fits: {átmérő_mm: "h7"} -> csak tűrésosztály (tol.Type = 8, swTolFIT).
    texts: {átmérő_mm: "Tr 24x5"} -> az érték helyett szöveg (menetjelölés).
    """
    fits, texts = fits or {}, texts or {}
    n = 0
    dd = c0(sketch_feat, "GetFirstDisplayDimension")
    while dd is not None:
        if c0(dd, "Type2") == 5:
            dm = round(dd.GetDimension2(0).SystemValue * 2000, 3)
            dd.Diametric = True
            key = int(dm) if float(dm).is_integer() else dm
            if key in fits:
                tol = dd.GetDimension2(0).Tolerance
                tol.Type = 8
                tol.SetFitValues("", fits[key])
            if key in texts:
                dd.ShowDimensionValue = False
                dd.SetText(1, texts[key])
            n += 1
        dd = sketch_feat.GetNextDisplayDimension(dd)
    return n


def set_precision(dd, decimals=None, tol_decimals=3):
    """Tizedesjegyek: egész értéknél 0, egyébként 1; illesztéses méretnél a tűrés 3 jegy."""
    v = dd.GetDimension2(0).SystemValue * 1000
    p = decimals if decimals is not None else (0 if float(round(v, 3)).is_integer() else 1)
    pt = tol_decimals if c0(dd.GetDimension2(0).Tolerance, "Type") else p
    dd.SetPrecision3(p, p, pt, pt)


# ---------------------------------------------------------------------------
#  Lapvázlat, megjegyzés
# ---------------------------------------------------------------------------
def sheet_centerline(d, x0_mm, y_mm, x1_mm):
    """Középvonal a LAPON. A lapvázlat a lap méretarányával skálázott: k = s2/s1 szorzó kell.

    A GetOutline a törés előtti körvonalat adja, ezért a végpontokat a törött kontúrból számold.
    """
    s1, s2 = sheet_scale(d)
    k = s2 / s1
    d.ActivateSheet(c0(c0(d, "GetCurrentSheet"), "GetName"))
    line = d.SketchManager.CreateCenterLine(m(x0_mm) * k, m(y_mm) * k, 0, m(x1_mm) * k, m(y_mm) * k, 0)
    d.ClearSelection2(True)
    return line


def note(d, text, x_mm, y_mm):
    """Megjegyzés mutatóvonal nélkül: ha van kijelölés, a jegyzet nyilat kap, ezért előtte ürítünk."""
    d.ClearSelection2(True)
    n = d.InsertNote(text)
    if n is not None:
        c0(n, "GetAnnotation").SetPosition2(m(x_mm), m(y_mm), 0)
    return n


# ---------------------------------------------------------------------------
#  Ellenőrzéshez: PDF -> PNG
# ---------------------------------------------------------------------------
def pdf_to_png(pdf_path, png_path=None, dpi=110, page=0):
    """A PDF egy oldalát PNG-be rendereli (PyMuPDF), hogy a rajzot képként át lehessen nézni."""
    import pymupdf
    png_path = png_path or os.path.splitext(pdf_path)[0] + ".png"
    with pymupdf.open(pdf_path) as doc:
        doc[page].get_pixmap(dpi=dpi).save(png_path)
    return png_path


