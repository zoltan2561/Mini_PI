"""Build a private, authenticated-download installer; never prints credentials."""
import json
from pathlib import Path
import zipfile

from codex_bridge import DEFAULT_CONFIG, load_config

root=Path(__file__).resolve().parent.parent
url,codex_token=load_config(DEFAULT_CONFIG)
_,browser_token=load_config(root/'.local'/'browser-bridge-config.json')
target=root/'.local'/'MiniPI-STEEL-collector.zip'
instructions='''MINI PI / STEEL-LEGEND ADATGYUJTO

1. A ZIP-et a STEEL-Legend gepen csomagold ki egy allando helyre, peldaul D:\\Mini_PI_Collector.
2. A STEEL-en a Codex legyen telepitve, sajat fiokkal bejelentkezve; Python 3 is szukseges.
3. PowerShellben, a kicsomagolt mappabol futtasd: .\\tools\\start_steel_collector.ps1
4. Chrome: chrome://extensions > Fejlesztoi mod > Kicsomagolt bovitmeny betoltese > browser_extension mappa.
5. A Grok, Instagram es TikTok hatterlapokon jelentkezz be, ha kerik.
6. A bovitmeny beallitasaiban ellenorizd a harom sikeres kuldest.

A Codex ketpercenkent frissul. A Chrome-adatkuldo szinten ketpercenkent olvas.
A Chrome-nak es a Windows-felhasznaloi munkamenetnek futnia kell.
Nem masolunk Codex- vagy webes bejelentkezesi adatokat a laptoprol.
A csomag korlatozott, csak a Mini PI kartyaertekeit iro kulcsokat tartalmaz.
Ne oszd meg es ne tedd nyilvanos Git-taroloba!
'''
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as package:
    for name in ['codex_bridge.py','install_bridge.ps1','run_bridge.ps1','run_bridge.pyw','start_steel_collector.ps1']:
        package.write(root/'tools'/name,'tools/'+name)
    for source in (root/'browser_extension').iterdir():
        if source.is_file():package.write(source,'browser_extension/'+source.name)
    package.writestr('collector-bootstrap.json',json.dumps({'url':url,'codex_token':codex_token,'browser_token':browser_token}))
    package.writestr('START-HERE.txt',instructions)
target.chmod(0o600)
print('Private STEEL collector package ready:',target)
