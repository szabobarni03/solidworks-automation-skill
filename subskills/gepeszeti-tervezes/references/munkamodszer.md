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
| 2026-11-22 | Belsőégésű motor mechanizmusa szkriptből: forgattyús hajtás, vezérlés, szelephajtás, motion study | A SaveAs csendben nem ment, ha nyitott összeállítás fogja a fájlt. A bütyökkövető illesztéshez külön felületlánc kell. A fogaskerék-illesztés alapból ellentétes irányú. Burkolathoz konvex burok pontmintából. |
| 2026-11-23 | Kézi mechanizmus rajzsorozatból: 11 alkatrész, szabványelemek, 1 szabadságfokú csuklós lánc, összeállítási rajz | Kinematika Pythonban előre, a helyzet transzformmal, aztán illesztés. Referenciatengelyek közt egybeesés, nem koncentrikus. Kötőelem a mozgó részen lock illesztéssel. A tömeg-ellenőrzés a rajz darabjegyzékével minden alkatrésznél elkapta a hibát. A felhasználó vette észre, hogy a menetes rúd a magátmérős furat falába lóg: az "szándékos" ütközésnek volt elkönyvelve. Javítás: névleges furat, metszetkép (`section_image`) minden furatos kapcsolatra. |
| 2026-11-23 | Nagy gép rajzsorozatból (kb. 30 alkatrész, 118 komponens): 7 fázis részegységenként, főösszeállítás forgó mechanizmussal, mozgásvideó | A fázisonkénti ellenőrző részegység (tömeg, ütközés, metszet) a főösszeállítás előtt kiszűrte a hibák nagyját. A darabjegyzék tömege is lehet hibás: térfogat × sűrűség dönt. A távolság-illesztés rossz oldalra is megoldhat: `flip` és `Transform2`-ellenőrzés. A megjelenés a rajz 3D képeihez: árnyékolt nézet fekete élekkel, a fémtípus a kép tónusa szerint. A felhasználó a színeltérést és a hiányzó élkontúrt kifogásolta, nem a geometriát. A forgattyúszög-söprés 12 szögben, utána a szögillesztés elnyomva a kézi forgatáshoz. Videó a `mozgas_kepkockak` és a `video` függvénnyel. |
| 2026-11-24 | Alkatrész- és elemkönyvtár feladatgyűjteményből: 28 alkatrész, 6 kis összeállítás (zsanér, fogaskerékpár, illesztés határméreteken, darabjegyzék) | Minden elem várt térfogata képletből, a modellel 0,1%-on belül; ahol a forrás egyszerűsít, a pontos képlet. Az elavult API `None`-t ad: az API-súgó "Obsolete" jelzését kell nézni, és a `CreateDefinition`/`CreateFeature` párost használni. A lemez K-tényezője csak a hajlítás-alfeature-ön hat; a kiterített hossz az egyetlen ellenőrzés, ami ezt elkapja. Az ütközésvizsgálat érzékenységét egy szándékosan rossz helyzettel kell igazolni. A README PDF-ben is kell. |
| 2026-11-24 | Gyakorlófeladat-gyűjtemény rajzokból (kb. 50 alkatrész, 4 összeállítás súlyponttal): extrude, revolve, minta, tükrözés, sweep, loft | Ahol a rajz kétféleképpen olvasható, a megadott térfogat (0,1%) vagy súlypont dönt; a válaszból rejtett méret vagy szög is visszaszámolható. A bizonytalan részletet nagyított renderen, pixelből mért méretaránnyal kell megnézni. Egyirányú kihúzás helyett a feature közepén álló sík és `mid`. Ami egyik olvasattal sem egyezik, kihagyva és feljegyezve, nem kiigazítva. |
| 2026-11-19 | FDM befogó egy NYÁK-ra, STEP alapján, 3 változat + próbadarab | Az átvett STEP-ben nem mindig van furat. A furatokat hengerfelületekből kell olvasni. Az importált alösszeállítás egy komponensként menjen az ütközésvizsgálatba. FDM-ben ne legyen rugalmas pattintás. |
