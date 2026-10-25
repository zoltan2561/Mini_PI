"""Pair the local Codex collector over an already authenticated SSH connection."""
import json
from pathlib import Path
import secrets
import subprocess
import sys

from codex_bridge import DEFAULT_CONFIG, save_config


if DEFAULT_CONFIG.exists():
    raise SystemExit("A helyi adatküldő már be van állítva; nem írjuk felül.")
token = secrets.token_urlsafe(40)
remote_script = """import sys, json, sqlite3
from werkzeug.security import generate_password_hash
token = json.loads(sys.stdin.read())
db = sqlite3.connect('/home/zoli/mini-pi/instance/mini_pi.sqlite', timeout=15)
existing = db.execute("SELECT value FROM settings WHERE key='ingest_token_hash'").fetchone()
if existing and json.loads(existing[0]):
    raise SystemExit('An ingest token already exists; refusing to rotate it')
with db:
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('ingest_token_hash',?)", (json.dumps(generate_password_hash(token)),))
db.close()
print('PAIRED')
"""
# Only the code is a process argument. The secret goes through the encrypted SSH stdin.
import base64
encoded = base64.b64encode(remote_script.encode()).decode()
command = "/home/zoli/mini-pi/.venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\""
result = subprocess.run(["ssh", "-F", str(Path.home()/".ssh"/"mini_pi_config"), "mini-pi", command],
                        input=json.dumps(token), capture_output=True, text=True, timeout=20)
if result.returncode != 0 or result.stdout.strip() != "PAIRED":
    raise SystemExit("Nem sikerült a párosítás; meglévő kulcsot nem módosítottunk.")
save_config(DEFAULT_CONFIG, "http://zolitft.local:8080", token)
token = None
print("Codex adatküldő párosítva. A helyi kulcs Windows DPAPI-védelemmel mentve.")
