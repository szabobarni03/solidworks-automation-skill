# Átvett STEP modell elemzése

## Import

- `sw.LoadFile4(path, "r", sw.GetImportFileData(path), err)`. A több testű STEP összeállítás lesz.
  Mentsd natívra (`step_elemzes.import_step`), és utána azt használd.
- Az import lassú lehet (nagy NYÁK: több száz alkatrész). Csak egyszer importálj. Az elemzést a
  natív fájlon futtasd.

## Először: van-e benne, ami kell?

- Ugyanannak a terméknek több STEP-exportja lehet. Az egyik NYÁK-export ("fabricated") **egyetlen
  fúrt furatot sem tartalmazott**. Egy másik export ("alternative") igen. Ha a furatlista üres vagy
  hiányos, kérj másik exportot, ne becsülj.
- Ellenőrizd a darabszámot és az átmérőket (`hole_diameters`) a várt értékekkel.

## Furatok kiolvasása

- Hengerfelületek a levél alkatrész testén (`GetBodies2`). Alösszeállítás-komponensen `None` jön,
  ezért a levél komponens kell (`not c.GetChildren`).
- `surface.CylinderParams` = `[px, py, pz, ax, ay, az, r]`. Furat, ha a tengely párhuzamos a lap
  normálisával (`|az| = 1`).
- A pontot a komponens `Transform2.ArrayData`-jával vidd át az összeállítás koordinátáiba.
- Egy furathoz több felület is tartozhat (a furatfal felezett felületei). Egyedi kulcs szerint
  gyűjtsd őket.

## Alkatrészek befoglalói

- A felső szintű komponensek doboza: `c.GetBox(False, False)`, méterben. Ebből kiderül, hol vannak a
  csatlakozók, az élek és a kiálló tüskék.
- A segédeszköz kritikus helyein (horog, borda) számold ki a szabad rést a szomszédos befoglalóktól.
  Írd be a paraméter megjegyzésébe.
- A NYÁK alján kiálló THT-tüskék (jellemzően 1,5-2 mm) a befoglalók alsó Z-jéből látszanak. A
  bordák ezek alatt fussanak, vagy kerüljék el őket.

## Koordináta-átszámítás

- Válassz egy referenciafuratot (0, 0). Írd le az átszámítást (pl. `X = y_STEP - a ; Y = b - x_STEP`).
  Tedd a szkript tetejére és az átadási README-be is.
- Az összeállításban a STEP modellt forgatással helyezd el (`transzform.axes`). Ellenőrizd: a
  referenciafurat a lap (0, 0) pontjára kerüljön.
