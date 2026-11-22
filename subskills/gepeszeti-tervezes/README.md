# Gépészeti tervezés (3D/2D)

A `gepeszeti-tervezes` a `solidworks-automation` subskillje. Valódi projektek tanulságait gyűjti egy
helyre, három formában: munkamódszer, kipróbált COM-segédkönyvtár és kötelező ellenőrzőlista.
A skill minden lezárt projekt után bővül (lásd: projektlezáró rutin a `SKILL.md`-ben).

## Tartalom

- `SKILL.md`: mikor kell, munkafolyamat, ellenőrzőlista, projektlezáró rutin.
- `scripts/`: `transzform` (tiszta Python), `swk` (alkatrész, összeállítás, illesztés), `rajz`,
  `step_elemzes`, `ellenorzes`.
- `references/`: COM-alapok, összeállítás, rajz, STEP-elemzés, FDM-segédeszköz, ellenőrzés,
  tanulság-sablon, munkamódszer és projektnapló.

## Gyors használat

```powershell
# STEP import és furatelemzés (a SolidWorks fusson)
venv\Scripts\python.exe subskills\gepeszeti-tervezes\scripts\step_elemzes.py import modell.step out modell
venv\Scripts\python.exe subskills\gepeszeti-tervezes\scripts\step_elemzes.py elemez out\modell_adatok.json

# Ütközés az aktív összeállításon, 24 szándékos pressz-illesztéssel
venv\Scripts\python.exe subskills\gepeszeti-tervezes\scripts\ellenorzes.py utkozes review\utkozes.json --expected 24
```

## Tesztek

```powershell
venv\Scripts\python.exe -m pytest tests\test_gepeszeti_tervezes.py
```

A transzform-matematika és a csomag szerkezete SolidWorks nélkül is tesztelhető. Az élő
smoke-teszt (`tests/gepeszeti_tervezes_live_smoke.py`) futó SolidWorkst igényel.

## Állapot

`pilot`: SolidWorks 2026-on (német felület) két projektben használt kódból kiemelve.
