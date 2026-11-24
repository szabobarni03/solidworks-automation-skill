"""Evolvens fogazatú homlokkerék profilja (egyenes fog, kiegészítő profileltolás nélkül).

Tiszta Python, SolidWorks nélkül tesztelhető. A `fogprofil` a teljes kerék zárt kontúrját adja
pontsorként (mm), a fog középvonala a +X tengelyen. Vázlatba `Part.poly(pontok)`, utána kihúzás.

Képletek (DIN 3960 jelöléssel):
- osztókör d = m z, alapkör db = d cos α, fejkör da = d + 2 m, lábkör df = d - 2,5 m;
- fogvastagság az osztókörön s = π m / 2;
- inv(α) = tan α - α; a fog fél szöge az alapkörön ψb = s / d + inv(α);
- r sugáron a fogoldal polárszöge a fog középvonalától: θ(r) = ψb - inv(arccos(rb / r)).
Ha a lábkör az alapkör alatt van (kb. z < 42 esetén), a fogoldal az alapkör alatt sugárirányú
egyenes. A lábgörbület (trochoid) helyett éles a fogtő: a tömeg és a kapcsolódás ellenőrzéséhez
elég, gyártási rajzhoz nem.
"""
import math


def inv(a):
    return math.tan(a) - a


def meretek(m, z, alfa_fok=20.0):
    """Fő átmérők (mm): osztókör, alapkör, fejkör, lábkör."""
    d = m * z
    return {"d": d, "db": d * math.cos(math.radians(alfa_fok)), "da": d + 2 * m, "df": d - 2.5 * m}


def tengelytav(m, z1, z2):
    """Elemi (profileltolás nélküli) tengelytáv: a = m (z1 + z2) / 2."""
    return m * (z1 + z2) / 2


def fogprofil(m, z, alfa_fok=20.0, n_oldal=8, n_fej=3, n_lab=4):
    """A teljes kerék zárt kontúrja [(x, y), ...] mm-ben; a 0. fog középvonala a +X tengelyen.
    n_oldal: pontok fogoldalanként, n_fej és n_lab: közbenső pontok a fej- és a lábkörön."""
    k = meretek(m, z, alfa_fok)
    r, rb, ra, rf = k["d"] / 2, k["db"] / 2, k["da"] / 2, k["df"] / 2
    alfa = math.radians(alfa_fok)
    psi_b = (math.pi * m / 2) / (2 * r) + inv(alfa)

    def theta(rr):
        return psi_b - inv(math.acos(min(1.0, rb / rr)))

    r0 = max(rb, rf)
    theta_a = theta(ra)
    if theta_a <= 0:
        raise ValueError(f"hegyes fog (z = {z}): a fej vastagsága nem pozitív")
    oldal = [r0 + (ra - r0) * i / (n_oldal - 1) for i in range(n_oldal)]

    def pont(rr, fi):
        return (rr * math.cos(fi), rr * math.sin(fi))

    pts = []
    for i in range(z):
        fi = 2 * math.pi * i / z
        th0 = theta(r0)
        pts.append(pont(rf, fi - th0))
        if rb > rf:
            pts.append(pont(rb, fi - th0))
        for rr in oldal[1:]:
            pts.append(pont(rr, fi - theta(rr)))
        for j in range(1, n_fej + 1):
            pts.append(pont(ra, fi - theta_a + 2 * theta_a * j / (n_fej + 1)))
        for rr in reversed(oldal[1:]):
            pts.append(pont(rr, fi + theta(rr)))
        if rb > rf:
            pts.append(pont(rb, fi + th0))
        pts.append(pont(rf, fi + th0))
        kov = 2 * math.pi * (i + 1) / z - th0
        for j in range(1, n_lab + 1):
            pts.append(pont(rf, fi + th0 + (kov - fi - th0) * j / (n_lab + 1)))
    return pts


def terulet(pts):
    """Zárt sokszög területe (mm²), cipőfűző-képlettel: a kerék tömegének becsléséhez."""
    n = len(pts)
    return abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))) / 2
