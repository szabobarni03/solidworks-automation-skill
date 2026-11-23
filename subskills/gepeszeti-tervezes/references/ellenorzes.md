# Ellenőrzés: mit, mivel, mi a hamis eredmény

| Mit | Mivel | Jó, ha | Hamis eredmény |
|---|---|---|---|
| Testszám | `ellenorzes.part_report` | `bodies == 1` | Az átfedő vázlat 2 testet ad, és ez nem tűnik fel a képen. |
| Térfogat, méret | `part_report` | Egyezik a becsléssel (anyag, tömeg) | Hiányzó feature: kisebb a térfogat. |
| Darabjegyzék-tömeg | `mass_check(doc, rajz_g, tures)` | Az eltérés a tűrésen belül | A rajz tömege is lehet hibás. Nagy eltérésnél számold ki a térfogat × sűrűség értéket. Ha a rajz értéke nem jön ki semmilyen ésszerű sűrűséggel (pl. tölgylap 5,9 g/cm³-rel), a térfogatból várt tömeg legyen az elvárt, és írd le a döntést. Néhány grammos alkatrésznél a rajz kerekítése 15–40%-ot is ad. |
| Csatlakozó menete | darabjegyzék és a fogadó furat rajza | A vett elem menete (NPT, G, M) azonos a furatéval | A forrásrajzok egymásnak ellentmondhatnak. Ne igazítsd csendben, jelezd a felhasználónak. |
| Előfeltételek | projekt `checks()` | Nincs hiba | Csak a jelenlegi paraméterekre fut; a változatokra is futtasd. |
| Ütközés | `ellenorzes.interference_report(expected=n)` | Csak a szándékos pressz-illesztések, n darab | Az importált alösszeállítás belső átfedései (`subassemblies_as_components=True` kell). Nulla találat elnyomott komponenssel. |
| Belső átfedés | `ellenorzes.section_image(out, plane, offset_mm, view, focus_prefix)` | A metszetben minden furat és a benne ülő csap/csavar/tengely kontúrja egymás mellett fut, nincs egymásba lógó metszetfelület | Külső nézetben nem látszik. A vágósík nem a tengelyen megy át, ezért a hiba kimarad: a furat tengelyét tartalmazó síkkal vágj (`offset_mm` = a tengely koordinátája). |
| Koordináta-átszámítás | `transzform.apply` és mért furat | Eltérés < 0,01 mm | Tengelycsere vagy előjelhiba, ami szimmetrikus elrendezésnél nem látszik. |
| Mechanizmus | hajtó méret 2+ értéken | Újraépül, nincs ütközés | Csak az alaphelyzet ellenőrzött. |
| Rajz | `pdf_to_png` és szemrevételezés | Méretarány, méretek olvashatók, nincs kóbor vonal | A "lefutott" nem ellenőrzés. A törött zónában lévő méret és a rossz méretarány csak képen látszik. |
| Képek | `ellenorzes.render_views` | A lényeg nagyítva látszik | A teljes összeállításra zoomolva a kis alkatrész nem látszik: használd a `focus_prefix`-et. |
| Referenciakép | `osszevetes.egymas_mellett`, `sziluett_egyezes` | Minden alkatrész után, rögzített nézőszögből; az eltérések leírva | A modellező szemének "jó" kép: csak egymás mellett látszik, hogy az arányok vagy a helyzet eltér. |
| Átadás | README "mérendő" lista | Minden becsült érték fel van sorolva | - |

## Átadás előtti sorrend

1. `checks()`, utána építés.
2. `part_report` minden alkatrészre.
3. Összeállítás, majd `interference_report`. A találatokat egyenként azonosítsd. Utána
   `section_image` minden furatos kapcsolatra, és a képeket nézd meg.
4. Képek.
5. Rajz PDF, utána PNG, és szemmel átnézés.
6. Csomag: fájlok, README, zip. A zip tartalmát listázva ellenőrizd.

## Metszetnézet COM-on

- `ModelViewManager.CreateSectionViewData()`, utána a tulajdonságok: `FirstPlane` (az alapsík
  feature-je, `std_planes`), `FirstOffset` (m), `ShowSectionCap = True`.
- `KeepCapColor = False`: a metszetfelület az alkatrész színét kapja. `True` esetén minden metszet
  fekete, és az egymásba lógó alkatrészek nem különböztethetők meg.
- `CreateSectionView(sd)` csak azt jelzi, hogy a nézet létrejött. Mentés után mindig
  `RemoveSectionView`, különben a következő kép is metszet marad.
