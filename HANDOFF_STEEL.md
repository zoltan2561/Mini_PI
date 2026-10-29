# Folytatás a STEEL-Legend Codex-környezetében

Átadás: 2026-10-25, Europe/Budapest. A felhasználó kifejezetten kéri a forrás GitHubra feltöltését és a munka folytatását a STEEL gépen.

## Projekt és gépek

- Tároló: `https://github.com/zoltan2561/Mini_PI`.
- Fejlesztési checkout a laptopon: `D:\Mini_PI`.
- Meglévő adatgyűjtő telepítése a STEEL-en: `D:\GITHUB\P_config`. Az ottani privát párosítási fájlokat, `.local/` és `.venv/` tartalmát meg kell őrizni. A Gitben szereplő, titokmentes forrás nem helyettesíti a párosított telepítést.
- Ha nincs megfelelő Git-checkout a STEEL-en, külön mappába klónozz; ne alakítsd át vagy írd felül vakon a meglévő `P_config` könyvtárat.
- STEEL-Legend utoljára feloldott címe: `192.168.50.102`. A laptopról az SSH/WinRM nem volt elérhető, a megosztás hozzáférést megtagadott. A felhasználó maga futtatja a parancsokat a STEEL-en.
- Pi: Raspberry Pi 4B, Debian 13, SPI ILI9486 TFT, 480×320. SSH: `zoli@192.168.50.245:22` Etherneten; Wi-Fi `192.168.50.246`, SSID `PPP_LAN`. Jelszó nincs a forrásban. A STEEL saját SSH-hozzáférését szükség esetén külön kell beállítani.
- Pi alkalmazás: `/home/zoli/mini-pi`; adat: `/home/zoli/mini-pi/instance`; admin: `http://192.168.50.246:8080/admin`.

## Ami működik

- Flask/SQLite/Waitress szerver, telefonos admin, jelszavas belépés, CSRF-védelem, képfeltöltés és diavetítés, állítható statisztikakártyák, éjszakai óranézet.
- Pi szerver: `mini-pi.service` rendszer-szolgáltatás. Kioszk: `mini-pi-kiosk.service` felhasználói szolgáltatás, labwc autostarttal.
- A kezdeti fekete kép a `wlr-randr --output SPI-1 --custom-mode 480x320@60Hz --on` paranccsal megszűnt. A felhasználó a fizikai tesztábrát is látta; az újraindítás utáni automatikus indulás ellenőrzött.
- A Chrome fordítási ajánlata kikapcsolva a saját kioszkprofilban; magyar nyelv és `notranslate` jelölés beállítva.
- A laptopos `MiniPI-CodexBridge` feladat kétpercenként működik. Az átadáskor ismét engedélyezett: utolsó ellenőrzött futás 09:12:30, eredmény 0; Pi-adat frissült 09:12:37-kor. A költözés még nem zárható le.

## STEEL időzített Codex-küldés: 2026-10-25-i hibajavítás

- A tényleges futtatógép `STEEL-Legend`, a forrás checkoutja `D:\GITHUB\Mini_PI`, a párosított gyűjtő továbbra is `D:\GITHUB\P_config`.
- A 09:26 és 09:28 időzített futás `PermissionError` hibát adott. A `.local` mappa tulajdonosa a rendszergazdák csoportja volt; ACL-je SYSTEM, rendszergazdák és tulajdonosi jogok hozzáférését tartalmazta. A korlátozott `yoli9` task nem olvashatta a párosítási fájlt. A 09:28-as diagnosztika: `config_readable=false`.
- A régi diagnosztikai action a nem írható `.local/bridge-run.log` fájlba irányított, majd `exit $LASTEXITCODE` parancsot futtatott. Ez 0-t is jelentett tényleges küldés nélkül; a korábbi 0-s eredmények nem bizonyítékok.
- A felhasználó külön jóváhagyással és saját PowerShellből a `yoli9` SID-nek csak RX jogot adott a `.local` mappára és R jogot a `bridge-config.json` fájlra. A kulcs tartalma, DPAPI-védelme és a többi jogosultság megmaradt.
- A reggeli javítás rejtett PowerShellből indította a `run_bridge.ps1` fájlt. Ezt az esti ablakfelugrás-javítás felváltotta; a jelenlegi actiont lásd alább. A principal, a párosítás és a PT2M ütemezés megmaradt.
- Helyi, Gitből kizárt bizonyítékok: `.local/steel-bridge-run.jsonl` (gép, kezdet/vég, kilépési kód, hibatípus); `.local/steel-pi-evidence.jsonl` (Pi API-visszaolvasások); `.local/steel-task-before*.xml` (actioncsere előtti taskmentés). Ezek nem tartalmaznak kulcsot.
- A runner jelenleg a forrás checkoutjára hivatkozik: a `D:\GITHUB\Mini_PI` könyvtárat ne mozgasd el a task action frissítése nélkül.
- A javító parancs: `& D:\GITHUB\Mini_PI\tools\repair_steel_bridge.ps1`. Csak az actiont cseréli, előbb taskmentést készít; a Windows-feladat módosítása a Codex-folyamatból hozzáférés-megtagadást adott, ezért a felhasználó futtatta.
- Új telepítésnél a `.local` könyvtár PowerShellből létrejön a Python-párosítás előtt, így örökli a csomag felhasználói engedélyét. A csomagkészítő már a runnert is csomagolja; a Pi-n tárolt ZIP-et ebben a körben nem cseréltük. A `tools/install_bridge.ps1 -UpdateExisting` továbbra is megőrzi az actiont; a szándékos cseréhez `-RepairAction` is szükséges.

