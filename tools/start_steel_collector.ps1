param([switch]$AllowOtherHost)
$ErrorActionPreference = 'Stop'
$miniRoot = Split-Path -Parent $PSScriptRoot
if (-not $AllowOtherHost -and $env:COMPUTERNAME -notmatch '^STEEL-Legend$') {
    throw 'Ezt a telepitot a STEEL-Legend gepen futtasd. Elt ero nevhez hasznald az -AllowOtherHost kapcsolot.'
}
$miniBootstrapPath = Join-Path $miniRoot 'collector-bootstrap.json'
if (-not (Test-Path -LiteralPath $miniBootstrapPath)) { throw 'Hianyzik a parositott telepitocsomag. A Pi adminjabol letoltott ZIP-et hasznald.' }
$miniHealth = Invoke-RestMethod -Uri 'http://192.168.50.246:8080/health' -TimeoutSec 10
if ($miniHealth.status -ne 'ok') { throw 'A Mini PI nem elerheto.' }
$miniOwner = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $miniRoot /inheritance:r /grant:r ($miniOwner + ':(OI)(CI)F') 'SYSTEM:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'A csomag fajljogosultsagai nem allithatok be.' }
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    & py.exe -3 -m venv (Join-Path $miniRoot '.venv')
} elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    & python.exe -m venv (Join-Path $miniRoot '.venv')
} else { throw 'Python 3 szukseges a Codex adatkuldohoz.' }
if ($LASTEXITCODE -ne 0) { throw 'Nem sikerult a Python kornyezetet letrehozni.' }
$miniPython = Join-Path $miniRoot '.venv\Scripts\python.exe'
$miniCodexPath = & $miniPython (Join-Path $PSScriptRoot 'codex_bridge.py') --resolve
if ($LASTEXITCODE -ne 0) {
    throw 'A Codex CLI nem talalhato. Nyisd meg a Store-os Codexet, vagy telepitsd a kulon CLI-t, majd futtasd ujra a telepitot.'
}
Write-Host ('Codex CLI megtalalva: ' + $miniCodexPath)
# Inherit the collector's explicit user grant. Python 3.13 mkdir(mode=0700)
# under an elevated installer can leave only administrator/owner access.
New-Item -ItemType Directory -Path (Join-Path $miniRoot '.local') -Force | Out-Null
$miniConfigure = @'
import json,sys,pathlib
root=pathlib.Path(sys.argv[1])
sys.path.insert(0,str(root/'tools'))
from codex_bridge import save_config
data=json.loads((root/'collector-bootstrap.json').read_text(encoding='utf-8'))
save_config(root/'.local'/'bridge-config.json',data['url'],data['codex_token'])
(root/'browser_extension'/'bootstrap.json').write_text(json.dumps({'url':data['url'],'token':data['browser_token'],'enabled':True}),encoding='utf-8')
print('Sajat gephez vedett parositas elkeszult.')
'@
$miniConfigure | & $miniPython - $miniRoot
if ($LASTEXITCODE -ne 0) { throw 'A helyi parositas nem sikerult.' }
& $miniPython (Join-Path $PSScriptRoot 'codex_bridge.py')
if ($LASTEXITCODE -ne 0) { throw 'A Codex lekerdezes nem sikerult. Jelentkezz be a Codexbe ezen a gepen, majd futtasd ujra a telepitot.' }
& (Join-Path $PSScriptRoot 'install_bridge.ps1') -IntervalMinutes 2 -UpdateExisting
Write-Host ''
Write-Host 'CODEX: ketpercenkenti adatkuldes telepitve.'
Write-Host 'CHROME: chrome://extensions > Fejlesztoi mod > Kicsomagolt bovitmeny betoltese'
Write-Host ('Valaszd ezt a mappat: ' + (Join-Path $miniRoot 'browser_extension'))
Write-Host 'A Grok/Instagram/TikTok hatterlapokon ezen a gepen is jelentkezz be.'
Write-Host 'A Chrome-nak es ennek a Windows-felhasznaloi munkamenetnek futnia kell.'
Write-Host 'A laptopos adatkuldo csak a STEEL sikeres ellenorzese utan allithato le.'
