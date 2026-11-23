"""Esztergált (forgás-) alkatrészek profilja lépcsős szakaszokból (tiszta Python, tesztelt).

Miért kell: a csapok, tengelyek, távtartók rajza szakaszonként méretez (hossz, átmérő, horony,
élletörés, furat). A profil pontjait kézzel felírni hibalehetőség. Itt a profil adatból jön, a
térfogata építés előtt ismert (tömeg-ellenőrzés), és `swk.Part.revolve_profile` egy lépésben
megépíti (a modell X tengelye körül).

    pts = profil([(2, 6), (1, 5), (15, 6)], letores={0: (0.5, 0)}, x0=0)
    terfogat(pts)                 # mm³
    part.revolve_profile(pts)

szakaszok: [(hossz, átmérő), ...] balról jobbra, x0-tól.
letores:   {szakasz_index: (bal, jobb)} 45°-os élletörés a szakasz külső sarkain. Csak domború
           sarokra (ahol a szomszéd kisebb vagy nincs); homorú sarokra ValueError.
furat:     átmenő furat átmérője (None = tömör). Menetes furatnál a magátmérő (pl. M4: 3,242).
sullyesztes: (bal, jobb) 90°-os süllyesztés külső átmérője a furat két végén (0 = nincs).
"""
import math


def profil(szakaszok, letores=None, x0=0.0, furat=None, sullyesztes=(0.0, 0.0)):
    """Zárt profil [(x, r), ...]: felső kontúr balról jobbra, vissza a tengelyen vagy a furaton."""
    if not szakaszok:
        raise ValueError("legalább egy szakasz kell")
    letores = letores or {}
    rb = furat / 2 if furat else 0.0
    for _, d in szakaszok:
        if d / 2 <= rb:
            raise ValueError(f"a Ø{d} szakasz nem nagyobb a furatnál")
    felso = []
    x = x0
    n = len(szakaszok)
    for i, (h, d) in enumerate(szakaszok):
        r = d / 2
        bal, jobb = letores.get(i, (0.0, 0.0))
        r_elozo = szakaszok[i - 1][1] / 2 if i > 0 else rb
        r_kov = szakaszok[i + 1][1] / 2 if i < n - 1 else rb
        for c, szomszed in ((bal, r_elozo), (jobb, r_kov)):
            if c and (szomszed >= r or c >= min(h, r - szomszed)):
                raise ValueError(f"a(z) {i}. szakasz {c} élletörése nem fér el")
        felso += [(x, r - bal), (x + bal, r)] if bal else [(x, r)]
        felso += [(x + h - jobb, r), (x + h, r - jobb)] if jobb else [(x + h, r)]
        x += h
    x1 = x
    sb, sj = sullyesztes
    also = []
    if furat:
        also += [(x1, sj / 2), (x1 - (sj / 2 - rb), rb)] if sj else [(x1, rb)]
        also += [(x0 + (sb / 2 - rb), rb), (x0, sb / 2)] if sb else [(x0, rb)]
    else:
        also = [(x1, 0.0), (x0, 0.0)]
    pts = [(x0, also[-1][1])] + felso + also[:-1] if furat else [(x0, 0.0)] + felso + [(x1, 0.0)]
    # egymás utáni azonos pontok kiszűrése
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-9:
            out.append(p)
    if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-9:
        out.pop()
    return out


def terfogat(pts):
    """A zárt (x, r) profil X tengely körüli forgatásával kapott test térfogata (mm³)."""
    v = 0.0
    n = len(pts)
    for i in range(n):
        (x1, r1), (x2, r2) = pts[i], pts[(i + 1) % n]
        v += (x2 - x1) * (r1 * r1 + r1 * r2 + r2 * r2)
    return abs(v) * math.pi / 3
