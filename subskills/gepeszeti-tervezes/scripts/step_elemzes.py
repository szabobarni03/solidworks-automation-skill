"""Vásárolt/átvett STEP modell importja és mérése: furatok (hengerfelületek) és alkatrész-befoglalók.

Cél: a ráépülő alkatrész minden kapcsolódó méretét a modellből olvasni, ne fotóról becsülni.

Futtatás:
    python step_elemzes.py import <step> <kimeneti_mappa> <név>
    python step_elemzes.py elemez <kimeneti_json> [--normal z] [--body-filter Board]
(az elemzés a SolidWorks aktív dokumentumán fut)
"""
import argparse
import json
import os
import sys
from collections import Counter

from swk import byref_int, c0, sw

AXIS = {"x": 3, "y": 4, "z": 5}       # CylinderParams: [px, py, pz, ax, ay, az, r]


def import_step(step_path, out_dir, name):
    """STEP betöltése és mentése natív formátumba. Több testű STEP összeállítás lesz (.SLDASM)."""
    err = byref_int()
    doc = sw().LoadFile4(step_path, "r", sw().GetImportFileData(step_path), err)
    if doc is None:
        raise RuntimeError(f"STEP import sikertelen (hiba {err.value}): {step_path}")
    os.makedirs(out_dir, exist_ok=True)
    ext = ".SLDASM" if c0(doc, "GetType") == 2 else ".SLDPRT"
    path = os.path.join(out_dir, name + ext)
    doc.SaveAs3(path, 0, 1 | 2)
    return doc, path


def _to_world(T, p):
    """Pont a komponens Transform2.ArrayData-jával (sorvektor-konvenció)."""
    return tuple(p[0] * T[0 + j] + p[1] * T[3 + j] + p[2] * T[6 + j] + T[9 + j] for j in range(3))


def cylinder_holes(component, normal="z"):
    """Hengerfelületek, amelyek tengelye a komponens SAJÁT `normal` tengelyével párhuzamos.

    Eredmény: [(x, y, z, átmérő)] mm, összeállítás-koordinátában. A tengelypontot előbb a saját
    normális menti 0-ra vetítjük (a furatfal több felülete különböző tengelypontot adhat), utána
    transzformáljuk. Így egy furat egy sor.
    """
    ax = AXIS[normal]
    T = component.Transform2.ArrayData
    holes = Counter()
    for b in component.GetBodies2(0) or []:
        for f in c0(b, "GetFaces") or []:
            s = c0(f, "GetSurface")
            if not c0(s, "IsCylinder"):
                continue
            p = s.CylinderParams
            if abs(abs(p[ax]) - 1) > 1e-6:
                continue
            local = list(p[:3])
            local[ax - 3] = 0.0
            w = _to_world(T, local)
            key = tuple(round(v * 1000, 3) for v in w) + (round(p[6] * 2000, 3),)
            holes[key] += 1
    return sorted(holes)


def analyse_active(normal="z", body_filter=None):
    """Aktív összeállítás: furatok a levélkomponensekből (body_filter névrész szerint), és a legfelső
    szintű komponensek befoglaló dobozai [xmin, ymin, zmin, xmax, ymax, zmax] mm-ben.

    Alösszeállítás-komponensen a GetBodies2 None: a furatokat a levél alkatrészből kell olvasni.
    Egyes exportok (pl. "fabricated" NYÁK-STEP) nem tartalmaznak furatot - ezt jelezni kell.
    """
    d = sw().ActiveDoc
    if d is None:
        raise RuntimeError("Nincs aktív dokumentum")
    comps, holes = [], []
    if c0(d, "GetType") != 2:
        raise RuntimeError("Az aktív dokumentum nem összeállítás")
    for c in d.GetComponents(False):
        parts = c.Name2.split("/")
        if len(parts) == 2:
            box = c.GetBox(False, False)
            comps.append([parts[1], [round(v * 1000, 3) for v in box] if box else None])
        leaf = not c.GetChildren
        if leaf and (body_filter is None or body_filter in c.Name2):
            holes.extend(cylinder_holes(c, normal))
    return {"holes": sorted(set(holes)), "comps": comps,
            "hole_diameters": dict(Counter(h[3] for h in holes))}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("import")
    a.add_argument("step")
    a.add_argument("out_dir")
    a.add_argument("name")
    e = sub.add_parser("elemez")
    e.add_argument("json_out")
    e.add_argument("--normal", default="z", choices=list(AXIS))
    e.add_argument("--body-filter")
    args = ap.parse_args()
    if args.cmd == "import":
        _, path = import_step(args.step, args.out_dir, args.name)
        print("mentve:", path)
    else:
        res = analyse_active(args.normal, args.body_filter)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(f"furatok: {len(res['holes'])}  átmérők: {res['hole_diameters']}  komponensek: {len(res['comps'])}")
        if not res["holes"]:
            print("FIGYELEM: nincs furat a modellben - más STEP-export kell (pl. fúrásokkal).")


if __name__ == "__main__":
    main()
