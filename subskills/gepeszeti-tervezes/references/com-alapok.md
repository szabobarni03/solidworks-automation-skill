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

- **Nem teljes körű forgatás iránya** (pl. 90°-os hajlítás egy rúdon): előre nem tudni. Próbáld
  az egyik irányt, és ellenőrizd a testszámot (a jó irány összeköti a két szárat, 1 test). A rossz
  irányt `f.Select2` + `Extension.DeleteSelection2(1)` (swDelete_Absorbed) törli a vázlatával
  együtt. A befoglaló méret erre nem jó: a referenciasík beleszámít.
- **Lemez kiköpölés (joggle):** a síkkontúrt húzd ki vastagon (középsíkra), aztán egy merőleges
  síkon rajzold meg a lemez S alakú oldalnézeti sávját, és vágd le a sávon kívüli két tartományt.
- **Kereszthorony és hasonló:** egy zárt sokszögként rajzold, ne két átfedő téglalapként.

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

## Lemez lekerekítése, zseb eltolt síkon

- Kihúzott lemez sarkai: a vázlatot éles sarkokkal rajzold, a lekerekítést utána a 3D éleken csináld
  (`Part.corner_edges(sarokpontok)` + `fillet_edges(élek, r, várt_db)`). Az ív-egyenes átmenetek
  érintési pontjait így nem kell kiszámolni. `FeatureFillet(195, r, 0, 0)`: pontosan 4 argumentum.
- Eltolt sík a másik oldalra: `plane(alap, d, flip=True)` (256-os opció), ne negatív távolság.
- Zseb vágása eltolt síkról: a `FeatureCut4` iránya a sík normálisától függ. A normál síkon
  `reverse=False`, a megfordított (`flip`) síkon `reverse=True` vág az anyagba. A rossz irány
  "vágás sikertelen" hibát ad, nem üres feature-t.
- Ferde falú zseb: `cut(mély, draft=30)` befelé szűkül (a kijelölt kontúr a felső él).
- Fedőlap körbefutó lekerekítése (pl. R1 a külső kontúron, a furatok nélkül):
  `fillet_edges(plane_edges(2, z, circle_radii=[r_sarok]), r, várt_db)`. A `plane_edges` a síkban
  fekvő egyenes éleket mind visszaadja, a köríveket csak a megadott sugárral.
- Átfedő kontúrok egy vázlatban (pl. téglalap és a végére rajzolt kör) "vágás sikertelen" hibát
  adnak. Rajzold őket külön vázlatba, és vágd egymás után.

## Hatszög (anya, kulcsnyílás)

- A `CreatePolygon` második pontja a SolidWorks 2026-ban mindig csúcs, az `Inscribed` kapcsolótól
  függetlenül (élőben mérve: mindkét értékkel 10 a csúcsok közti méret, ha a pont 5-re van).
- Laptávolsághoz (s) a csúcs s/√3 távolságra kell: ezt csinálja a `Part.hexagon(x, y, s)`.
  Csúcskör-átmérőhöz (d) a pont d/2-re kell: `Part.hexagon_corner(x, y, d)`.
- Ellenőrzés: a befoglaló méret egyik iránya s, a másik 2s/√3 (10-es kulcsnál 10 és 11,55).
  Ha mindkettő kisebb, a hatszög alulméretes; ezt a tömeg-ellenőrzés is jelzi.

## Minta, sweep, héj, lemez (élőben kipróbálva, SW 2026)

- **Lineáris minta:** `Part.linear_pattern(feature-ök, irány, db, osztás)`; `FeatureLinearPattern5`
  22 argumentummal. Kijelölés: a minta feature-ök 4-es, az irány (referenciatengely vagy egyenes él)
  1-es jelöléssel. A darabszámot a hosszból és az osztásból számold, ne rögzítsd.
- **Sweep:** `Part.sweep(profil, pálya)`; `InsertProtrusionSwept4` 20 argumentummal. Profil 1-es,
  pálya 4-es jelölés. A profil síkja a pálya kezdőpontján legyen, arra merőlegesen. Csőhöz két
  koncentrikus kör a profil.
- **Héj:** `Part.shell(lapok, vastagság)`. Az `InsertFeatureShell` semmit nem ad vissza: a sikert a
  feature-szám növekedése mutatja. A `GetFeatureCount` pywin32 alatt property is lehet: `c0`.
- **Süllyesztett furat:** `Part.cbore_holes(sík, pontok, d, D, mélység)`: két vágás egy
  pontlistából. A vakvágás az alap iránnyal (`reverse=False`) megy az anyagba a felső lap síkjáról.
- **Hosszú horony:** `Part.slot(x1, y1, x2, y2, szélesség)`: két egyenes és két félkör (`ccw=False`).
- **Lemezalkatrész alapperem:** az `InsertSheetMetalBaseFlange2` elavult, SW 2026-ban `None`-t ad
  bármilyen argumentummal; `None` a `CustomBendAllowance` helyén "Type mismatch". Helyette
  `fm.CreateDefinition(34)` (swFmBaseFlange) + `CreateFeature(adat)`, a nyitott vázlat kijelölve.
  Ez a `Part.sheet_metal_base_flange`.
- **K-tényező:** sem az alapperem adatán (`KFactor`, `OverrideKFactor`), sem a Sheet-Metal feature
  adatán (`SetCustomBendAllowance` + `ModifyDefinition`) nem hat: a beállítás csendben elvész, vagy
  tárolódik, de a kiterítés nem változik. Ami hat: minden `SketchBend` alfeature definíciója,
  `AccessSelections(doc, nv())`, `UseDefaultBendAllowance = False`, `GetCustomBendAllowance` (Type 2,
  KFactor), `SetCustomBendAllowance`, `ModifyDefinition(adat, doc, nv())`. Az `UseDefaultBendRadius`
  maradjon igaz, különben a sugár elállítódik.
- **Ellenőrzés:** a kiterített hossz (`Part.flat_size()`, a FlatPattern feature feloldásával) a
  K-tényezőtől függ, a formázott test térfogata nem. Ezért a K-tényezőt a kiterített hosszal kell
  ellenőrizni: L = a + b − BD, BD = 2 (r + t) tan(φ/2) − φ (r + K t).
- `AccessSelections` és `ModifyDefinition` harmadik (callout) paramétere `None` helyett `nv()`
  (VT_DISPATCH null), különben "Type mismatch".
