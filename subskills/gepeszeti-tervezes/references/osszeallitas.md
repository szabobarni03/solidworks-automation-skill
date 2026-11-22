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
