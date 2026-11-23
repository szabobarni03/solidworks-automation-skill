"""Síklemez-kontúr érintő körökből és lekerekített sarkokból (tiszta Python, tesztelt).

Miért kell: a lemezalkatrészek (karok, konzolok, hevederek) rajza tipikusan így méretez:
furatközéppontok, körülöttük R ívek, az ívek közt érintő egyenesek, a belső sarkokban R
lekerekítés. Ezt kézzel vázlatba rakni (érintési pontok, metszéspontok) hibalehetőség. Itt a
kontúr adatból számolódik, a területe előre ismert (tömeg-ellenőrzés építés előtt), és egy
lépésben vázlatba rajzolható.

Elemek, az óramutatóval ELLENTÉTES (CCW) körüljárási sorrendben, az anyag balra esik:
    ("kor", (x, y), r)               domború ív a középpont körül (pl. R10 egy furat körül)
    ("sarok", r, ((x, y), rr))       lekerekített sarok két érintő egyenes metszésénél. Az egyik
                                     egyenes az előző elem köréből, a másik a következő elem köréből
                                     fut a "rejtett" ((x, y), rr) körhöz. Homorú (belső) és domború
                                     sarokra is jó; a fordulás iránya dönti el.
A két szomszédos kör közti egyenes a közös külső érintő (a körök a menetirány bal oldalán).

    lanc = kontur(elemek)     [("vonal", p1, p2) | ("iv", kozep, p1, p2, ccw), ...]
    terulet(lanc)             a zárt kontúr területe (mm²), CCW esetén pozitív
    rajzol(part, lanc)        vázlatba rajzolás (swk.Part.line / Part.arc)
"""
import math


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _mul(a, k):
    return (a[0] * k, a[1] * k)


def _len(a):
    return math.hypot(a[0], a[1])


def _unit(a):
    n = _len(a)
    if n < 1e-12:
        raise ValueError("nulla hosszú irány")
    return (a[0] / n, a[1] / n)


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def erinto(c1, r1, c2, r2):
    """Külső érintő c1 -> c2 irányban, a körök a menetirány BAL oldalán (az érintő a jobb oldalon).
    Visszaad: (p1, p2) érintési pontok."""
    d = _sub(c2, c1)
    L = _len(d)
    a = (r1 - r2) / L
    if abs(a) > 1:
        raise ValueError(f"nincs külső érintő: {c1} r{r1} / {c2} r{r2}")
    u = _unit(d)
    jobb = (u[1], -u[0])
    n = _add(_mul(u, a), _mul(jobb, math.sqrt(1 - a * a)))
    return _add(c1, _mul(n, r1)), _add(c2, _mul(n, r2))


def _metszes(p1, u1, p2, u2):
    den = _cross(u1, u2)
    if abs(den) < 1e-12:
        raise ValueError("párhuzamos egyenesek a saroknál")
    t = _cross(_sub(p2, p1), u2) / den
    return _add(p1, _mul(u1, t))


def _kor(e):
    return (e[1], e[2]) if e[0] == "kor" else e[2]


def kontur(elemek):
    """A zárt kontúr vonalai és ívei (lásd a modul leírását)."""
    n = len(elemek)
    if n < 2:
        raise ValueError("legalább két elem kell")
    # i-edik egyenes: az i. és az (i+1). elem köre közti érintő
    vonalak = []
    for i in range(n):
        (c1, r1), (c2, r2) = _kor(elemek[i]), _kor(elemek[(i + 1) % n])
        vonalak.append(list(erinto(c1, r1, c2, r2)))
    ivek = []
    for i, e in enumerate(elemek):
        be, ki = vonalak[i - 1], vonalak[i]
        if e[0] == "kor":
            ivek.append(("iv", e[1], be[1], ki[0], True))
            continue
        r = e[1]
        u1, u2 = _unit(_sub(be[1], be[0])), _unit(_sub(ki[1], ki[0]))
        P = _metszes(be[0], u1, ki[0], u2)
        szog = math.atan2(_cross(u1, u2), _dot(u1, u2))
        bal = szog > 0
        t = r * math.tan(abs(szog) / 2)
        t1, t2 = _sub(P, _mul(u1, t)), _add(P, _mul(u2, t))
        normal = (-u1[1], u1[0]) if bal else (u1[1], -u1[0])
        kozep = _add(t1, _mul(normal, r))
        if _dot(_sub(t1, be[0]), u1) < -1e-9 or _dot(_sub(ki[1], t2), u2) < -1e-9:
            raise ValueError(f"a(z) {i}. sarok R{r} lekerekítése nem fér el az egyeneseken")
        be[1], ki[0] = t1, t2
        ivek.append(("iv", kozep, t1, t2, bal))
    lanc = []
    for i in range(n):
        iv = ivek[i]
        if _len(_sub(iv[2], iv[3])) > 1e-9:
            lanc.append(iv)
        p1, p2 = vonalak[i]
        if _len(_sub(p2, p1)) > 1e-9:
            lanc.append(("vonal", tuple(p1), tuple(p2)))
    return lanc


def _iv_szog(c, p1, p2, ccw):
    a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
    a2 = math.atan2(p2[1] - c[1], p2[0] - c[0])
    s = (a2 - a1) % (2 * math.pi)
    return s if ccw else s - 2 * math.pi


def terulet(lanc):
    """Zárt kontúr előjeles területe: húrokra Gauss-képlet + körszeletek."""
    A = 0.0
    for s in lanc:
        p1, p2 = (s[1], s[2]) if s[0] == "vonal" else (s[2], s[3])
        A += (p1[0] * p2[1] - p2[0] * p1[1]) / 2
        if s[0] == "iv":
            c = s[1]
            r = _len(_sub(p1, c))
            phi = _iv_szog(c, p1, p2, s[4])
            A += r * r / 2 * (phi - math.sin(phi))
    return A


def rajzol(part, lanc):
    """A kontúr vázlatba rajzolása egy `swk.Part` (vagy line/arc metódusú) objektummal."""
    for s in lanc:
        if s[0] == "vonal":
            part.line(s[1][0], s[1][1], s[2][0], s[2][1])
        else:
            c, p1, p2, ccw = s[1], s[2], s[3], s[4]
            part.arc(c[0], c[1], p1[0], p1[1], p2[0], p2[1], ccw)
