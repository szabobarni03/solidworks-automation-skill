# Összeállítás: elhelyezés és illesztés

## Elhelyezés transzformmal (rögzített komponensek)

- Sorvektor-konvenció: `p' = p·R + t`. Az R sorai a lokális X, Y, Z tengely képei világkoordinátában.
- A `Transform2.ArrayData` 16 elemű: 9 forgatás, 3 eltolás méterben, a skála (1), majd 0, 0, 0.
  Ezt adja a `transzform.transform_data(R, t_mm)`, a SolidWorks felé a `create_math_transform(sw, data)`.
- Csak tiszta forgatás lehet (det = +1). Tükrözés kell? Forgass, és ellenőrizd egy ismert ponton.
- Sorrend: komponens beszúrása, `UnfixComponent`, `Transform2` beállítása, `FixComponent`.
- **Visszaellenőrzés:** egy ismert pontot (pl. egy furatközéppontot) a `transzform.apply`-jal számolj
  át. Hasonlítsd össze a ráhelyezett modellből mért értékkel (`step_elemzes.cylinder_holes` a
  komponensen). Egy eltévesztett tengelycsere így azonnal kiderül.

## Illesztések (mozgó mechanizmus)

- Az alkatrészbe építs nevesített referenciatengelyt és -pontot (`Part.axis`, `Part.point`). Ne
  élre vagy lapra hivatkozz, mert ezek újraépítéskor átszámozódhatnak.
- Komponens feature-je összeállítás-szinten: `get_assembly_entity(comp, feature)`. Alösszeállításban
  lévő komponens neve: `"Alossz-1/Alkatresz-1"`.
- Csukló: tengely-tengely egybeesés, plusz középsík-egybeesés a tengelyirányú helyzethez.
- **Hajtó méret:** pont-sík távolság-illesztés kell. A tengely-sík és a sík-sík távolság
  párhuzamos geometriánál túlhatároz (`add_mate5` hiba 5).
- Hajtó méret állítása: `doc.Parameter("D1@<illesztésnév>").SystemValue = h/1000`, utána
  `EditRebuild3`. Legalább két értéken ellenőrizd (alsó és felső helyzet), mindkettőn ütközéssel.
- Görgő síkon: pont-sík távolság a görgő sugarával.
- **Tengely-tengely illesztés típusa:** két referenciatengelyre `MATE_COINCIDENT` (0) kell. A
  `MATE_CONCENTRIC` (1) referenciatengelyekre `AddMate5` hibát ad (error_status 0). Koncentrikus
  csak hengeres lapokra jó.
- **Furattengely az alkatrészben:** `Part.hole_axis(x, y, z, név)`. A hengeres lapot geometriából
  keresi (a pont a palástján). A koordinátás `SelectByID2("FACE")` néha nem talál semmit. Az
  összeállításban a csap és a furat lapja egybeesik, ezért ott ne lapot jelölj ki.
- **Kötőelem mozgó részen** (csavar, biztosítótárcsa, csap): előbb helyezd el pontosan
  transzformmal, aztán `Assembly.lock(komp, hordozó)` (swMateLOCK = 16). Így együtt mozog, és nem
  kell rá 3 illesztés.
- **Kinematika előre:** a mechanizmus helyzetét számold ki Pythonban (szög, hajtó méret,
  kimeneti méret), és ebből helyezd el a komponenseket illesztés előtt. A hajtó méret
  végigléptetésekor minden lépésben vesd össze a mért komponenshelyzetet a számolttal. Az eltérés
  0 legyen; ha nem, az illesztés rossz ágra ugrott.
- **Szabadon forgó pofa vagy talp:** a nyílás a két csap távolságából számolandó (a lapok egymás
  felé fordulnak), nem egy rögzített irány mentén. A két lapot egymással párhuzamosra illeszd.

## Hajtáslánc-kényszerek (fogaskerék, bütyökkövető)

- **Fogaskerék-illesztés (típus 10):** két forgástengelyt köt. Az áttétel `gear_num` = az első
  entitás fogszáma, `gear_den` = a másodiké. Az alapértelmezett illesztés ellentétes forgást ad.
  Azonos forgásirányhoz (pl. lánc- vagy szíjhajtás) `flip=True` kell.
- **Lánchajtás merev modellben:** a láncot rögzített testként modellezd, a kerekeket fogaskerék-
  illesztés kösse. Az álló lánc és a forgó kerék átfedése várt ütközés, szűrd ki a jelentésből.
- **Bütyökkövető illesztés (típus 9):** először a bütyök felületét válaszd ki, utána a követő
  hengerét (görgő). A bütyök felületlánca nem olvadhat össze a szomszédos bütyökével. Hagyj köztük
  legalább 1 mm hézagot, különben az `add_mate5` 5-ös hibát ad.
- **Felület kiválasztása összeállításban:** iterálj az alkatrész felületein
  (`comp.GetModelDoc2()`), szűrj sugárra és befoglaló dobozra, majd `get_assembly_entity(comp, face)`
  (`Component2.GetCorresponding`).
- **Ellenőrzés:** forgasd végig a hajtótengelyt szögillesztéssel (két menetben, mert a szögillesztés
  iránya 0 és 180 fok körül átfordulhat). Minden lépésben olvasd ki a hajtott tagok szögét a
  `Transform2`-ből, és hasonlítsd össze az elvárt áttétellel.
- **Motion study:** minden újraépítés után újra kell hozzáadni a motort. A fő illesztés-gráf egy
  szabadságfokú legyen, különben a szimuláció nem egyértelmű.

## Ütközésvizsgálat

- `inspect_interference(asm, treat_subassemblies_as_components=...)`.
  - Saját, több részegységből álló mechanizmus: `False`, hogy a részegységek közti ütközés is
    látsszon.
  - Importált STEP (pl. NYÁK sok alkatrésszel): `True`, mert különben a modell belső átfedései
    tömegesen hamis találatot adnak.
- A szándékos pressz-illesztés (szorítóborda, hatszögcsap-csúcs) találatként jelenik meg. Darabszám
  és térfogat alapján azonosítsd: azonos térfogatú, várt darabszámú csoportok.
- Egy tétel = egy összefüggő átfedési térfogat, nem egy komponenspár. Egy hatszögcsap egy furatban
  6 tételt ad (csúcsonként egyet), 3 szorítóborda egy fejen 3 tételt. A várt szám ennek megfelelően
  számolandó.
- A nulla találat nem bizonyítja a működést. Elnyomott komponens és túl nagy hézag is nullát ad.
- Futtasd újra minden paraméterváltozás után.
- Menetes pár: a furatot a névleges átmérőn modellezd (M10: Ø10, M4: Ø4), menetprofil nélkül. A
  magátmérős furatba a névleges csavar vagy orsó belelóg. A felhasználó ezt látja hibának (a rúd
  "átmegy" a furat falán), és az ütközésvizsgálatot is elszennyezi. Ha a rajz tömege a magátmérővel
  számol, a tömeget azzal ellenőrizd, utána bővítsd a furatot névlegesre. A várt ütközésszám így 0.
- Szemrevételezés metszetben: `ellenorzes.section_image` minden furatos kapcsolatra (csap, csavar,
  tengely). A vágósík a furat tengelyén menjen át. A darabszám nem mutatja, hol az átfedés; a metszet igen.
- Csavar iránya: ellenőrizd, hogy a fej kívül van. A fordított csavar a fejével a lemezbe lóg, és
  ugyanolyan darabszámú, de nagyobb térfogatú átfedést ad.
