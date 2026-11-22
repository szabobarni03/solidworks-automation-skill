# Projektlezárás: tanulság-sablon

Minden projekt végén töltsd ki. Ami általános, az kerüljön a megfelelő referenciába vagy szkriptbe.
A projekt-specifikus rész a projekt saját jegyzetében marad. A repo nyilvános, ezért ügyfél- vagy
munkahelyi adat nem kerülhet bele.

```markdown
## <dátum> - <projekttípus, általánosan megfogalmazva>

### Mi működött elsőre
- ...

### Mi nem működött, és mi lett a megoldás
| Tünet (pontos hibaüzenet) | Ok | Megoldás | Hova került |
|---|---|---|---|
| ... | ... | ... | references/<fájl>.md / scripts/<fájl>.py |

### Új, újrahasznosítható kód
- `scripts/<fájl>.py:<függvény>`: mit old meg

### Ellenőrzési lépés, ami hiányzott
- ...

### Tervezési szabály (anyag, gyártás, tűrés)
- ...

### Visszajelzés a felhasználótól (ha van)
- ...
```

## Beépítés lépései

1. Minden "Hova került" sor valóban be van építve (referencia vagy kód).
2. Az új kód docstringje leírja a hibát, amit megold.
3. Egy általános sor a `munkamodszer.md` "Projektnapló" táblázatába.
4. `pytest tests/test_gepeszeti_tervezes.py`, és élő SolidWorks esetén a smoke-teszt.
5. Commit: `docs(gepeszeti-tervezes): <projekttípus> tanulságai`.
