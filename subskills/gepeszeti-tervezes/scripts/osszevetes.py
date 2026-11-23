"""Referenciakép és SolidWorks-kép összevetése (tiszta PIL, SolidWorks nélkül is fut és tesztelhető).

Miért kell: egy képről vagy rajzról modellezett alkatrész könnyen "nagyjából jó" a modellezőnek, de
messze van a céltól. Ha az összevetés csak a projekt végén történik, minden alkatrészt újra kell
csinálni. Ezért minden alkatrész után kell egy egymás melletti kép és egy szám (sziluett-egyezés).

Függvények:
    kivag(img)                    a háttér levágása (a bal felső pixel színe a háttér)
    egymas_mellett(ref, sw, out)  bal: referencia, jobb: modell, azonos magasságra méretezve
    racs(kepek, out)              több nézet egy rácsban, fájlnévvel (nézőszög-kereséshez)
    sziluett_egyezes(ref, sw)     a két kép sziluettjének IoU értéke (0..1)

Parancssor:
    python osszevetes.py par <ref> <sw> <out> [--crop x0,y0,x1,y1] [--cimkek "Ref,Modell"]
    python osszevetes.py racs <out> <kep1> <kep2> ...
    python osszevetes.py iou <ref> <sw> [--crop x0,y0,x1,y1]
"""
import argparse
import os
import sys

from PIL import Image, ImageChops, ImageDraw


def _eloter(rgb, kuszob=28):
    """Előtér-maszk (L kép, 0/255): ami a (5, 5) pixel színétől (a háttértől) a küszöbnél jobban eltér.
    A legnagyobb csatornánkénti eltérés számít, nem a fényerő: a sárga a szürke háttértől főleg a kék
    csatornában tér el, és fényerőre szinte azonos vele."""
    hatter = Image.new("RGB", rgb.size, rgb.getpixel((min(5, rgb.width - 1), min(5, rgb.height - 1))))
    r, g, b = ImageChops.difference(rgb, hatter).split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > kuszob else 0)


def kivag(img, kuszob=28):
    """Levágja az egyszínű hátteret. A háttér színe a (5, 5) pixel; a SolidWorks színátmenetes
    háttere a küszöbön belül marad. Üres kép esetén az eredetit adja vissza."""
    rgb = img.convert("RGB")
    box = _eloter(rgb, kuszob).getbbox()
    return rgb.crop(box) if box else rgb


def _megnyit(kep, crop=None):
    img = kep if isinstance(kep, Image.Image) else Image.open(kep)
    img = img.convert("RGB")
    return img.crop(tuple(crop)) if crop else img


def _magassagra(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), h))


def egymas_mellett(ref, swkep, out, crop=None, cimkek=("Referencia", "SolidWorks modell"), magassag=900):
    """Bal oldalon a referencia (opcionálisan kivágva), jobb oldalon a háttér nélküli modellkép."""
    r = _magassagra(_megnyit(ref, crop), magassag)
    s = _magassagra(kivag(_megnyit(swkep)), magassag)
    kep = Image.new("RGB", (r.width + s.width + 60, magassag + 50), "white")
    kep.paste(r, (20, 40))
    kep.paste(s, (r.width + 40, 40))
    d = ImageDraw.Draw(kep)
    d.text((20, 10), cimkek[0], fill="black")
    d.text((r.width + 40, 10), cimkek[1], fill="black")
    kep.save(out)
    return out


def racs(kepek, out, oszlop=2, szelesseg=700):
    """Több kép rácsban, mindegyik fölött a fájlnevével. Nézőszög-kereséshez: több szögből
    renderelt kép egy lapon, és a referenciához legközelebbit kell kiválasztani."""
    kicsik = []
    for p in kepek:
        k = _megnyit(p)
        kicsik.append((os.path.basename(str(p)), k.resize((szelesseg, max(1, round(k.height * szelesseg / k.width))))))
    h = max(k.height for _, k in kicsik)
    sor = (len(kicsik) + oszlop - 1) // oszlop
    lap = Image.new("RGB", (oszlop * szelesseg, sor * (h + 20)), "white")
    d = ImageDraw.Draw(lap)
    for i, (nev, k) in enumerate(kicsik):
        x, y = (i % oszlop) * szelesseg, (i // oszlop) * (h + 20)
        lap.paste(k, (x, y + 20))
        d.text((x + 5, y + 4), nev, fill="black")
    lap.save(out)
    return out


def _maszk(img, meret, kuszob=28):
    """Előtér-maszk az eredeti háttérszínhez mérve, az előtér befoglalójára vágva, adott méretre nyújtva."""
    m = _eloter(img.convert("RGB"), kuszob)
    box = m.getbbox()
    m = m.crop(box) if box else m
    return m.resize(meret).point(lambda v: 255 if v > 127 else 0)


def sziluett_egyezes(ref, swkep, crop=None, meret=(256, 256), kuszob=28):
    """A két kép sziluettjének IoU értéke (metszet / unió) azonos méretre normálva.

    Durva, de objektív szám: azonos nézőszög mellett az arányok és a körvonal eltérését méri.
    A színt és a részleteket nem. Csak azonos nézőszögű képpárnál van értelme.
    """
    a = _maszk(_megnyit(ref, crop), meret, kuszob)
    b = _maszk(_megnyit(swkep), meret, kuszob)
    metszet = ImageChops.multiply(a, b).histogram()[255]
    unio = ImageChops.lighter(a, b).histogram()[255]
    return metszet / unio if unio else 0.0


def _crop(s):
    return tuple(int(v) for v in s.split(",")) if s else None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("par")
    p.add_argument("ref")
    p.add_argument("sw")
    p.add_argument("out")
    p.add_argument("--crop")
    p.add_argument("--cimkek", default="Referencia,SolidWorks modell")
    r = sub.add_parser("racs")
    r.add_argument("out")
    r.add_argument("kepek", nargs="+")
    i = sub.add_parser("iou")
    i.add_argument("ref")
    i.add_argument("sw")
    i.add_argument("--crop")
    a = ap.parse_args()
    if a.cmd == "par":
        print(egymas_mellett(a.ref, a.sw, a.out, _crop(a.crop), tuple(a.cimkek.split(",", 1))))
    elif a.cmd == "racs":
        print(racs(a.kepek, a.out))
    else:
        print(f"sziluett-egyezés (IoU): {sziluett_egyezes(a.ref, a.sw, _crop(a.crop)):.3f}")


if __name__ == "__main__":
    main()
