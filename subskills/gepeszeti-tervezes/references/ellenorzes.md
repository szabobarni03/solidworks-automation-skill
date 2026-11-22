# Ellenőrzés: mit, mivel, mi a hamis eredmény

| Mit | Mivel | Jó, ha | Hamis eredmény |
|---|---|---|---|
| Testszám | `ellenorzes.part_report` | `bodies == 1` | Az átfedő vázlat 2 testet ad, és ez nem tűnik fel a képen. |
| Térfogat, méret | `part_report` | Egyezik a becsléssel (anyag, tömeg) | Hiányzó feature: kisebb a térfogat. |
| Előfeltételek | projekt `checks()` | Nincs hiba | Csak a jelenlegi paraméterekre fut; a változatokra is futtasd. |
| Ütközés | `ellenorzes.interference_report(expected=n)` | Csak a szándékos pressz-illesztések, n darab | Az importált alösszeállítás belső átfedései (`subassemblies_as_components=True` kell). Nulla találat elnyomott komponenssel. |
| Koordináta-átszámítás | `transzform.apply` és mért furat | Eltérés < 0,01 mm | Tengelycsere vagy előjelhiba, ami szimmetrikus elrendezésnél nem látszik. |
| Mechanizmus | hajtó méret 2+ értéken | Újraépül, nincs ütközés | Csak az alaphelyzet ellenőrzött. |
| Rajz | `pdf_to_png` és szemrevételezés | Méretarány, méretek olvashatók, nincs kóbor vonal | A "lefutott" nem ellenőrzés. A törött zónában lévő méret és a rossz méretarány csak képen látszik. |
| Képek | `ellenorzes.render_views` | A lényeg nagyítva látszik | A teljes összeállításra zoomolva a kis alkatrész nem látszik: használd a `focus_prefix`-et. |
| Átadás | README "mérendő" lista | Minden becsült érték fel van sorolva | - |

## Átadás előtti sorrend

1. `checks()`, utána építés.
2. `part_report` minden alkatrészre.
3. Összeállítás, majd `interference_report`. A találatokat egyenként azonosítsd.
4. Képek.
5. Rajz PDF, utána PNG, és szemmel átnézés.
6. Csomag: fájlok, README, zip. A zip tartalmát listázva ellenőrizd.