A kétperces STEEL Codex-frissítés igazolt, három egymást követő automatikus futással (Europe/Budapest, 2026-10-25):

| STEEL indítás | Befejezés | Task/runner eredmény | Pi Codex updated_at |
| --- | --- | --- | --- |
| 09:30:11 | 09:30:17 | 0 / sent | Később olvasva; külön forrásként nem használtuk |
| 09:32:11 | 09:32:17 | 0 / sent | 09:32:18.236900 |
| 09:34:11 | 09:34:17 | 0 / sent | 09:34:18.088695 |

A két utolsó Pi-frissítés között 119,852 másodperc telt el. A Pi-visszaolvasás 09:32:21 és 09:34:32 szerveridőnél történt; mindkétszer `source=codex`, érték 61. A helyi runner `host=STEEL-LEGEND` rekordjai bizonyítják az időzített STEEL-küldést, nem pusztán a közös Pi-beérkezésre támaszkodunk. A task ismétlődése PT2M; utolsó eredménye 0, következő futása az ellenőrzéskor 09:36:09. Kézi taskindítást nem végeztünk.

A laptopos tartalékot nem állítottuk le; külön laptopelérés nincs. A Codex-átállás bizonyítási feltétele teljesült, a laptopos `MiniPI-CodexBridge` most már a laptop saját Feladatütemezőjében letiltható. A böngészős gyűjtő három szolgáltatásának ellenőrzése továbbra is nyitott.

Ellenőrzések: 3 bridge-, 3 CLI-felismerési és 1 Windows-runner teszt sikeres; 14 böngészős parser-ellenőrzés sikeres. A teljes Python-discovery két importhibával nem futott végig: a rendszer-Pythonból hiányzik a Werkzeug, a gyűjtő környezetéből a Pillow/Werkzeug. Az alkalmazásfüggőségeket nem telepítettük a párosított gyűjtőbe. A négy módosított/új PowerShell-script szintaxisa ellenőrzött.

## Ablakfelugrás javítása: 2026-10-25 este

- A konzolos PowerShell `-WindowStyle Hidden` kapcsolója csak indulás után rejti el az ablakot. A task most közvetlenül a `D:\GITHUB\P_config\.venv\Scripts\pythonw.exe` GUI-indítót használja, a `D:\GITHUB\Mini_PI\tools\run_bridge.pyw` fájllal; PowerShell/CMD nincs az időzített indítási láncban.
- A `.pyw` indító a valódi `codex_bridge.py` fájlt konzolos Pythonnal, érvényes stdin/stdout/stderr csövekkel és `CREATE_NO_WINDOW` jelzővel indítja. Naplózása titokmentes, a hibakódot megőrzi; naplózási hiba esetén 1-et ad vissza. A régi PS runner kompatibilitásból megmaradt.
- A módosítást saját Windows UAC-jóváhagyás után emelt segédfolyamat alkalmazta; az action visszaolvasása igazolta a cserét. A task továbbra is korlátozott felhasználóval fut. Párosítási fájl, ACL, titok és Pi-kód nem változott.
- A telepítő, a javító és a csomagkészítő az új `.pyw` indítót használja/tartalmazza. A javító sikertelen actioncsere esetén hibát ad, és ellenőrzi a mentett actiont.
- Két célzott Windows-runner teszt sikeres. A GUI-indítós teszt valódi `pythonw.exe` folyamatból igazolja a konzol hiányát, a gyermek érvényes kimenetét, a hibakódok megőrzését és a naplózási hiba kezelését. Teljes backendtesztet csak emiatt nem futtattunk újra.
- Első automatikus futás: 20:26:11–20:26:16, `status=sent`, kilépési kód 0, `launcher=windowless`, `console_attached=false`. A Pi Codex-kártya frissült 20:26:18-kor. Második automatikus futás: 20:28:11–20:28:16, szintén `sent`, 0 és `console_attached=false`; a Pi 20:28:18-kor frissült. A kétperces ütemezés és az ablak nélküli futás így két egymást követő körben igazolt.
- Helyi bizonyíték: `.local/windowless-task-update.json`, `.local/windowless-pi-evidence.jsonl`, `.local/steel-bridge-run.jsonl`.

