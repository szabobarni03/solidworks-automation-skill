"""README.md -> README.pdf: böngészőben és bárhol megnyitható átadási dokumentum.

A Markdown HTML-lé alakul (táblázatok, kódblokkok, képek a README mappájához képest), utána a
Microsoft Edge vagy a Chrome fej nélküli módban PDF-be nyomtatja. A .md marad a forrás (abból
generálható újra), a PDF mellé kerül azonos néven.

Futtatás:  python readme_pdf.py <README.md> [kimenet.pdf]
Kell hozzá: a `markdown` csomag (Anacondában benne van) és Edge vagy Chrome.
"""
import base64
import html
import io
import os
import pathlib
import re
import subprocess
import sys
import tempfile

BONGESZOK = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10pt; line-height: 1.45;
       color: #1d2330; max-width: 100%; }
h1 { font-size: 20pt; border-bottom: 2px solid #2f5d8a; padding-bottom: 4px; color: #1f3f60; }
h2 { font-size: 14pt; color: #1f3f60; margin-top: 18px; border-bottom: 1px solid #c9d4e0; }
h3 { font-size: 11.5pt; color: #2f5d8a; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 8.8pt;
        page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #c9d4e0; padding: 3px 6px; vertical-align: top; text-align: left; }
th { background: #e8eef5; }
tr:nth-child(even) td { background: #f7f9fc; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f0f3f7; padding: 0 3px; }
pre { background: #f0f3f7; padding: 8px; border-radius: 4px; white-space: pre-wrap; }
pre code { padding: 0; }
img { max-width: 100%; max-height: 120mm; display: block; margin: 8px auto;
      page-break-inside: avoid; }
blockquote { border-left: 3px solid #2f5d8a; margin-left: 0; padding-left: 10px; color: #445; }
a { color: #2f5d8a; text-decoration: none; }
"""


def kepek_kicsinyitve(torzs, mappa, max_px=1100, minoseg=85):
    """Az <img> forrásokat kicsinyített JPEG-ként a HTML-be ágyazza. A SolidWorks-képek ~1700 px
    szélesek PNG-k: 30 kép így 20 MB-os PDF-et adna, kicsinyítve 2-3 MB-ot. PIL nélkül változatlan."""
    try:
        from PIL import Image
    except ImportError:
        return torzs

    def csere(mt):
        p = (mappa / mt.group(2)).resolve()
        if not p.exists():
            return mt.group(0)
        im = Image.open(p).convert("RGB")
        if im.width > max_px:
            im = im.resize((max_px, round(im.height * max_px / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=minoseg)
        return f'{mt.group(1)}data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}{mt.group(3)}'

    return re.sub(r'(<img[^>]*?src=")([^"]+\.(?:png|jpg|jpeg))(")', csere, torzs, flags=re.I)


def html_keszit(md_path):
    """A README HTML-je; a <base> a README mappája, így a relatív képek és linkek működnek."""
    import markdown
    md_path = pathlib.Path(md_path).resolve()
    szoveg = md_path.read_text(encoding="utf-8")
    torzs = markdown.markdown(szoveg, extensions=["tables", "fenced_code", "sane_lists", "toc"])
    torzs = kepek_kicsinyitve(torzs, md_path.parent)
    cim = next((s.lstrip("# ").strip() for s in szoveg.splitlines() if s.startswith("# ")), md_path.stem)
    base = md_path.parent.as_uri() + "/"
    return (f'<!doctype html><html lang="hu"><head><meta charset="utf-8"><base href="{base}">'
            f"<title>{html.escape(cim)}</title><style>{CSS}</style></head><body>{torzs}</body></html>")


def bongeszo():
    for b in BONGESZOK:
        if os.path.exists(b):
            return b
    raise RuntimeError("Nincs Edge vagy Chrome a szokásos helyen")


def pdf(md_path, out=None):
    md_path = pathlib.Path(md_path).resolve()
    out = pathlib.Path(out).resolve() if out else md_path.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        h = pathlib.Path(tmp) / "readme.html"
        h.write_text(html_keszit(md_path), encoding="utf-8")
        if out.exists():
            out.unlink()
        subprocess.run([bongeszo(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={tmp}\\profil", f"--print-to-pdf={out}", h.as_uri()],
                       check=False, capture_output=True, timeout=120)
    if not out.exists() or out.stat().st_size < 1000:
        raise RuntimeError(f"A PDF nem készült el: {out}")
    print(f"{out} ({out.stat().st_size // 1024} kB)")
    return out


if __name__ == "__main__":
    pdf(*sys.argv[1:3])
