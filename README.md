# Mini PI

Helyben futó dashboard és digitális képkeret Raspberry Pi 4B-re, 480×320-as SPI TFT-vel. Python + Flask + SQLite + Chromium; nincs szükség felhős tárhelyre.

## Használat

- Wi-Fi: `PPP_LAN`, automatikus csatlakozással. Az ellenőrzéskori Wi-Fi-cím `192.168.50.246`, Ethernet-cím `192.168.50.245`.
- Admin: `http://zolitft.local:8080/admin`, vagy a Pi aktuális IP-címe a 8080-as porton.
- Első belépés: a fizikai TFT-n megjelenő hatjegyű kóddal állíts be saját, legalább 10 karakteres jelszót. A kód nem olvasható ki hálózati kliensről, és a beállítás után megszűnik.
- A kijelző érintésére a következő oldal jelenik meg. Éjszakai nézetben az érintés 30 másodpercre felébreszti a dashboardot.
- A kézi adatok és a Codex-adatok forrása, frissítési ideje látható. Tíz percnél régebbi Codex-adat figyelmeztetést kap; a hiányzó adat nem nulla.
- Ha az előfizetés csak egy Codex-keretet közöl, a nem létező második keret nem foglal külön helyet a kijelzőn. A kártya az adminban továbbra is kezelhető.
- A képek helyben, JPEG-ként, legfeljebb 1920×1920-as méretben tárolódnak. A feltöltés legfeljebb 12 MB és 30 megapixel lehet. A fotók sorrendje és láthatósága állítható.
- Az éjszakai nézet lehet fekete kép vagy halvány óra. Az adminban megadható például a 23:00–08:00 időszak; nappal a normál nézet tér vissza. A kijelző háttérvilágításának hardveres kikapcsolása nincs megvalósítva.

## Adatkapcsolatok

**Codex:** a Windows-gépen a `MiniPI-CodexBridge` ütemezett feladat kétpercenként, illetve bejelentkezéskor fut. A helyi, bejelentkezett Codex CLI `account/rateLimits/read` műveletét használja. Nem indít modellhívást, és a Pi nem kap Codex-bejelentkezési adatot. Ha a számítógép nem fut, a kijelzőn megmarad az utolsó érték, elavulási jelzéssel.

A `tools/codex_bridge.py` csak a két Codex-kártyát frissítheti. A kézi módba állított kártyát nem írja felül. Az adminban visszakapcsolható az automatikus adat. A helyi párosítás az ignorált `.local/bridge-config.json` fájlban, Windows DPAPI-védelemmel tárolódik; ez nem hordozható más Windows-felhasználóhoz.

Kézi ellenőrzés:

```powershell
.\.venv\Scripts\python.exe tools/codex_bridge.py --probe
.\.venv\Scripts\python.exe tools/codex_bridge.py
Get-ScheduledTaskInfo -TaskName MiniPI-CodexBridge
```

Újrapárosítás: az admin Kapcsolatok részében készíts új adatküldő kulcsot, majd futtasd a `tools/codex_bridge.py --configure` parancsot. A kulcs rejtett terminálbevitellel adható meg. Az új kulcs érvényteleníti a régit.

**Grok, Instagram, TikTok:** a `browser_extension/` könyvtárban lévő saját Chrome-adatküldő kétpercenként olvassa a bejelentkezett Grok heti használati sávját, az Instagram `zoltan.ppp` és TikTok `@zoltan.ppp` profilok követőszámát. A Groknál a felhasznált százalékot maradék százalékká alakítja. Három háttérlapot tart nyitva; az éppen aktív lapot nem tölti újra. A belépési adatok és cookie-k nem kerülnek a Pi-re. Chrome-futás és érvényes webes bejelentkezés szükséges. Bejelentkezési kérés, CAPTCHA vagy megváltozott oldal esetén az utolsó adat marad meg, tíz perc után elavulási jelzéssel. A kerekített követőszámot (pl. 1.2K) nem állítja be pontos számként. A Grok előfizetéses kerete külön kezelendő az API-költéstől.

A bővítmény telepítése egyszeri felhasználói jóváhagyást igényel. A `tools/prepare_browser_extension.py` előkészíti a privát, párosított mappát a `.local/browser-extension/` helyen; nem telepíti magától. A mappa `bootstrap.json` fájlja korlátozott adatküldő kulcsot tartalmaz: ne oszd meg és ne tedd Gitbe. Windows alatt a mappa csak a saját felhasználó és a SYSTEM számára hozzáférhető. A nyilvánosan megosztható forrás a `browser_extension/` könyvtár, amely nem tartalmaz kulcsot.

Kézi betöltés: `chrome://extensions` → Fejlesztői mód → Kicsomagolt bővítmény betöltése → `D:\Mini_PI\.local\browser-extension`. A bővítmény beállítási oldala megmutatja az utolsó sikeres küldéseket és a hibákat. Az adminban generált új böngészős kulcs a bővítmény beállításaiban cserélhető. Ez a kulcs csak a három megfelelő kártyát frissítheti; a Codex-kulcstól különálló.

**Facebook:** még nincs megadva profil vagy oldal; továbbra is kézzel állítható.

A Codex ütemezésének módosítása a meglévő beállítások megőrzésével:

```powershell
.\tools\install_bridge.ps1 -UpdateExisting -IntervalMinutes 2
```

### Folyamatos működés STEEL-Legend gépről

A STEEL-Legend párosított Codex-küldője a `D:\GITHUB\P_config` mappából fut, kétperces ütemezéssel. A 2026-10-25-i jogosultsági javítást és az élő futások bizonyítékait a [HANDOFF_STEEL.md](HANDOFF_STEEL.md) tartalmazza. A laptopos tartalék leállítása még külön, a laptopon végzendő lépés.

