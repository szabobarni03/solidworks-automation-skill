"""gepeszeti-tervezes élő smoke-teszt (futó SolidWorks kell).

Épít egy lapot furattal és élletöréssel, egy hatszögletű préscsapot, összeállítja őket elforgatva,
visszaméri a furat helyét, ütközést vizsgál (6 tétel: hatszögcsúcsonként egy pressz-térfogat), majd rajzot készít
1:2 méretaránnyal, PDF-et és PNG-t ment.

Futtatás:
    venv\\Scripts\\python.exe tests\\gepeszeti_tervezes_live_smoke.py [kimeneti_mappa] [lapkeret.slddrt]
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "subskills" / "gepeszeti-tervezes" / "scripts"))

import ellenorzes  # noqa: E402
import rajz  # noqa: E402
import step_elemzes  # noqa: E402
from swk import Assembly, Part, close, sw  # noqa: E402
from transzform import apply, axes  # noqa: E402

HOLE = (10.0, 8.0, 3.2)          # x, y (felül sík vázlat), átmérő
PLATE_T = 5.0
PIN_CORNER = 3.35                # csúcskör: 0,15 túlfedés


def build_plate(out):
    p = Part("smoke_lap", out)
    p.sketch(p.top, lambda s: s.rect(0, 0, 40, 30))
    p.extrude(PLATE_T)
    p.sketch(p.top, lambda s: s.circle(HOLE[0], HOLE[1], HOLE[2]))
    p.cut(40, mid=True)
    ok = p.chamfer_edges(p.circle_edges(HOLE[2] / 2, PLATE_T), 0.4, expected=1)
    rep = ellenorzes.part_report(p.doc)
    p.save(expect_bodies=1, step=True, stl=True)
    return p.path, rep, ok


def build_pin(out):
    p = Part("smoke_csap", out)
    p.sketch(p.top, lambda s: s.hexagon_corner(0, 0, PIN_CORNER))
    p.extrude(4.0)
    p.save(expect_bodies=1)
    return p.path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    out = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="gt_smoke_")
    fmt = sys.argv[2] if len(sys.argv) > 2 else \
        r"C:\ProgramData\SolidWorks\SOLIDWORKS 2026\lang\german\sheetformat\a3 - din.slddrt"
    res = {"out": out}

    plate, res["plate"], res["chamfer_ok"] = build_plate(out)
    pin = build_pin(out)

    # Lap elforgatva: lokális X -> világ Z, lokális Y -> világ X
    R = axes((0, 0, 1), (1, 0, 0))
    t = (20.0, -5.0, 7.0)
    a = Assembly("smoke_ossz", out)
    cp = a.add(plate, R, t)
    a.add(pin, R, apply(R, t, (HOLE[0], 1.0, -HOLE[1])))
    a.save()

    want = apply(R, t, (HOLE[0], 0.0, -HOLE[1]))
    got = step_elemzes.cylinder_holes(cp, normal="y")
    res["hole_expected"] = [round(v, 3) for v in want]
    res["holes_measured"] = got
    res["hole_ok"] = len(got) == 1 and all(abs(g - w) < 0.01 for g, w in zip(got[0][:3], want)) \
        and abs(got[0][3] - HOLE[2]) < 0.01

    res["interference"] = ellenorzes.interference_report(a.doc, subassemblies_as_components=False, expected=6)  # hatszögcsúcsonként 1 tétel
    res["images"] = ellenorzes.render_views(os.path.join(out, "review"), "smoke", focus_prefix="smoke_csap",
                                            views={"izo": 7})

    d = rajz.new_drawing(fmt, 8, 420, 297, 1, 2)
    v = rajz.view(d, plate, "*Oben", 150, 150, scale=0.5)
    rajz.note(d, "Smoke-teszt", 30, 40)
    res["sheet_scale"] = rajz.sheet_scale(d)
    res["view_scale"] = v.ScaleDecimal
    pdf = rajz.save_drawing(d, os.path.join(out, "smoke_rajz"))
    res["png"] = rajz.pdf_to_png(pdf)

    res["ok"] = bool(res["plate"]["ok"] and res["chamfer_ok"] and res["hole_ok"]
                     and res["interference"]["ok"] and tuple(res["sheet_scale"]) == (1.0, 2.0)
                     and abs(res["view_scale"] - 0.5) < 1e-9 and os.path.exists(res["png"]))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    for title in ("smoke_rajz.SLDDRW", "smoke_ossz.SLDASM", "smoke_lap.SLDPRT", "smoke_csap.SLDPRT"):
        close(title)
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
