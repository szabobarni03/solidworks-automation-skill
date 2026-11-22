# Rajz (2D): bevált sorrend és buktatók

## Sorrend

1. **Előkészítés a modellben.** Egyéni tulajdonságok (megnevezés, anyag, szabvány). Forgástestnél a
   vázlatméretek átrendezése, lásd lent.
2. `rajz.new_drawing(lapkeret, size_code, w, h, s1, s2)`. Az új lap méretarányát a függvény utólag
   SetScale-lel beállítja.
3. Nézetek: `rajz.view(..., scale=...)`. A méretarányt mindig explicit add meg.
4. Metszet, törött nézet, modellméretek (`InsertModelAnnotations3`).
5. Méretek elrendezése (pozíció, pontosság), középvonal, megjegyzés (tűrés, felület, élek).
6. Darabjegyzék és tételszámok (összeállítási rajz).
7. `save_drawing`, utána `pdf_to_png`, és a kép szemmel átnézése. A "lefutott" nem jelenti, hogy jó.

## Méretarány: háromszor kell beállítani

- A `SetupSheet5` nem veszi át az s1:s2-t. Utána a `GetCurrentSheet().SetScale(s1, s2, True, False)`
  kell, az újra lekért lapon.
- A nézet sem mindig veszi át a lap méretarányát. Ezért kell a `UseSheetScale = False` és a
  `ScaleDecimal = ...`.
- Az első nézet beszúrása átírja a lap méretarányát (automatikus méretarány; 1:2-ből 2:1 lett a
  szövegmezőben). A `rajz.view` ezért kiolvassa a lap méretarányát a beszúrás előtt, és utána
  visszaállítja. Saját kódban is ellenőrizd a nézetek után.
- A lapvázlat (pl. kézzel rajzolt középvonal) a lap méretarányával skálázott. A koordinátát
  `k = s2/s1`-gyel szorozni kell (`sheet_scale`, `sheet_centerline`).
- Visszaolvasás: a `sheet.GetProperties2[2:4]` (property, zárójel nélkül) és a `view.ScaleDecimal`.

## Törött nézet (hosszú tengely)

- `view.InsertBreak2(0, pos1, pos2, gap_style, line_style)`:
  - A pozíciók a nézet közepéhez mért eltolások, méterben.
  - A nézet 1:1 kell legyen. Különben `None` jön vissza.
- Utána: nézet kijelölése, majd `d.BreakView()`.
- A `GetOutline` törés után is a törés előtti körvonalat adja. A törött kontúr végpontjait
  számold: a bal oldal `x_bal + (x_modell - x0)`, a jobb oldal `x_jobb - (x1 - x_modell)`.
- A törött zónába eső méret hosszú, kóbor vonalat rajzol. Tedd a zónán kívülre, vagy a két
  oldal közé középre (hosszméretnél).

## Forgástest: átmérő, illesztés, menet

- A forgásvázlatban az `AddDimension2` (vonal + középvonal kijelölve) sugárméretet ad (`Type2 = 5`).
  Az `AddDiameterDimension2` és a kijelölési sorrend cseréje nem segített.
- Megoldás: lépj ki a vázlatból, kérd le a méreteket a feature-ből
  (`GetFirstDisplayDimension`/`GetNextDisplayDimension`), és állítsd be a `dd.Diametric = True`-t.
  Az értéket az átkapcsolás előtt olvasd ki, mert akkor még sugár.
- Illesztés tűrésosztállyal: `tol.Type = 8` (swTolFIT), `tol.SetFitValues("", "h7")`. Tűrés-pontosság:
  3 tizedes (`SetPrecision3(p, p, 3, 3)`). Másképp `0`-ra kerekített eltérések jelennek meg.
- Menetjelölés: `dd.ShowDimensionValue = False`, `dd.SetText(1, "Tr 24x5")`.
- Régi méretek törlése: az `annotation.Select2(True, 0)` minden méretre, majd az `EditDelete`. A
  `Select3(True, nv())` nem jelöl ki.
- A 3 mm-nél keskenyebb beszúrásokat (biztosítógyűrű-horony, alámetszés) ne méretezd egyenként.
  Ezeket a megjegyzésben a szabványra hivatkozva add meg.
- Méret felvétele közben kapcsold ki a "méret megadása létrehozáskor" opciót
  (`SetUserPreferenceToggle(10, False)`), különben dialógus blokkol.
- Nem gyártási méret (pl. segéd-kihúzási mélység) törlése a rajzon: a `FullName` alapján keresd meg,
  majd töröld.

## Darabjegyzék, tételszám, metszet

- `InsertBomTable4(True, x, y, 2, 1, "Standard", sablon, False, 0, False)`. Az utolsó oszlop után új
  oszlop: `InsertColumn2(4, n-1, fejléc, 0)`, majd `SetColumnCustomProperty(n, tulajdonság)`.
- A tábla mozgatása: előbb `Anchored = False`, majd `annotation.SetPosition2`.
- Fejléc szövege: `set_table_text` (Invoke, PROPERTYPUT).
- Tételszám: `CreateAutoBalloonOptions` + `AutoBalloon5`, kijelölt nézettel.
- Metszet: a metszővonalat a nézet aktív vázlatába rajzold. A vázlatkoordináta
  `(lap - nézetpozíció) / nézet méretarány`. Utána `CreateSectionViewAt5`.
- Megjegyzés előtt `ClearSelection2`. Kijelölés mellett a jegyzet mutatóvonalat kap.
