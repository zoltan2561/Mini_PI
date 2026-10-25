# Mini PI fejlesztési útmutató

- Magyarul kommunikálj. A folytatás előtt olvasd el a `HANDOFF_STEEL.md` fájlt.
- A Pi szervere és a Windows-adatgyűjtők külön futnak. A helyi teszt, a Pi-n futó alkalmazás és a STEEL időzített küldése külön ellenőrzendő.
- Őrizd meg az `instance/`, `.local/`, `collector-bootstrap.json`, `browser_extension/bootstrap.json` és a meglévő adatgyűjtő telepítés tartalmát. Ezek nem tartoznak Gitbe.
- A felhasználó már engedélyezte a STEEL-re költöztetést és a kétperces Codex-frissítést. A laptopos küldőt csak a STEEL-ről érkező, időzített frissítés bizonyítása után állítsd le.
- Ne változtass kézi értéket automatikusan nullára hiba vagy hiányzó adat miatt. A kézi felülbírálást a gyűjtők tiszteletben tartják.
- Célzott ellenőrzések: `python -m unittest discover -s tests -v`, `node tests/browser_parsers.cjs`. Újrafuttatásukat a változtatás indokolja; dokumentáció vagy puszta feltöltés miatt ne indíts új teljes tesztkört.
