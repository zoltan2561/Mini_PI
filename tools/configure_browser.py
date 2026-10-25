"""Configure only Mini PI's own Chromium profile, while its browser is stopped."""
import json
from pathlib import Path

profile = Path.home() / ".config" / "mini-pi-browser" / "Default"
profile.mkdir(parents=True, exist_ok=True)
path = profile / "Preferences"
preferences = json.loads(path.read_text()) if path.exists() else {}
preferences.setdefault("translate", {})["enabled"] = False
preferences.setdefault("intl", {})["accept_languages"] = "hu-HU,hu,en-US,en"
temporary = path.with_suffix(".mini-pi.tmp")
temporary.write_text(json.dumps(preferences), encoding="utf-8")
temporary.chmod(0o600)
temporary.replace(path)
