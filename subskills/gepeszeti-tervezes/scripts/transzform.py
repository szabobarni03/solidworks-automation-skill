"""Forgatás- és eltolásmátrixok komponensek elhelyezéséhez (tiszta Python, SolidWorks nélkül is tesztelhető).

Konvenció (SolidWorks MathTransform): sorvektor, p' = p·R + t.
R sorai a lokális X, Y, Z tengely képei világkoordinátában.
Minden hossz mm-ben; a SolidWorks felé menő tömb méterben van (transform_data).
"""
import math

I3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1.0, 0.0, 0.0), (0.0, c, s), (0.0, -s, c))


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c))


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, s, 0.0), (-s, c, 0.0), (0.0, 0.0, 1.0))


def mul(a, b):
    """Először a, utána b (p' = p·a·b)."""
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def axes(x_to, y_to):
    """Forgatás, amely a lokális X-et x_to-ra, a lokális Y-t y_to-ra viszi (egységvektorok, merőlegesek)."""
    z = (x_to[1] * y_to[2] - x_to[2] * y_to[1],
         x_to[2] * y_to[0] - x_to[0] * y_to[2],
         x_to[0] * y_to[1] - x_to[1] * y_to[0])
    return (tuple(x_to), tuple(y_to), z)


def apply(R, t, p):
    """Pont transzformálása: p·R + t."""
    return tuple(sum(p[k] * R[k][j] for k in range(3)) + t[j] for j in range(3))


def det(R):
    return (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1])
            - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
            + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))


def transform_data(R=I3, t_mm=(0.0, 0.0, 0.0)):
    """16 elemű ArrayData a create_math_transform-hoz: 9 forgatás, eltolás méterben, skála 1, majd 0,0,0.

    Tükrözést (det = -1) a SolidWorks komponens-transzformként nem fogad el: hibát dobunk.
    """
    if abs(det(R) - 1.0) > 1e-6:
        raise ValueError(f"R nem tiszta forgatás (det = {det(R):.6f}); tükrözés helyett forgass")
    return [R[0][0], R[0][1], R[0][2], R[1][0], R[1][1], R[1][2], R[2][0], R[2][1], R[2][2],
            t_mm[0] / 1000.0, t_mm[1] / 1000.0, t_mm[2] / 1000.0, 1.0, 0.0, 0.0, 0.0]


def map_points(points, R=I3, t=(0.0, 0.0, 0.0)):
    """Pontlista transzformálása (ellenőrzéshez: pl. STEP furatok -> összeállítás koordináták)."""
    return [apply(R, t, p) for p in points]
