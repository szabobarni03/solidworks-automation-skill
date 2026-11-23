"""Tesztalkatrész-készlet kiértékelése: a kérésekből (eval/esetek.json) épített alkatrészek mérése és
összevetése a várt értékekkel. A sikerarányból látszik, hogy egy skill-változás javított vagy rontott.

A várt értékek analitikusan számoltak (testszám, térfogat, befoglaló méret). A befoglaló méretet
nagyság szerint rendezve hasonlítjuk, így az alkatrész tájolása (melyik alapsíkon készült) nem számít.

Futtatás (futó SolidWorks kell):
    python eval_ellenor.py <eredmeny_mappa> [--elozo elozo_eredmeny.json]
A mappában az alkatrészek neve az eset azonosítója: <id>.SLDPRT. Az eredmény az
<eredmeny_mappa>/eval_eredmeny.json fájlba kerül.
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

ESETEK = Path(__file__).resolve().parents[1] / "eval" / "esetek.json"


def betolt(path=ESETEK):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ertekel(meres, elvart, tures):
    """Egy eset értékelése. meres: {"testek", "terfogat_mm3", "meret_mm"} vagy None (nincs fájl).
    Visszaad: {"ok": bool, "hibak": [str, ...]}."""
    if meres is None:
        return {"ok": False, "hibak": ["hiányzik az alkatrész"]}
    hibak = []
    if meres["testek"] != elvart["testek"]:
        hibak.append(f"testszám {meres['testek']}, várt {elvart['testek']}")
    v, ve = meres["terfogat_mm3"], elvart["terfogat_mm3"]
    if v is None or abs(v - ve) > tures["terfogat_rel"] * ve:
        hibak.append(f"térfogat {v} mm3, várt {ve} mm3")
    mm = sorted(meres["meret_mm"] or [])
    me = sorted(elvart["meret_mm"])
    if len(mm) != 3 or any(abs(a - b) > tures["meret_mm"] for a, b in zip(mm, me)):
        hibak.append(f"befoglaló {mm} mm, várt {me} mm")
    return {"ok": not hibak, "hibak": hibak}


def osszegez(eredmenyek):
    """Sikerarány és a sikertelen esetek listája."""
    n = len(eredmenyek)
    jo = sum(1 for e in eredmenyek.values() if e["ok"])
    return {"sikeres": jo, "osszes": n, "arany": round(jo / n, 3) if n else 0.0,
            "sikertelen": sorted(k for k, e in eredmenyek.items() if not e["ok"])}


def osszehasonlit(most, elozo):
    """Esetenként: javult / romlott, az előző futás eredmény-JSON-jához képest."""
    valt = {}
    for k, e in most.items():
        r = elozo.get(k)
        if r is not None and r["ok"] != e["ok"]:
            valt[k] = "javult" if e["ok"] else "romlott"
    return valt


def meres(path):
    """Az alkatrész mérése SolidWorksben (megnyitás, part_report, bezárás)."""
    if not os.path.exists(path):
        return None
    from swk import open_doc, sw          # SolidWorks csak itt kell
    from ellenorzes import part_report
    d = open_doc(path)
    try:
        r = part_report(d)
    finally:
        sw().CloseDoc(os.path.basename(path))
    return {"testek": r["bodies"], "terfogat_mm3": r["volume_mm3"], "meret_mm": r["size_mm"]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("mappa")
    ap.add_argument("--elozo")
    a = ap.parse_args()
    cfg = betolt()
    eredmenyek = {}
    for eset in cfg["esetek"]:
        m = meres(os.path.join(a.mappa, eset["id"] + ".SLDPRT"))
        eredmenyek[eset["id"]] = {**ertekel(m, eset["elvart"], cfg["tures"]), "meres": m}
        e = eredmenyek[eset["id"]]
        print(f"{'OK  ' if e['ok'] else 'HIBA'} {eset['id']:18s} {'; '.join(e['hibak'])}")
    ossz = osszegez(eredmenyek)
    print(f"sikerarány: {ossz['sikeres']}/{ossz['osszes']} ({ossz['arany']:.0%})")
    ki = {"datum": datetime.datetime.now().isoformat(timespec="seconds"), "osszegzes": ossz,
          "esetek": eredmenyek}
    if a.elozo:
        with open(a.elozo, encoding="utf-8") as f:
            ki["valtozas"] = osszehasonlit(eredmenyek, json.load(f)["esetek"])
        for k, v in ki["valtozas"].items():
            print(f"  {k}: {v}")
    with open(os.path.join(a.mappa, "eval_eredmeny.json"), "w", encoding="utf-8") as f:
        json.dump(ki, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
