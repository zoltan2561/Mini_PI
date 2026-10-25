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

## Legfontosabb nyitott feladat: STEEL időzített Codex-küldés

A felhasználó a friss csomagot a STEEL-en sikeresen futtatta:

```text
Codex CLI megtalalva: C:\Program Files\WindowsApps\OpenAI.Codex_26.1016.6573.0_x64__2p2nqsd0c76g0\app\resources\codex.exe
Sajat gephez vedett parositas elkeszult.
Codex keretek frissítve.
MiniPI-CodexBridge Ready
```

Az első kézi adatküldés sikerült, az időzített feladat viszont hibás:

```text
LastRunTime    : 2026. 10. 25. 9:04:10
LastTaskResult : 1
NextRunTime    : 2026. 10. 25. 9:06:09
```

A hiba oka még nem ismert. A laptopon a rejtett `pythonw.exe` futásból a Store-os CLI felismerése, a Codex-lekérdezés és a DPAPI-párosítás olvasása is sikeresen lefutott. Ez a STEEL hibáját nem cáfolja, de nem indokol általános `pythonw`-hibát állítani.

A legutóbb elküldött diagnosztika a STEEL feladatának actionjét rejtett PowerShell + `python.exe` futásra állítja, és az eredményt ebbe írja:

```text
D:\GITHUB\P_config\.local\bridge-run.log
```

A felhasználó ezt még nem igazolta vissza. Először olvasd ki a valódi task actiont, principalt és a naplót; ne kérj újabb csomagletöltést találgatott javításhoz.

```powershell
Get-ScheduledTaskInfo -TaskName MiniPI-CodexBridge |
  Format-List LastRunTime,LastTaskResult,NextRunTime
(Get-ScheduledTask -TaskName MiniPI-CodexBridge).Actions |
  Format-List Execute,Arguments,WorkingDirectory
(Get-ScheduledTask -TaskName MiniPI-CodexBridge).Principal |
  Format-List UserId,LogonType,RunLevel
Get-Content D:\GITHUB\P_config\.local\bridge-run.log
```

Figyelem: a jelenlegi `tools/install_bridge.ps1 -UpdateExisting` a meglévő actiont megőrzi. Emiatt a telepítő újrafuttatása önmagában nem cseréli le a korábbi vagy diagnosztikai actiont.

A Pi-n korábban kézi módban volt a Codex-kártya; ezt automatikusra visszakapcsoltuk. A kézi módú kártyát a szerver szándékosan nem írja felül, miközben a régebbi kliens még általános sikerüzenetet írhat. Ellenőrizd a tényleges adatbázis- vagy `/api/display` frissítési időt is.

Sikerfeltétel: legalább két, időzítetten indult sikeres küldés a STEEL-ről, friss Pi-adattal. A laptopos küldő maradjon működő tartalék, amíg ez nincs bizonyítva; utána a felhasználó kérésének megfelelően leállítható. A Pi érkezési ideje önmagában nem igazolja a STEEL-forrást, amíg mindkét küldő fut.

## Grok, Instagram, TikTok

- Felhasználói cél: Grok előfizetés maradék heti kerete; Instagram `zoltan.ppp`, TikTok `@zoltan.ppp` követőszám. Facebook-oldalt még nem adott meg.
- A `browser_extension/` MV3-bővítmény elkészült. Kétpercenként a bejelentkezett Grok használati oldalát és a két konkrét profilt olvassa; csak számokat küld a Pi `/api/ingest/browser` végpontjára. Nem másol cookie-t vagy bejelentkezést.
- A felhasználó engedélyezte a bővítmény betöltését, majd az állandó STEEL gépet választotta gyűjtőnek. A STEEL-en a betöltés és a három sikeres küldés még nem igazolt. A laptopon nem telepítettük.
- A párosított STEEL-csomag `browser_extension/bootstrap.json` fájlját a telepítő készíti el. Ez privát fájl, Gitből nem pótolható. A tiszta forrás `browser_extension/` könyvtára nem tartalmaz kulcsot.
- STEEL Chrome: `chrome://extensions` → Fejlesztői mód → Kicsomagolt bővítmény betöltése → `D:\GITHUB\P_config\browser_extension`. A STEEL saját böngészőjében kell bejelentkezni a szolgáltatásokba. A Chrome-nak és a Windows-felhasználói munkamenetnek futnia kell.
- Átadáskor a Grok-kártya még kézi, az Instagram/TikTok nincs bekötve. Ne állíts kész, automatikus kapcsolatot a bővítmény élő ellenőrzése nélkül.
- A bővítmény szándékosan figyeli a pontos profilt és URL-t. Másik profilra navigálás, hiányzó/kerekített számláló, login vagy CAPTCHA esetén nem küld hibás nullát. Utolsó adat megmarad, tíz perc után elavulási jelzéssel.

## Ellenőrzések és megőrzés

- Legutóbb 15 backend/bridge teszt és 14 JavaScript számlálófeldolgozási ellenőrzés sikeres volt. Utána 3 célzott CLI-felismerési teszt és a tényleges helyi Store-CLI felismerése is sikerült.
- A Pi-n a párosított telepítő a `instance/steel-collector.zip` fájl; adminbelépés után tölthető le, 600-as fájljoggal. Nem tartozik Gitbe.
- A kulcsok, titkos ZIP-ek, adatbázisok, fotók, SSH-kulcsok és Windows DPAPI-fájlok nem kerülnek Gitbe. A forrásfrissítés nem cserélheti le a Pi `instance/` mappáját.
- A laptopos adatküldő kezelése a laptop Windows-feladatütemezőjében történik. Ezt a STEEL Codex-környezetéből külön elérés nélkül ne tekintsd módosíthatónak.
