# Munkamódszer

## Alapelvek

- **Méret csak forrással.** A forrás sorrendje: CAD/STEP modell, mérés, adatlap, fotó. A fotóról
  becsült méret csak ideiglenes lehet. Egy valódi projektben a fotóbecslés 2,8 mm-t tévedett egy
  furatpozíción, és ez ütközést okozott volna. A STEP-ből olvasott érték pontos volt.
- **Paraméteres szkript, nem kézi modell.** Minden méret egy nevesített konstans a szkript tetején.
  Változtatás után az egész lánc újrafut: alkatrész, összeállítás, ellenőrzés, képek, csomag.
- **Előfeltétel-ellenőrzés építés előtt.** A `checks()` függvény a geometriai feltételeket
  ellenőrzi, és hibánál leáll. Példák: a lyuk kisebb a fejnél, a fészek mélyebb a fejnél, a csap
  bevezető vége kisebb a furatnál, a borda alacsonyabb a párnánál.
- **Változatok egy kódból.** Ha a koncepció nem egyértelmű, építs 2-3 változatot ugyanabból a
  kódból (pl. sima / horgos / becsúsztatós), és mutasd meg őket képen. A felhasználó választ.
- **A felhasználó ötlete is változat.** Építsd meg, és írd le tényszerűen az előnyét és a hátrányát.
- **Ellenőrzött állapot = ami le van futtatva.** Az "ütközésmentes" csak akkor állítható, ha az
  ütközésvizsgálat lefutott, és a találatokat egyenként megnézted.

## Mappaszerkezet (projekt)

```text
projekt/
  build_<alkatresz>.py      paraméterek + építés + checks()
  build_<osszeallitas>.py   elhelyezés/illesztés + ütközés JSON
  <rajz>.py                 rajzok + PDF
  <atvett>_step/            importált STEP + elemzés JSON
  review/                   ütközés JSON, képek, PDF renderek
  <Atadas_mappa>/ + .zip    STL, STEP, képek, README a címzett nyelvén
```

## Átadási README tartalma

1. Mire való, mit vált ki.
2. A csomag tartalma, fájlonként.
3. Méretek és forrásuk (táblázat), koordináta-rendszer és átszámítás.
4. Ellenőrzés: mit vizsgáltál, és mi lett az eredmény (a szándékos pressz-illesztések darabszáma).
5. Miért működik a konstrukció (anyag, tartás módja, tűrések).
6. Szerelési sorrend.
7. Nyomtatási beállítások.
8. Próbadarab és visszajelzés módja.
9. Még nem mért értékek.

Ékezetes nyelven UTF-8 BOM és CRLF, hogy Windows Jegyzettömbben is jól látsszon.

## Projektnapló (csak általános tanulság)

| Dátum | Típus | Fő tanulság |
|---|---|---|
| 2026-11-17 | Ollós emelőasztal: alkatrészek, összeállítás, hajtó méret, 2 rajz | Pont-sík távolság-illesztés kell hajtó méretnek. A rajz méretarányát háromszor kell beállítani (lap, nézet, lapvázlat). Forgásvázlat-sugarat utólag kell átmérőre váltani. |
| 2026-11-19 | FDM befogó egy NYÁK-ra, STEP alapján, 3 változat + próbadarab | Az átvett STEP-ben nem mindig van furat. A furatokat hengerfelületekből kell olvasni. Az importált alösszeállítás egy komponensként menjen az ütközésvizsgálatba. FDM-ben ne legyen rugalmas pattintás. |