A Pi adminjának Kapcsolatok részében letölthető a **STEEL-Legend telepítő**. A ZIP csak adminbelépés után érhető el, nem cache-elhető, és korlátozott adatküldő kulcsokat tartalmaz. Az `instance/steel-collector.zip` és a helyi `.local/MiniPI-STEEL-collector.zip` nem nyilvános forrásfájl.

A STEEL-en csomagold ki állandó helyre, például `D:\Mini_PI_Collector`, majd a mappából futtasd:

```powershell
.\tools\start_steel_collector.ps1
```

A telepítő ellenőrzi a gép nevét, a Pi elérhetőségét, a Python és a Codex meglétét; a STEEL saját Windows-felhasználójához védi a helyi kulcsot, majd kétperces Codex-feladatot készít. A Chrome-bővítményt ezen a gépen is egyszer be kell tölteni a csomag `browser_extension` mappájából, és a szolgáltatásokba itt kell bejelentkezni. Laptopos webes munkamenetet és Codex-bejelentkezést nem másol át.

A Chrome-nak és a Windows-felhasználói munkamenetnek a STEEL-en is futnia kell. A gép bekapcsolt állapota önmagában nem elég. A laptopos Codex-feladatot csak legalább két sikeres, időzített STEEL-küldés és a Pi-adat frissülésének igazolása után kapcsold ki. A Chrome-bővítmény STEEL-telepítését a felhasználó visszaigazolta; a Grok ismételt automatikus frissülése API-ból is ellenőrzött. Az Instagram/TikTok külön élő ellenőrzése még nem történt meg.

## Pi telepítés és működés

A kiválasztott gépen az alkalmazás helye `/home/zoli/mini-pi`. Az `instance/` tartalmazza az SQLite-adatbázist, a képeket és a munkamenetkulcsot; forrásfrissítéskor ezt a könyvtárat meg kell őrizni.

```sh
cd /home/zoli/mini-pi
sh deploy/install.sh
systemctl status mini-pi.service
systemctl --user status mini-pi-kiosk.service
curl http://127.0.0.1:8080/health
```

A szerver rendszerindításkor indul `zoli` felhasználóként. A kioszkot a meglévő, automatikusan bejelentkező labwc-munkamenet `~/.config/labwc/autostart` fájlja indítja. Meglévő autostart esetén a telepítő időbélyeges másolatot készít, majd megőrzi a korábbi sorokat.

### Fekete SPI kijelző javítása

Az ILI9486 meghajtó ezen a gépen 0,007 Hz-es alapmódot hirdetett. A labwc fekete képet adott. A következő egyedi megjelenítési móddal a tesztábra megjelent; ezt a felhasználó a fizikai kijelzőn is megerősítette:

```sh
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 \
  wlr-randr --output SPI-1 --custom-mode 480x320@60Hz --on
```

A kioszkindító minden indításkor alkalmazza ezt. A beállított mód nem jelent 60 képkocka/másodperces fizikai SPI-átvitelt. A korábbi asztalnaplóban `pcmanfm` / `libfm-gtk3` szimbólumhibák is látszottak; általános rendszerfrissítést vagy asztaljavítást nem végeztünk. A kioszk közvetlenül Chromiumot indít.

A kioszk külön Chromium-profilt használ magyar nyelvvel, kikapcsolt fordítási ajánlatokkal. A `tools/configure_browser.py` csak ezt a profilt módosítja; az oldal maga is `notranslate` jelölésű.

### Visszaállítás

A szerver és a kioszk leállítható:

```sh
systemctl --user stop mini-pi-kiosk.service
sudo systemctl disable --now mini-pi.service
```

Az automatikus kioszkindítás megszüntetéséhez a `~/.config/labwc/autostart` fájlból csak a `MINI_PI_KIOSK_START` és `MINI_PI_KIOSK_END` közötti blokkot távolítsd el, vagy állítsd vissza a telepítő előtti mentést, ha volt. Az alkalmazás adatait ez nem törli.

Windows-adatküldő leállítása:

```powershell
Disable-ScheduledTask -TaskName MiniPI-CodexBridge
```

A fejlesztési SSH-eléréshez külön `mini_pi_codex_ed25519` kulcs készült a Windows-felhasználó `.ssh` mappájában; a Pi `authorized_keys` fájlja a `mini-pi-codex` jelölésű nyilvános kulccsal bővült. Az SSH-jelszó nem került a projektbe. A Wi-Fi-jelszó a Pi NetworkManagerének csak rendszergazdaként olvasható profiljában van.

## Helyi fejlesztés és ellenőrzés

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MINI_PI_HOST='127.0.0.1'
$env:MINI_PI_PORT='8081'
$env:MINI_PI_DATA='D:\Mini_PI\.local\qa'
.\.venv\Scripts\python.exe app.py
```

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A backend-ellenőrzések külön ideiglenes adatbázisokat használnak. A böngészős QA-adatok a `.local/qa/` könyvtárban vannak; a kézi mintaszámok és tesztfotó nem kerülnek a Pi éles adatbázisába. Képernyőmentések: `output/playwright/` (ignorált). A felület külső CDN-t, betűkészletet és képszolgáltatást nem használ.

A rendszer helyi hálózati használatra készült. Az admin jelszóvédett és CSRF-védett, az adatküldő külön kulcsot használ. A kijelző olvasási felülete a helyi hálózaton jelszó nélkül elérhető. Internetes publikálás nincs beállítva.
