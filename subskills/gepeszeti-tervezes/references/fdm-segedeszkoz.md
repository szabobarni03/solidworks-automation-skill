# FDM-nyomtatott segédeszköz (PLA/PETG)

## Tartás rugalmas elem nélkül

- **Ne legyen hasított pattintó horog** kis méretben PLA/PETG-ből. Merev, és a réteghatáron törik.
  A tartás pressz-illesztés és alakzáró kapcsolat legyen.
- **Hatszögletű préscsap kerek furatba.** Csak a 6 csúcs deformálódik, a lapok között helye van a
  kiszorított anyagnak. Bevált értékek egy Ø3,2 furatra:
  - csúcskör = furat + 0,15 mm,
  - egyenes rész = lemezvastagság - 0,2 mm,
  - kúpos bevezető vég 1,2 mm hosszon, 15°-os kúppal.
  Hüvelykujjal benyomható, és tart.
- **Szorítóbordák fészekben.** Egy fejnek való fészek: átmérő = fej + 0,4 mm, mélység > fejmagasság,
  peremén 0,5 mm élletörés. A fészekben 3 kis félhenger-borda (r 0,4) van, a belső körük = fej - 2·0,1 mm.
  Kicsik, ezért deformálódnak, és nem törnek.
- **Merev horog élre, beakasztás + lebillentés.** Az ajak 0,8 mm-rel fog rá, 0,1 mm a rés. A falnál
  0,3 mm a rés, és van 0,5 mm-es bevezető élletörés. Semmi nem hajlik. A csapok akadályozzák meg, hogy
  a horog leakadjon.
- **Lehúzófül** a levételhez.

## Nyomtathatóság

- A lap feküdjön a tálcán, a funkcionális elemek (párna, csap) felfelé nézzenek.
- 0,8-1,2 mm-es túlnyúlás támasz nélkül is nyomtatható. Nagyobbat kerülj el, vagy legyen 45°-os.
- A támasztás csak párnákon legyen. A bordák maradjanak a kapcsolódó felület alatt (pl. 1,5 mm),
  hogy alkatrészt, forrasztást, kiálló tüskét ne érjenek.
- Csavarhúzó-lyuk a fej alatt: kisebb a fejnél, alján 45°-os tölcsérrel, hogy a bit vakon is
  betaláljon.
- Egy zárt test, vízzáró STL. Ellenőrzés: `ellenorzes.part_report`.

## Próbadarab (mindig)

- A pressz-illesztés a nyomtatótól függ. Egy kis próbadarab 3 oszlopban készüljön, különböző
  értékekkel (pl. szorítás 0,05/0,10/0,15, csap-túlfedés 0,05/0,15/0,25). Az oszlopokat pontokkal
  számozd, mert a szám kis méretben olvashatatlan.
- A fő alkatrész a középső értékkel épül. A visszajelzés után csak a paramétert kell átírni.
- A README-ben szerepeljen, mit jelent a "jó": a kapcsolat érezhetően bepattan és tart, és
  hüvelykujjal benyomható.

## Beállítás (kiindulás)

PETG ajánlott (szívósabb), a PLA is megfelel. 0,2 mm rétegmagasság, 3 perem, 30-40 % kitöltés,
támasz nélkül.
