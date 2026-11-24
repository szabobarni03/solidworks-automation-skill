---
name: gepeszeti-tervezes
description: Gépészeti 3D/2D tervezési munkamódszer SolidWorks COM automatizáláshoz (magyar). Akkor használd, ha alkatrészt, összeállítást vagy műhelyrajzot kell készíteni, vásárolt/átvett STEP modellre kell segédeszközt (befogót, tartót, sablont) tervezni, FDM-nyomtatható alkatrész kell, vagy egy projekt lezárásakor a tanulságokat be kell építeni a skillbe. Kipróbált segédkönyvtárat ad (alkatrész-építő, illesztések, rajz méretaránnyal, törött nézet, átmérő/illesztés méretezés, darabjegyzék, STEP furatelemzés, ütközésvizsgálat), kötelező ellenőrzőlistát és projektlezáró rutint.
---

# Gépészeti tervezés (3D/2D)

Ez a subskill a `solidworks-automation` fölött dolgozik. A szülő adja a COM-kapcsolatot és az
alapfüggvényeket (`scripts/sw_connect.py`, `scripts/sw_assembly.py`, `scripts/sw_measure.py`).
Ez a subskill a munkamódszert, a valódi projektekben bevált megoldásokat és az ellenőrzést adja.

## Mikor kell

- Alkatrész, összeállítás vagy rajz SolidWorksben, szkriptből, megismételhetően.
- Segédeszköz egy meglévő termékre (NYÁK, ház, gép), amelynek STEP modellje van.
- FDM-nyomtatott alkatrész (PLA/PETG), ami tényleg működjön, ne csak jól nézzen ki.
- Műhelyrajz: méretarány, nézetek, metszet, törött nézet, illesztések, darabjegyzék.
- Projekt lezárása: a tanulságok beépítése ebbe a skillbe (lásd lent).

## Munkafolyamat

0. **Bontás és "kész" feltétel.** Nagy célt (gép, motor, jármű) előbb bonts alkatrészekre vagy
   csoportokra, mindegyikhez mérhető "kész" feltétellel (méretek, testszám, referencianézet). Egyszerre
   egy csoport készül, és csak az előző ellenőrzése után jön a következő. Ha a cél egy kép vagy rajz
   kinézete: [kepalapu-modellezes.md](references/kepalapu-modellezes.md), alkatrészenkénti
   összevetéssel és az első eredmény korai megmutatásával.
1. **Méretforrás rögzítése.** Sorrend: CAD/STEP modell > mérés (tolómérő) > adatlap > fotó.
   Minden méret mellé írd oda a forrását. Ami becsült, az legyen külön listában "mérendő" jelöléssel.
   Átvett STEP-nél először ellenőrizd, hogy van-e benne furat: [step-elemzes.md](references/step-elemzes.md).
2. **Paraméterek a szkript tetején.** Minden méret egy nevesített konstans, mm-ben, megjegyzéssel.
   Előfeltétel-ellenőrzés (`checks()`) fusson építés előtt: pl. csavarhúzó-lyuk < fej, borda < párna.
3. **Építés szkriptből.** `scripts/swk.py` `Part` és `Assembly` osztályai. Az illesztésekhez
   referenciatengelyt, -síkot, -pontot építs az alkatrészbe, ne élre/lapra hivatkozz.
   Részletek: [com-alapok.md](references/com-alapok.md), [osszeallitas.md](references/osszeallitas.md).
4. **Ellenőrzés.** Kötelező lista lent. Eredmények JSON-ba és képbe (`scripts/ellenorzes.py`).
5. **Rajz.** `scripts/rajz.py`; a buktatók és a bevált sorrend: [rajz.md](references/rajz.md).
6. **Csomagolás.** Átadási mappa: nyomtatási STL, semleges STEP, összeállítás STEP, képek,
   README a címzett nyelvén (miért jó a konstrukció, méretek forrása, mérendő tételek).
7. **Lezárás.** Tanulságok beépítése a skillbe: [tanulsag-sablon.md](references/tanulsag-sablon.md).

## Kötelező ellenőrzőlista (átadás előtt)

- [ ] Minden alkatrész 1 test (`part_report`: `bodies == 1`), a térfogat és a befoglaló méret ésszerű.
- [ ] Ütközésvizsgálat lefutott. Csak a szándékos pressz-illesztések szerepelnek, darabszámuk egyezik
      a várttal (`interference_report(expected=...)`). Importált STEP alösszeállítás = egy komponens.
      Menetes furat névleges átmérőn: a menetes pár nem ütközés.
- [ ] Metszetkép minden furatos kapcsolatról (`section_image`, a sík a tengelyen át), szemmel átnézve.
- [ ] A kapcsolódó méretek a modellből jönnek. A koordináta-átszámítás egy ismert ponton vissza van
      ellenőrizve (pl. egy furat középpontja a ráhelyezett modellben).
- [ ] Hajtó méret (mechanizmusnál) legalább két értéken újraépítve, ütközés nélkül.
- [ ] Rajz: a lap és a nézet méretaránya visszaolvasva; PDF képpé renderelve és szemmel átnézve.
- [ ] FDM: nincs támaszt igénylő túlnyúlás, nincs törékeny rugalmas elem, van próbadarab a tűrésekhez.
      Részletek: [fdm-segedeszkoz.md](references/fdm-segedeszkoz.md).
