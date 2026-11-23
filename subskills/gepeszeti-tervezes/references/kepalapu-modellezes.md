# Modellezés referenciakép vagy rajz alapján

Akkor kell, ha a cél egy fotó, sajtókép, robbantott ábra vagy rajz "kinézete", és nincs CAD modell.
A legnagyobb kockázat: a modell a modellezőnek elfogadhatónak tűnik, a felhasználónak pedig "közel
sem olyan". Ezt csak a korai, alkatrészenkénti összevetés szűri ki.

## Kötelező lépések

1. **Bontás.** A célt bontsd alkatrészekre vagy csoportokra, mielőtt bármit építesz. Mindegyikhez
   írd le a "kész" feltételt: melyik referenciakép, melyik nézet, milyen méretek egyeznek.
   Egy teljes gép vagy jármű egy lépésben nem cél, csak az alkatrészek sorozata.
2. **Méretarány ismert méretből.** A képről csak arányt mérj. Az abszolút méretet egy ismert érték
   adja (furatosztás, kerékátmérő, gyári adat). Írd le, melyik méret melyik forrásból jön.
3. **Nézőszög beállítása az első alkatrész előtt.** Renderelj több szögből
   (`megjelenes.szogkereses`), tedd rácsba (`osszevetes.racs`), és válaszd ki a referenciához
   legközelebbit. Ezt a szöget rögzítsd a projektszkriptben, és minden összevetés ezzel készüljön.
4. **Összevetés minden alkatrész után.** `megjelenes.nezet_kep` a rögzített szögből, majd
   `osszevetes.egymas_mellett` a referenciával. Mellé `osszevetes.sziluett_egyezes` (IoU) számként.
   A képet nézd meg, és írd le az eltéréseket. A következő alkatrész csak ezután jöhet.
5. **Megmutatás korán.** Az első alkatrész összevető képét mutasd meg a felhasználónak, mielőtt a
   többit építed. Az irány hibáját itt a legolcsóbb javítani.
6. **Megjelenés.** A szín és a fényezés a hasonlóság nagy része: `megjelenes.alkalmaz` RealView
   anyagokkal, `megjelenes.realview`.
   - A színt a referenciaképről mintázd (egy megvilágított lap pixelértéke), ne becsüld.
   - Festett test egyedi színnel: `megjelenes.alkatresz(doc, "painted/car/steel grey.p2m", szin=(R, G, B))`.
     A `painted/car/*` megjelenések átveszik a `PrimaryColor`-t, a `painted/powder coat/*` nem
     (élőben mérve: a porfesték fekete maradt).
   - Megmunkált lapok fémesen (furat, illesztett homlok, ahogy a műhelyrajzok 3D képein):
     `megjelenes.lapok(doc, part.plane_faces(...) + part.cylinder_faces(...), "metal/aluminum/polished aluminum.p2m")`.
     A sarok-lekerekítések hengeres lapjait az `exclude_radii` hagyja ki, így azok festettek maradnak.

## Buktatók

- **Perspektíva.** A sajtóképek perspektivikusak, a robbantott katalógusábrák izometrikusak. A
  SolidWorks-nézet alapból párhuzamos vetítésű, ezért a sziluett-egyezés soha nem lesz 1.
  Az IoU az alkatrészek közti javulás követésére jó, nem abszolút minősítésre.
- **Kivágás.** A referenciából vágd ki a tárgyat (`--crop`), különben a felirat és a háttér is
  beleszámít. A SolidWorks-kép hátterét az `osszevetes.kivag` levágja.
- **Háttér-maszk színnel:** a kivágás a csatornánkénti legnagyobb eltérést nézi, nem a
  fényerőt. A sárga test fényerőre majdnem azonos a szürke háttérrel, és fényerő-küszöbbel félbe
  vágódott.
- **Nézőirány:** a referencia 3D képének irányából renderelj (`szogkereses`). Más irányból egy
  meglévő lekerekítés vagy furat "hiányzónak" látszik, és a felhasználó joggal rákérdez. A RealView
  nem rajzol élvonalat, ezért a kis lekerekítés kevésbé látszik, mint egy vonalas rajzon.
- **Sárga festés:** a `painted/car/metallic gold` narancsnak látszik. Sárga festett részhez a
  `plastic/high gloss/yellow high gloss plastic` közelebb áll.
- **Referenciajelölők** a képen: a `nezet_kep` elrejti őket (198-as kapcsoló).
- **Összeállítás-szintű megjelenés** felülírja a lapszíneket: a többszínű alkatrészt hagyd ki a
  szabályokból, és alkatrész szinten színezd.
- **Szabadformás felület** (burkolatok, öntvények bordázata) vázlat + kihúzás lépésekkel csak
  durván közelíthető. Mondd meg előre a felhasználónak, mi lesz durva, és kérdezd meg, elég-e.
- **Túl nagy cél.** Ha a feladat több tucat összetett alkatrész képről, az első lépés egy
  alkatrész kész minőségben, nem az egész durván. Az egész durván elkészítve újrakezdést jelent.
