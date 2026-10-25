"""Prepare a private, paired extension folder. Does not install the extension."""
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

from codex_bridge import load_config, save_config

root = Path(__file__).resolve().parent.parent
target = root / ".local" / "browser-extension"
config_path = root / ".local" / "browser-bridge-config.json"
target.mkdir(parents=True, exist_ok=True, mode=0o700)
if os.name == "nt":
    owner = subprocess.check_output(["whoami"],text=True).strip()
    subprocess.run(["icacls",str(target),"/inheritance:r","/grant:r",owner+":(OI)(CI)F","SYSTEM:(OI)(CI)F"],check=True,stdout=subprocess.DEVNULL)
if config_path.exists():
    url, token = load_config(config_path)
else:
    token = secrets.token_urlsafe(40)
    code = """import sys,json,sqlite3
from werkzeug.security import generate_password_hash
token=json.loads(sys.stdin.read())
db=sqlite3.connect('/home/zoli/mini-pi/instance/mini_pi.sqlite',timeout=15)
row=db.execute("SELECT value FROM settings WHERE key='browser_token_hash'").fetchone()
if row and json.loads(row[0]): raise SystemExit('Existing browser token; refusing to overwrite')
with db: db.execute("INSERT INTO settings(key,value) VALUES('browser_token_hash',?)",(json.dumps(generate_password_hash(token)),))
db.close()
print('PAIRED')
"""
    encoded=base64.b64encode(code.encode()).decode()
    remote="/home/zoli/mini-pi/.venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\""
    result=subprocess.run(["ssh","-F",str(Path.home()/".ssh"/"mini_pi_config"),"mini-pi",remote],input=json.dumps(token),capture_output=True,text=True,timeout=20)
    if result.returncode or result.stdout.strip()!="PAIRED":
        raise SystemExit('Pairing failed; existing token was not changed')
    url="http://192.168.50.246:8080"
    save_config(config_path,url,token)
for source in (root/"browser_extension").iterdir():
    if source.is_file():
        shutil.copy2(source,target/source.name)
bootstrap=target/"bootstrap.json"
bootstrap.write_text(json.dumps({"url":url,"token":token,"enabled":True}),encoding="utf-8")
bootstrap.chmod(0o600)
token=None
print('Private paired extension prepared:',target)