- [ ] A "mérendő" lista ott van az átadási README-ben.
- [ ] Referenciakép vagy rajz esetén: minden alkatrészhez van egymás melletti összevető kép
      ugyanabból a nézőszögből, sziluett-egyezés számmal, és az eltérések le vannak írva.
- [ ] Ami projektszkriptben új, általános segédfüggvény lett (több projektben is kellene), az a
      `scripts/` alá került, nem a projektmappában maradt.

Teljes lista és a tipikus hamis eredmények: [ellenorzes.md](references/ellenorzes.md).

## Szkriptek

| Fájl | Tartalom |
|---|---|
| `scripts/transzform.py` | Forgatás/eltolás mátrixok, `transform_data()` a `create_math_transform`-hoz. Tiszta Python, tesztelt. |
| `scripts/swk.py` | `c0`, `m`, `nv`, `byref_int`, `sw`, `open_doc`, `props`, `std_planes`, `set_material` (angol anyagnév a nyelvi anyagkönyvtárra fordítva); `Part` (vázlat, kihúzás, vágás, forgatás, ref. sík (`flip` a másik oldalra)/tengely/pont, körél-élletörés, lemezsarok-élek pontok alapján (`corner_edges`), síkban fekvő kontúrélek (`plane_edges`), lapok irány és sugár szerint (`plane_faces`, `cylinder_faces`) vagy befoglaló dobozzal (`faces_in_box`, pl. zseb összes lapja) és lekerekítésük (`fillet_edges`), hatszög laptávolsággal (`hexagon`) vagy csúcskörrel (`hexagon_corner`), körminta feature-ökből referenciatengely körül (`circular_pattern`), mentés testszám-ellenőrzéssel); `Assembly` (elhelyezés, illesztés, hajtó méret). |
| `scripts/rajz.py` | Lap méretaránnyal, nézet explicit méretaránnyal, darabjegyzék, tételszám, metszet, törött nézet, sugár->átmérő + illesztés + menetszöveg, pontosság, lapközépvonal, megjegyzés, PDF->PNG. |
| `scripts/step_elemzes.py` | STEP import; furatok (hengerfelületek) és komponens-befoglalók JSON-ba. |
| `scripts/ellenorzes.py` | Alkatrész-jelentés, ütközés-összefoglaló várt darabszámmal, nézetképek, metszetkép (`section_image`), tömeg a rajz darabjegyzékéhez (`mass_check`). |
| `scripts/osszevetes.py` | Referenciakép és modellkép egymás mellett, nézőszög-rács, sziluett-egyezés (IoU). Tiszta PIL, tesztelt. |
| `scripts/megjelenes.py` | RealView-megjelenések névelőtag-szabályokkal (összeállítás) vagy egy alkatrész összes testére (`alkatresz`, egyedi színnel is, RealView alatt is a `szines_p2m` másolattal) vagy kijelölt lapjaira (`lapok`), RealView be/ki, árnyékolt nézet élekkel (`elekkel`, mint a rajzok 3D képei), kép egyedi nézőszögből (`forgatas` sorozattal is), szögkeresés, alkatrész és rajza egy összevető képen (`alkatresz_osszevetes`), mozgásvideó képkockái rögzített nézetből, metszetben is (`mozgas_kepkockak`), MP4 ffmpeg-gel, üres háttér levágva (`video`). |
| `scripts/kontur.py` | Lemezkontúr érintő körökből és lekerekített sarkokból, terület előre (tömegbecslés), vázlatba rajzolás. Tiszta Python, tesztelt. |
| `scripts/forgastest.py` | Esztergált profil szakaszokból (hossz, átmérő, élletörés, horony, furat, süllyesztés), térfogat előre. Tiszta Python, tesztelt. |
| `scripts/eval_ellenor.py` | Tesztalkatrész-készlet kiértékelése (`eval/esetek.json`): várt testszám, térfogat, befoglaló méret. Lásd [eval.md](references/eval.md). |

Használat saját projektszkriptből:

```python
import sys
sys.path.insert(0, r"<skill>\subskills\gepeszeti-tervezes\scripts")
from swk import Part, Assembly, MATE_COINCIDENT, MATE_DISTANCE
from transzform import axes, rot_x
import rajz, ellenorzes
```

Futtatás a skill venv Pythonjával (Windows Store `python` alias nem jó).

## Projektlezáró rutin (minden projekt végén)

1. Írd ki a projekt tanulságait a [tanulsag-sablon.md](references/tanulsag-sablon.md) szerint.
2. Ami általános (COM-viselkedés, rajz-buktató, FDM-szabály, ellenőrzési lépés), az kerüljön a
   megfelelő `references/*.md`-be. Ami újrahasznosítható kód, az a `scripts/` alá, docstringben a hibával,
   amit megold.
3. Ügyfél- vagy munkahely-specifikus adat (cégnév, termékméretek, koordináták) **nem** kerül ide:
   a repo nyilvános. Az a projekt saját mappájában és jegyzeteiben marad.
4. Ha a `scripts/` változott és fut a SolidWorks, futtasd az evalt is ([eval.md](references/eval.md)), és
   hasonlítsd a sikerarányt az előzőhöz. Romlás esetén ne commitolj.
5. Futtasd a teszteket (`tests/test_gepeszeti_tervezes.py`), frissítsd a `references/munkamodszer.md`
   "Projektnapló" táblázatát egy általános sorral, és commitolj.