## Kijelző finomítása: Pi-re telepítve, 2026-10-25 10:20

- 8 px belső biztonsági keret, beljebb húzott óra/dátum; a fő kártyaszám 49 helyett 54 px. A szám szükség esetén kisebbre igazodik, hogy növelt betűméretnél se vágódjon le.
- Új `night_mode`: `clock` (halvány óra, kompatibilis alapérték) vagy `blank` (fekete kép). Az adminban választható, az időzítés és az érintéses 30 másodperces felébresztés megmaradt. A háttérvilágítás hardveres kikapcsolását ez nem végzi.
- Élőben mentett és szolgáltatás-újraindítás után visszaolvasott beállítás: `night_enabled=true`, `night_mode=blank`, `night_start=23:00`, `night_end=08:00`; 08:00–23:00 között normál kijelzés. 08:00–23:00 között normál kijelzés működik.
- 20 Python-teszt és 14 parser-ellenőrzés sikeres az elkülönített `.local/qa-venv` környezetben. Playwright: 480×320 kijelző, 390 és 360 px admin, 100/125% betűméret; 23:00/08:00 határidők, fekete/óra mód, érintés és beállításmentés ellenőrzött.
- Helyi előnézet: `.local/display-after.png`; forráscsomag: `.local/mini-pi-display-update.zip` (csak app.py, display.css/js, admin.html). A felhasználó külön jóváhagyásával a négy fájl feltöltve. A távoli kiinduló forrás Git HEAD-del egyezett; a feltöltött fájlok SHA256-ellenőrzése sikeres.
- SSH: a felhasználó külön terminálban, rejtett bevitellel adta meg a jelszót, és jóváhagyta a 192.168.50.245 hostkulcsát. A jelszót nem mentettük fájlba/naplóba, SSH-kulcsot és known_hosts fájlt nem módosítottunk. A kapcsolat lezárult.
- Mentés a Pi-n, az alkalmazás könyvtárán kívül: `/home/zoli/mini-pi-backups/display-20261025T092022533265Z`. Tartalom: a négy eredeti forrásfájl, online SQLite-mentés (600-as jogosultság), előző éjszakai beállítások. Az adatbázist nem cseréltük le; csak a négy jóváhagyott kijelzőbeállítás változott.
- Újraindított szolgáltatások: `mini-pi.service`, `mini-pi-kiosk.service`. Visszaolvasás: szerver `active`, `enabled`; kioszk `active`; labwc autostart marker jelen. Az első health-próba az újraindulás alatt kapcsolódási hibát adott, az automatikus ismétlés már `ok`. Teljes Pi-rebootot nem végeztünk.
- Élő HTTP/API és Playwright 480×320 ellenőrzés sikeres, JavaScript-hiba nélkül. Óra: jobb szél 456 px; dátum: jobb szél 456 px, alsó szél 303,5 px. Kártyaszámok: 54 px, vízszintes/függőleges levágás nélkül. Élő képernyőkép: `.local/display-live-after.png`; telepítési napló: `.local/pi-display-deployment.jsonl`.

## Grok, Instagram, TikTok

