# COM alapok (pywin32, SolidWorks 2026)

## Hívási minták

- **Paraméter nélküli tag:** `c0(obj, "Name")`. A pywin32 ugyanazt a tagot egyszer metódusként,
  máskor property-ként adja (pl. `GetFaces`, `FirstFeature`, `GetType`). A `c0` csak akkor hív, ha a tag
  hívható, és nem `CDispatch`.
- **Property, ami tuple-t ad:** `sheet.GetProperties2`, `view.GetOutline`, `view.Position`,
  `surface.CylinderParams`, `curve.CircleParams`. Zárójel nélkül kell. A `GetProperties2()` hibája:
  `'tuple' object is not callable`.
- **Üres callout / selection data:** `VARIANT(VT_DISPATCH, None)`, vagyis `nv()`. A `None` önmagában
  típushibát ad.
- **Kimeneti int:** `VARIANT(VT_BYREF | VT_I4, 0)`, vagyis `byref_int()`. Az érték a `.value`-ban van.
- **Tömb property írása:** `VARIANT(VT_ARRAY | VT_R8, [x, y])`, pl. a `view.Position`-höz.
- **Paraméteres property (pl. `Table.Text(row, col) = ...`):** csak `_oleobj_.Invoke` működik, a
  `DISPATCH_PROPERTYPUT` flaggel (`rajz.set_table_text`).
- **Egységek:** a COM mindig métert vár és ad. Szögnél radiánt. A szkriptben mm van, és az `m()` vált.
- **Konzol:** a `sys.stdout.reconfigure(encoding="utf-8")` vagy a `PYTHONIOENCODING=utf-8` kell, különben
  az ékezetes kiírás `UnicodeEncodeError`-t (cp1252) ad.

## Vázlatsíkok (vázlat x,y -> modell)

| Sík | vázlat x | vázlat y | normális |
|---|---|---|---|
| elöl (front) | X | Y | +Z |
| felül (top) | X | -Z | +Y |
| jobb (right) | -Z | Y | +X |

A felül síkon rajzolt NYÁK-felülnézet y-ja a modell -Z irányába esik. Ezt az összeállításnál
figyelembe kell venni.

## Nyelvfüggés

- A szabvány síkok nevét (Ebene vorne / Front Plane / Elölnézet) ne használd. Az első három
  `RefPlane` feature-t vedd (`std_planes`).
- A rajznézet nevei a felület nyelvén vannak: német SW-ben `*Vorderseite`, `*Oben`, `*Links`,
  `*Isometrisch`.
- A sablon- és lapkeret-útvonal a telepítés nyelvi mappájában van (`lang\<nyelv>\sheetformat`).

## Építési buktatók

- Az átfedő, egymást metsző vázlatkontúrok egy kihúzásban hibát vagy több testet adnak. Bontsd
  külön vázlatokra/feature-ökre, vagy rajzolj egyesített kontúrt.
- Feature után mindig ellenőrizd, hogy nem `None` jött-e vissza, és dobj hibát. A csendes hiba
  később nehezen visszakereshető.
- Mentés előtt: ref. geometria elrejtése, `ForceRebuild3`, testszám ellenőrzése.
- Él kiválasztása élletöréshez: körélek sugár és magasság szerint (`Part.circle_edges`). A
  kiválasztott darabszámot ellenőrizd, eltérésnél ne készüljön feature.
- STL/STEP mentés: `SaveAs3(path.STL, 0, 1)` a kiterjesztés alapján választ formátumot.
