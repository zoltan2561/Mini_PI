"""Read Codex plan limits without running a model; send only the two counters."""
import argparse
import base64
import ctypes
from ctypes import wintypes
import getpass
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / ".local" / "bridge-config.json"


def protect(data, decrypt=False):
    if os.name != "nt":
        return data
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    api = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not api(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)


def save_config(path, url, token):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = {"url": url.rstrip("/"), "token": base64.b64encode(protect(token.encode())).decode(), "protected": os.name == "nt"}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(content, f)


def load_config(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    raw = base64.b64decode(config["token"])
    if config.get("protected"):
        raw = protect(raw, decrypt=True)
    return config["url"], raw.decode()


def resolve_codex():
    """Find the CLI, including the Store app's CLI; never launch the desktop GUI."""
    executable = shutil.which("codex.exe" if os.name == "nt" else "codex")
    if executable and Path(executable).suffix.lower() not in (".cmd", ".bat", ".ps1"):
        return executable
    if os.name != "nt":
        return None
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()/"AppData"/"Local")))
    standalone = local/"Programs"/"OpenAI"/"Codex"/"bin"/"codex.exe"
    if standalone.is_file():
        return str(standalone)
    # Package metadata is stable across Store updates; app/Codex.exe is the GUI.
    command = "$p=Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1; if($p){[Console]::Write((Join-Path $p.InstallLocation 'app\\resources\\codex.exe'))}"
    try:
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, timeout=20,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        store_path = result.stdout.strip()
        if result.returncode == 0 and store_path and Path(store_path).is_file():
            return store_path
    except (OSError, subprocess.TimeoutExpired):
        pass
    npm = Path(os.environ.get("APPDATA", str(Path.home()/"AppData"/"Roaming")))/"npm"/"node_modules"/"@openai"
    patterns = ("codex/vendor/*/codex/codex.exe", "codex-*/vendor/*/codex/codex.exe",
                "codex/node_modules/@openai/codex-*/vendor/*/codex/codex.exe")
    for pattern in patterns:
        for candidate in npm.glob(pattern):
            if candidate.is_file():
                return str(candidate)
    return None


def read_limits(executable=None):
    executable = executable or resolve_codex()
    if not executable:
        raise RuntimeError("Codex CLI nem található.")
    process = subprocess.Popen([executable, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    messages = queue.Queue()
    def receive():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                pass
        messages.put(None)
    threading.Thread(target=receive, daemon=True).start()
    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
    def result(identifier):
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            try:
                message = messages.get(timeout=max(.1, deadline-time.monotonic()))
            except queue.Empty:
                break
            if message is None:
                raise RuntimeError("A Codex kapcsolat lezárult.")
            if message.get("id") == identifier:
                if "error" in message:
                    raise RuntimeError("A Codex nem adott használati adatot. Ellenőrizd a bejelentkezést.")
                return message.get("result", {})
        raise RuntimeError("A Codex adatlekérdezés időtúllépésbe futott.")
    try:
        send({"id":1,"method":"initialize","params":{"clientInfo":{"name":"mini_pi_dashboard","title":"Mini PI","version":"1.0.0"}}})
        result(1)
        send({"method":"initialized"})
        send({"id":2,"method":"account/rateLimits/read"})
        return result(2)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        process.stdout.close()


def counters(result):
    limits = (result.get("rateLimitsByLimitId") or {}).get("codex") or result.get("rateLimits")
    if not isinstance(limits, dict):
        raise RuntimeError("Ehhez a fiókhoz nem érkezett Codex-keretadat.")
    cards = []
    for name, card_id in (("primary", "codex_primary"), ("secondary", "codex_secondary")):
        window = limits.get(name)
        if not isinstance(window, dict) or window.get("usedPercent") is None:
            cards.append({"id":card_id,"remaining":None,"resets_at":None})
            continue
        used = float(window["usedPercent"])
        if not math.isfinite(used) or not 0 <= used <= 100:
            raise RuntimeError("Érvénytelen Codex-keretadat.")
        minutes = window.get("windowDurationMins")
        label = "heti" if minutes == 10080 else f"{minutes // 60} órás" if isinstance(minutes, int) and minutes % 60 == 0 else f"{minutes} perces" if minutes else "aktuális"
        resets = window.get("resetsAt")
        cards.append({"id":card_id,"remaining":round(100-used,2),"label":f"Codex · {label} keret",
                      "resets_at":datetime.fromtimestamp(resets,timezone.utc).isoformat() if resets else None})
    if all(card["remaining"] is None for card in cards):
        raise RuntimeError("A Codex jelenleg nem közöl keretadatot.")
    return cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--probe", action="store_true", help="Read counters without sending them")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--codex")
    parser.add_argument("--resolve", action="store_true", help="Print the detected CLI path without logging in or querying usage")
    args = parser.parse_args()
    if args.resolve:
        executable = resolve_codex()
        if not executable:
            raise RuntimeError("Codex CLI nem található. A Store-os Codex vagy a külön CLI telepítése szükséges.")
        print(executable)
        return
    if args.configure:
        url = input("Mini PI címe [http://192.168.50.246:8080]: ").strip() or "http://192.168.50.246:8080"
        token = getpass.getpass("Az adminban létrehozott adatküldő kulcs: ")
        if not token or not url.startswith(("http://", "https://")):
            raise RuntimeError("Hiányzó vagy érvénytelen beállítás.")
        save_config(args.config,url,token)
        print("Beállítás mentve. A kulcs Windows alatt DPAPI-val védett.")
        return
    cards = counters(read_limits(args.codex))
    if args.probe:
        print(json.dumps({"cards":cards},ensure_ascii=True))
        return
    url, token = load_config(args.config)
    req = urllib.request.Request(url+"/api/ingest/codex",data=json.dumps({"cards":cards}).encode(),
                                 headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=10) as response:
        if response.status != 200:
            raise RuntimeError("A Mini PI nem fogadta az adatot.")
    print("Codex keretek frissítve.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never emit server bodies, credentials or an unfiltered subprocess log.
        print("Mini PI adatküldő: " + (str(error) if isinstance(error, RuntimeError) else type(error).__name__))
        raise SystemExit(1)
