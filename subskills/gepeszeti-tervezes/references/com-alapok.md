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
- **A SaveAs hiba nélkül nem ment**, ha egy nyitott összeállítás hivatkozik az alkatrészre. A régi
  fájl marad, és a következő lépés elavult geometriával dolgozik. Alkatrész újraépítése előtt
  `sw.CloseAllDocuments(True)`. A `swk.Part.save` a fájl módosítási idejét ellenőrzi, és hibát dob.
- **Forgatás tengelye:** a középvonal legyen hosszú (pl. ±300 mm). A rövid középvonal mellett a
  forgatás néha hibát ad, ha a profil a középvonal végén túlnyúlik.
- **Egymást érintő forgató vágások** (pl. két szomszédos szelepfészek, amelyek pontosan érintik
  egymást) hibát adnak. Hagyj legalább 0,3 mm hézagot, vagy rajzold egy vázlatba.
- **Élletörés vékony falon:** ha a letörés nagyobb a falvastagságnál, a forgatás hibát ad.
- **Burkológörbe körökből:** ne tételezd fel, hogy minden kör a burkon van. Mintavételezd a köröket
  pontokra, és számolj konvex burkot (monotone chain). A burokra eltolt kontúr így mindig zárt.
- **Feature-ök kapcsolódása:** a különálló darab (pl. egy szívókosár) új testet ad. A testszámot
  minden alkatrész végén ellenőrizd (`GetBodies2`), és egy test legyen, ha egy darabról van szó.
- **Negatív síkeltolás:** az `InsertRefPlane` távolsága nem lehet negatív. Ha az alkatrész egy része
  az alapsík "mögé" kerülne, építsd az alkatrészt eltolt helyi koordinátákban (pl. X + 100), tegyél
  bele egy referenciasíkot a helyi 100-nál, és az összeállításban ezt a síkot illeszd a helyére.
- **Nem középsíkos vágás iránya:** a `FeatureCut4` egyirányú vágása a vázlatsík normálisával
  ellentétesen halad. Ha a vágásnak a sík "előtt" kell lennie, a vázlatot a vágás túlsó végére tedd,
  vagy használj középsíkos vágást (`mid=True`).
