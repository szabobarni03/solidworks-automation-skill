# Eval: mérjük, hogy a skill jobb lett-e

A skill (szabályok, `scripts/`) változása csak akkor javítás, ha a tesztkészleten a sikerarány nem
romlik. Kézi benyomás helyett szám kell.

## A készlet

`eval/esetek.json`: egyszerű, egyértelműen meghatározott alkatrészek szöveges kéréssel. Mindegyikhez
analitikusan számolt várt érték tartozik: testszám, térfogat (mm³), befoglaló méret (mm, nagyság
szerint rendezve). Tűrés: térfogat 0,5%, méret 0,1 mm.

Új eset felvétele: a kérés legyen egyértelmű (minden méret megadva, a tájolás csak a befoglaló
méretre nem hathat). A várt térfogatot képlettel számold, ne a modellből olvasd vissza. Bővítési
irányok: lekerekítés, minta, forgatott profil, lemezalkatrész, kis összeállítás illesztésekkel,
rajzból (PDF/kép) induló kérés.

## Futtatás

1. Új Claude Code munkamenet a skill aktuális állapotával (ne vigyen át a korábbi beszélgetés).
2. Minden esetnél a `keres` szövege a kérés, kiegészítve: "Mentsd ide: `<mappa>/<id>.SLDPRT`".
   A modellező a skill munkafolyamatát követi, utólag kézzel nem javítunk.
3. `python scripts/eval_ellenor.py <mappa> [--elozo <előző eval_eredmeny.json>]`
4. Az eredményt írd be az alábbi naplóba. Romlás esetén a változtatást vissza kell vonni, vagy a
   szabályt pontosítani.

## Napló

| Dátum | Skill commit | Sikerarány | Megjegyzés |
|---|---|---|---|
| 2026-11-24 | a569b63 + mirror, loft, fillet_path, plane_pn (a commit előtt) | 10/10 | Regresszió-ellenőrzés: az eseteket egy szkript építette az aktuális `swk`-val, nem új munkamenet. A skill szabálykövetését ez nem méri, csak azt, hogy a régi függvények nem romlottak. |
