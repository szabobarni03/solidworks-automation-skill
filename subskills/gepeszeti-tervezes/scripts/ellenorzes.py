"""Kötelező ellenőrzések átadás előtt: alkatrész (testszám, térfogat, befoglaló), összeállítás ütközés,
képek. Az eredmény JSON-ba megy, hogy a döntés visszakereshető legyen.

Futtatás (aktív dokumentumon):
    python ellenorzes.py alkatresz [json]
    python ellenorzes.py utkozes <json> [--expected 24] [--no-subasm]
    python ellenorzes.py kepek <kimeneti_mappa> [--focus komponensnév-előtag]
"""
import argparse
import json
import os
import sys
from pathlib import Path

from swk import c0, nv, sw  # a swk import a szülő scripts mappát is felveszi a sys.path-ra

from sw_measure import inspect_interference  # noqa: E402

VIEWS = {"alul": 6, "izo": 7, "elol": 1, "felul": 5}   # swStandardViews_e


def _tomeg_g(doc):
    """Tömeg grammban a hozzárendelt anyag sűrűségével.

    Buktató: a `CreateMassProperty` objektum 1 kg/m³ sűrűséggel számol (a Mass = Volume), az anyagot
    figyelmen kívül hagyja. A `GetMassProperties2` a valódi anyaggal számol: [.., 3] térfogat, [5] tömeg.
    """
    import pythoncom
    from win32com.client import VARIANT
    st = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    r = doc.Extension.GetMassProperties2(1, st, False)
    return round(r[5] * 1000, 2) if r else None


def part_report(doc=None):
    """Testszám, térfogat (mm³) és befoglaló méretek (mm). Nyomtatáshoz 1 zárt test kell."""
    d = doc or sw().ActiveDoc
    bodies = d.GetBodies2(0, True) or []
    mp = c0(d.Extension, "CreateMassProperty")
    box = d.GetPartBox(True)
    size = [round((box[i + 3] - box[i]) * 1000, 2) for i in range(3)] if box else None
    return {"bodies": len(bodies), "volume_mm3": round(mp.Volume * 1e9, 1) if mp else None,
            "mass_g": _tomeg_g(d),
            "size_mm": size, "ok": len(bodies) == 1}


def interference_report(asm=None, subassemblies_as_components=True, expected=None):
    """Ütközésvizsgálat összefoglalóval.

    subassemblies_as_components=True: importált (pl. STEP) alösszeállítás egy egységként számít, így a
    belső alkatrészei egymással nem adnak hamis találatot. Saját mechanizmusnál False, hogy a
    részegységek közti ütközés is látsszon.
    expected: a szándékos pressz-illesztések várt száma; eltérésnél ok = False.
    """
    a = asm or sw().ActiveDoc
    res = inspect_interference(a, treat_subassemblies_as_components=subassemblies_as_components)
    items = [{"volume_mm3": round(it.get("volume_mm3") or 0, 4),
              "components": [c["name"] for c in it["components"]]} for it in res.get("items", [])]
    n = res.get("interference_count")
    ok = (n == 0) if expected is None else (n == expected)
    return {"count": n, "expected": expected, "ok": ok, "errors": res.get("errors"), "items": items}


def render_views(out_dir, prefix, focus_prefix=None, views=VIEWS):
    """Szabványnézetek PNG-be; focus_prefix esetén a megfelelő komponensre nagyít."""
    d = sw().ActiveDoc
    os.makedirs(out_dir, exist_ok=True)
    target = None
    if focus_prefix and c0(d, "GetType") == 2:
        target = next((c for c in d.GetComponents(True) if c.Name2.startswith(focus_prefix)), None)
    out = []
    for name, code in views.items():
        d.ShowNamedView2("", code)
        d.ClearSelection2(True)
        if target is not None:
            target.Select4(False, nv(), False)
            c0(d, "ViewZoomToSelection")
            d.ClearSelection2(True)
        else:
            c0(d, "ViewZoomtofit2")
        c0(d, "GraphicsRedraw2")
        path = os.path.join(out_dir, f"{prefix}_{name}.png")
        d.SaveAs3(path, 0, 2)
        out.append(path)
    return out


def _dump(res, path):
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1, default=str)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("alkatresz")
    p.add_argument("json_out", nargs="?")
    u = sub.add_parser("utkozes")
    u.add_argument("json_out")
    u.add_argument("--expected", type=int)
    u.add_argument("--no-subasm", action="store_true")
    k = sub.add_parser("kepek")
    k.add_argument("out_dir")
    k.add_argument("--prefix", default="nezet")
    k.add_argument("--focus")
    args = ap.parse_args()
    if args.cmd == "alkatresz":
        res = part_report()
        _dump(res, args.json_out)
        print(res)
    elif args.cmd == "utkozes":
        res = interference_report(subassemblies_as_components=not args.no_subasm, expected=args.expected)
        _dump(res, args.json_out)
        print(f"ütközés: {res['count']} (várt {res['expected']}) ok={res['ok']} {res['errors'] or ''}")
        for it in res["items"]:
            print(f"  {it['volume_mm3']:9.4f} mm3  " + " <-> ".join(it["components"]))
    else:
        for path in render_views(args.out_dir, args.prefix, args.focus):
            print(path, os.path.exists(path))


if __name__ == "__main__":
    main()