- Felhasználói cél: Grok előfizetés maradék heti kerete; Instagram `zoltan.ppp`, TikTok `@zoltan.ppp` követőszám. Facebook-oldalt még nem adott meg.
- A `browser_extension/` MV3-bővítmény elkészült. Kétpercenként a bejelentkezett Grok használati oldalát és a két konkrét profilt olvassa; csak számokat küld a Pi `/api/ingest/browser` végpontjára. Nem másol cookie-t vagy bejelentkezést.
- A felhasználó engedélyezte a bővítmény betöltését, majd az állandó STEEL gépet választotta gyűjtőnek. A felhasználó a STEEL-en betöltötte, és működő küldést jelzett vissza. A Grok `source=browser` állapota és ismételt frissülése a Pi API-jából igazolt; az Instagram/TikTok külön élő ellenőrzése nem történt meg. A laptopon nem telepítettük.
- A párosított STEEL-csomag `browser_extension/bootstrap.json` fájlját a telepítő készíti el. Ez privát fájl, Gitből nem pótolható. A tiszta forrás `browser_extension/` könyvtára nem tartalmaz kulcsot.
- STEEL Chrome: `chrome://extensions` → Fejlesztői mód → Kicsomagolt bővítmény betöltése → `D:\GITHUB\P_config\browser_extension`. A STEEL saját böngészőjében kell bejelentkezni a szolgáltatásokba. A Chrome-nak és a Windows-felhasználói munkamenetnek futnia kell.
- A Grok már automatikus (`source=browser`); a 10:21-es élő kijelzőpróbában 28,03% maradék keretet mutatott. Az Instagram/TikTok állapotát ettől külön kell ellenőrizni.
- A bővítmény szándékosan figyeli a pontos profilt és URL-t. Másik profilra navigálás, hiányzó/kerekített számláló, login vagy CAPTCHA esetén nem küld hibás nullát. Utolsó adat megmarad, tíz perc után elavulási jelzéssel.

## Csak látható kártyák böngészős frissítése: 2026-10-29

- A Pi `/api/display` végpontja az ellenőrzéskor csak a Codex és a Grok bekapcsolt kártyáját adta vissza. Az Instagram és TikTok már ki volt kapcsolva; élő Pi-beállítást nem kellett módosítani.
- A bővítmény 1.0.1 minden frissítési kör előtt lekéri a látható kártyákat. Kikapcsolt kártyához nem nyit és nem tölt újra lapot; a már nyitott lapot nem zárja be. A tartalmi számlálófigyelés és az adatküldés is szünetel, a korábbi kártyaérték megmarad.
- Ha a Pi nem érhető el vagy hibás kártyalistát ad, nem indít közösségi oldalfrissítést. Visszakapcsolás után a következő kétperces körben újra gyűjt. A bővítmény állapotoldala a kikapcsolt kártyákhoz szünetelést jelez.
- A STEEL párosított telepítésében öt titokmentes fájl frissítve: `background.js`, `content.js`, `options.js`, `options.html`, `manifest.json`. A korábbi fájlok mentése `.local/browser-extension-before-20261029-141309`; a bootstrap és Chrome-profil változatlan. A telepített fájlok hash-egyezése ellenőrzött.
- A Chrome az ellenőrzéskor nem futott; a módosítás következő indításkor aktiválódik. Éles böngészős futást most nem indítottunk. A Pi szerverkódja és a Codex ütemezése változatlan.
- `node tests/browser_refresh.cjs`: bekapcsolt/kikapcsolt kártya, visszakapcsolás, adatküldés tiltása, Pi-hiba, hibás válasz, globális kikapcsolás és tartalmi számlálófigyelés ellenőrzött. A 14 parser-ellenőrzés is sikeres.

## Ellenőrzések és megőrzés

- Legutóbb 15 backend/bridge teszt és 14 JavaScript számlálófeldolgozási ellenőrzés sikeres volt. Utána 3 célzott CLI-felismerési teszt és a tényleges helyi Store-CLI felismerése is sikerült.
- A Pi-n a párosított telepítő a `instance/steel-collector.zip` fájl; adminbelépés után tölthető le, 600-as fájljoggal. Nem tartozik Gitbe.
- A kulcsok, titkos ZIP-ek, adatbázisok, fotók, SSH-kulcsok és Windows DPAPI-fájlok nem kerülnek Gitbe. A forrásfrissítés nem cserélheti le a Pi `instance/` mappáját.
- A laptopos adatküldő kezelése a laptop Windows-feladatütemezőjében történik. Ezt a STEEL Codex-környezetéből külön elérés nélkül ne tekintsd módosíthatónak.
