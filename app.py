"""Mini PI: local dashboard and photo frame. No external services required."""
import functools
import hmac
import io
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

DEFAULT_CARDS = [
    ("codex_primary", "Codex · aktuális keret", "AI", "percent", "#b8f28b"),
    ("codex_secondary", "Codex · második keret", "AI", "percent", "#b8f28b"),
    ("grok", "Grok · maradék keret", "AI", "percent", "#e9d4ff"),
    ("facebook", "Facebook", "Követők", "number", "#8db8ff"),
    ("instagram", "Instagram", "Követők", "number", "#f5a6d4"),
    ("tiktok", "TikTok", "Követők", "number", "#85e5df"),
]
DEFAULT_SETTINGS = {"title": "Zoli / desk", "mode": "mixed", "slide_seconds": 15,
                    "photo_seconds": 20, "photo_fit": "cover", "font_scale": 100,
                    "night_enabled": False, "night_start": "23:00", "night_end": "07:00",
                    "orientation": "auto"}


def now():
    return datetime.now(timezone.utc).isoformat()


def create_app(data_dir=None, testing=False):
    app = Flask(__name__)
    root = Path(data_dir or os.environ.get("MINI_PI_DATA", Path(__file__).parent / "instance"))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    photos = root / "photos"
    photos.mkdir(exist_ok=True, mode=0o700)
    secret_path = root / "session.key"
    if not secret_path.exists():
        fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    app.config.update(SECRET_KEY=secret_path.read_text(), TESTING=testing,
                      MAX_CONTENT_LENGTH=16 * 1024 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                      PERMANENT_SESSION_LIFETIME=60 * 60 * 12, DATA_DIR=str(root))
    attempts = {}
    lock = threading.Lock()

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(root / "mini_pi.sqlite", timeout=15)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys=ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        if "db" in g:
            g.db.close()

    def get_setting(key, default=None):
        row = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(key, value):
        db().execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (key, json.dumps(value, ensure_ascii=False)))

    with app.app_context():
        db().executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cards(
                id TEXT PRIMARY KEY, label TEXT NOT NULL, category TEXT NOT NULL,
                unit TEXT NOT NULL, color TEXT NOT NULL, value TEXT,
                source TEXT NOT NULL DEFAULT 'unconfigured', updated_at TEXT,
                resets_at TEXT, enabled INTEGER NOT NULL DEFAULT 1, position INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS photos(
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, caption TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1, position INTEGER NOT NULL);
        """)
        if get_setting("initialized") is None:
            for key, value in DEFAULT_SETTINGS.items():
                set_setting(key, value)
            set_setting("bootstrap_code", f"{secrets.randbelow(1000000):06d}")
            set_setting("initialized", True)
            for position, card in enumerate(DEFAULT_CARDS):
                db().execute("INSERT INTO cards(id,label,category,unit,color,position) VALUES(?,?,?,?,?,?)", (*card, position))
            db().commit()
        if os.name != "nt":
            os.chmod(root / "mini_pi.sqlite", 0o600)

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_forms():
        if request.method == "POST" and request.endpoint not in ("ingest", "browser_ingest"):
            expected = session.get("csrf", "")
            actual = request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected, actual):
                abort(400, "A munkamenet lejárt. Frissítsd az oldalt.")

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'"
        if request.path.startswith(("/api/", "/admin")) or request.path == "/":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.after_request
    def extension_cors(response):
        if request.path == "/api/ingest/browser":
            origin = request.headers.get("Origin", "")
            if origin.startswith("chrome-extension://"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return response

    def admin_required(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not get_setting("admin_password"):
                return redirect(url_for("setup"))
            if session.get("admin_version") != get_setting("admin_version") or not session.get("admin"):
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapper

    def rate_limit(kind):
        key = (kind, request.remote_addr)
        stamp = time.monotonic()
        with lock:
            for old in [k for k, v in attempts.items() if stamp - v[0] > 300]:
                del attempts[old]
            start, count = attempts.get(key, (stamp, 0))
            if count >= 10:
                abort(429, "Túl sok próbálkozás. Próbáld újra 5 perc múlva.")
            attempts[key] = (start, count + 1)

    def public_state():
        settings = {key: get_setting(key, default) for key, default in DEFAULT_SETTINGS.items()}
        cards = [dict(r) for r in db().execute("SELECT * FROM cards WHERE enabled=1 ORDER BY position,id")]
        images = [dict(r) for r in db().execute("SELECT * FROM photos WHERE enabled=1 ORDER BY position,id")]
        for image in images:
            image["url"] = url_for("photo", filename=image.pop("filename"))
        setup_code = None
        if not get_setting("admin_password") and request.remote_addr in ("127.0.0.1", "::1"):
            setup_code = get_setting("bootstrap_code")
        return {"settings": settings, "cards": cards, "photos": images, "server_time": now(),
                "admin_url": os.environ.get("MINI_PI_ADMIN_URL", "zolitft.local:8080/admin"),
                "needs_setup": not bool(get_setting("admin_password")), "setup_code": setup_code}

    @app.get("/")
    def display():
        return render_template("display.html")

    @app.get("/api/display")
    def display_data():
        return jsonify(public_state())

    @app.get("/health")
    def health():
        db().execute("SELECT 1").fetchone()
        return jsonify(status="ok", app="mini-pi")

    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "icon.svg", mimetype="image/svg+xml")

    @app.route("/admin/setup", methods=["GET", "POST"])
    def setup():
        if get_setting("admin_password"):
            return redirect(url_for("login"))
        if request.method == "POST":
            rate_limit("setup")
            code, password = request.form.get("code", ""), request.form.get("password", "")
            if not hmac.compare_digest(code, get_setting("bootstrap_code", "")):
                flash("A kijelzőn látható beállítási kód nem egyezik.", "error")
            elif len(password) < 10 or len(password) > 200:
                flash("A jelszó 10–200 karakter hosszú legyen.", "error")
            else:
                set_setting("admin_password", generate_password_hash(password))
                set_setting("admin_version", secrets.token_hex(16))
                set_setting("bootstrap_code", None)
                db().commit()
                session.clear()
                session.update(admin=True, admin_version=get_setting("admin_version"))
                session.permanent = True
                return redirect(url_for("admin"))
        return render_template("auth.html", setup=True)

    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        if not get_setting("admin_password"):
            return redirect(url_for("setup"))
        if request.method == "POST":
            rate_limit("login")
            password = request.form.get("password", "")
            if len(password) <= 200 and check_password_hash(get_setting("admin_password"), password):
                session.clear()
                session.update(admin=True, admin_version=get_setting("admin_version"))
                session.permanent = True
                return redirect(url_for("admin"))
            flash("Hibás jelszó.", "error")
        return render_template("auth.html", setup=False)

    @app.post("/admin/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/admin")
    @admin_required
    def admin():
        return render_template("admin.html", settings={k: get_setting(k, v) for k, v in DEFAULT_SETTINGS.items()},
                               cards=[dict(r) for r in db().execute("SELECT * FROM cards ORDER BY position,id")],
                               photos=[dict(r) for r in db().execute("SELECT * FROM photos ORDER BY position,id")],
                               has_bridge=bool(get_setting("ingest_token_hash")),
                               has_browser=bool(get_setting("browser_token_hash")),
                               new_token=session.pop("new_token", None))

    @app.post("/admin/settings")
    @admin_required
    def settings_save():
        try:
            values = {"title": request.form.get("title", "").strip()[:32] or "Mini PI"}
            for key, allowed in {"mode": ["dashboard", "photos", "mixed"], "photo_fit": ["cover", "contain"],
                                 "orientation": ["auto", "landscape", "portrait"]}.items():
                value = request.form.get(key)
                if value not in allowed:
                    raise ValueError()
                values[key] = value
            for key, low, high in [("slide_seconds", 5, 300), ("photo_seconds", 5, 300), ("font_scale", 80, 125)]:
                value = int(request.form.get(key, ""))
                if not low <= value <= high:
                    raise ValueError()
                values[key] = value
            for key in ("night_start", "night_end"):
                value = request.form.get(key, "")
                datetime.strptime(value, "%H:%M")
                values[key] = value
            values["night_enabled"] = request.form.get("night_enabled") == "on"
        except (ValueError, TypeError):
            abort(400, "Érvénytelen kijelzőbeállítás.")
        for key, value in values.items():
            set_setting(key, value)
        db().commit()
        flash("A kijelző beállításai elmentve.")
        return redirect(url_for("admin") + "#display")

    def validate_value(value, unit):
        if value is None or str(value).strip() == "":
            return None
        if unit == "text":
            return str(value).strip()[:24]
        number = float(str(value).replace(",", "."))
        if not math.isfinite(number) or number < 0 or number > 1e15 or (unit == "percent" and number > 100):
            raise ValueError()
        return str(int(number)) if number.is_integer() else str(round(number, 2))

    @app.post("/admin/cards/<card_id>")
    @admin_required
    def card_save(card_id):
        card = db().execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
        if not card:
            abort(404)
        try:
            label = request.form.get("label", "").strip()
            if not label or len(label) > 40:
                raise ValueError()
            value = validate_value(request.form.get("value"), card["unit"])
        except (ValueError, TypeError):
            abort(400, "Érvénytelen érték. A százalék 0 és 100 közötti szám legyen.")
        enabled = request.form.get("enabled") == "on"
        if request.form.get("resume_auto") == "on" and card_id in ("codex_primary", "codex_secondary", "grok", "instagram", "tiktok"):
            db().execute("UPDATE cards SET label=?,enabled=?,source='unconfigured',value=NULL,updated_at=NULL,resets_at=NULL WHERE id=?", (label,enabled,card_id))
            db().commit()
            flash("Az automatikus adatkapcsolat a következő frissítéskor újraindul.")
            return redirect(url_for("admin") + "#cards")
        # Changing visibility or a label must not convert a connected card into a manual one.
        changed = value != card["value"] or request.form.get("make_manual") == "on"
        if changed:
            db().execute("UPDATE cards SET label=?,value=?,enabled=?,source=?,updated_at=?,resets_at=NULL WHERE id=?",
                         (label, value, enabled, "manual" if value is not None else "unconfigured", now() if value is not None else None, card_id))
        else:
            db().execute("UPDATE cards SET label=?,enabled=? WHERE id=?", (label, enabled, card_id))
        db().commit()
        flash("A kártya elmentve.")
        return redirect(url_for("admin") + "#cards")

    @app.post("/admin/cards")
    @admin_required
    def card_add():
        label = request.form.get("label", "").strip()
        unit = request.form.get("unit")
        if not label or len(label) > 40 or unit not in ("number", "percent", "text"):
            abort(400)
        if db().execute("SELECT count(*) FROM cards").fetchone()[0] >= 24:
            abort(400, "Legfeljebb 24 kártya hozható létre.")
        position = db().execute("SELECT coalesce(max(position),0)+1 FROM cards").fetchone()[0]
        db().execute("INSERT INTO cards(id,label,category,unit,color,position) VALUES(?,?,?,?,?,?)",
                     ("custom_" + secrets.token_hex(6), label, "Saját adat", unit, "#f6cb83", position))
        db().commit()
        return redirect(url_for("admin") + "#cards")

    @app.post("/admin/cards/<card_id>/move/<direction>")
    @admin_required
    def card_move(card_id, direction):
        if direction not in ("up", "down"):
            abort(404)
        rows = db().execute("SELECT id FROM cards ORDER BY position,id").fetchall()
        ids = [r[0] for r in rows]
        if card_id not in ids:
            abort(404)
        index = ids.index(card_id)
        target = index + (-1 if direction == "up" else 1)
        if 0 <= target < len(ids):
            ids[index], ids[target] = ids[target], ids[index]
        for position, item in enumerate(ids):
            db().execute("UPDATE cards SET position=? WHERE id=?", (position, item))
        db().commit()
        return redirect(url_for("admin") + "#cards")

    @app.post("/admin/photos")
    @admin_required
    def photo_upload():
        upload = request.files.get("photo")
        if not upload or not upload.filename:
            abort(400, "Válassz ki egy képet.")
        if db().execute("SELECT count(*) FROM photos").fetchone()[0] >= 100:
            abort(400, "Legfeljebb 100 képet tölthetsz fel.")
        image_id = secrets.token_hex(12)
        filename = image_id + ".jpg"
        try:
            raw = upload.read(12 * 1024 * 1024 + 1)
            if len(raw) > 12 * 1024 * 1024:
                raise ValueError()
            with Image.open(io.BytesIO(raw)) as original:
                if original.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError()
                if original.width * original.height > 30_000_000:
                    raise ValueError()
                image = ImageOps.exif_transpose(original)
                image.thumbnail((1920, 1920))
                if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                    rgba = image.convert("RGBA")
                    image = Image.new("RGB", rgba.size, "#131b1a")
                    image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    image = image.convert("RGB")
                image.save(photos / filename, "JPEG", quality=88)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            abort(400, "Érvényes JPG, PNG vagy WebP képet válassz, legfeljebb 12 MB / 30 megapixel méretben.")
        position = db().execute("SELECT coalesce(max(position),0)+1 FROM photos").fetchone()[0]
        caption = request.form.get("caption", "").strip()[:80]
        db().execute("INSERT INTO photos(id,filename,caption,position) VALUES(?,?,?,?)", (image_id, filename, caption, position))
        db().commit()
        flash("A kép feltöltve.")
        return redirect(url_for("admin") + "#photos")

    @app.post("/admin/photos/<image_id>/<action>")
    @admin_required
    def photo_action(image_id, action):
        item = db().execute("SELECT * FROM photos WHERE id=?", (image_id,)).fetchone()
        if not item:
            abort(404)
        if action == "delete":
            db().execute("DELETE FROM photos WHERE id=?", (image_id,))
            db().commit()
            (photos / item["filename"]).unlink(missing_ok=True)
        elif action == "toggle":
            db().execute("UPDATE photos SET enabled=1-enabled WHERE id=?", (image_id,))
            db().commit()
        elif action in ("up", "down"):
            ids = [r[0] for r in db().execute("SELECT id FROM photos ORDER BY position,id")]
            index = ids.index(image_id)
            target = index + (-1 if action == "up" else 1)
            if 0 <= target < len(ids):
                ids[index], ids[target] = ids[target], ids[index]
            for position, item_id in enumerate(ids):
                db().execute("UPDATE photos SET position=? WHERE id=?", (position, item_id))
            db().commit()
        else:
            abort(404)
        return redirect(url_for("admin") + "#photos")

    @app.get("/photos/<filename>")
    def photo(filename):
        if not db().execute("SELECT 1 FROM photos WHERE filename=?", (filename,)).fetchone():
            abort(404)
        return send_from_directory(photos, filename, max_age=86400)

    @app.post("/admin/bridge-token")
    @admin_required
    def bridge_token():
        token = secrets.token_urlsafe(40)
        set_setting("ingest_token_hash", generate_password_hash(token))
        db().commit()
        # Never put this secret in a client-side Flask session cookie.
        return render_template("token.html", token=token)

    @app.post("/admin/browser-token")
    @admin_required
    def browser_token():
        token = secrets.token_urlsafe(40)
        set_setting("browser_token_hash", generate_password_hash(token))
        db().commit()
        return render_template("token.html", token=token, browser=True)

    @app.get("/admin/collector-download")
    @admin_required
    def collector_download():
        return send_from_directory(root, "steel-collector.zip", as_attachment=True,
                                   download_name="MiniPI-STEEL-collector.zip", max_age=0)

    @app.post("/api/ingest/browser")
    def browser_ingest():
        token_hash = get_setting("browser_token_hash")
        header = request.headers.get("Authorization", "")
        if not token_hash or not header.startswith("Bearer ") or len(header) > 200 or not check_password_hash(token_hash, header[7:]):
            abort(401)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("cards"), list) or not 1 <= len(payload["cards"]) <= 3:
            abort(400)
        validated, seen = [], set()
        try:
            for card in payload["cards"]:
                if not isinstance(card, dict) or card.get("id") not in ("grok", "instagram", "tiktok") or card["id"] in seen:
                    raise ValueError()
                card_id = card["id"]
                seen.add(card_id)
                unit = "percent" if card_id == "grok" else "number"
                value = validate_value(card.get("value"), unit)
                if value is None:
                    raise ValueError()
                if unit == "number" and float(value) % 1:
                    raise ValueError()
                validated.append((value, now(), card_id))
        except (ValueError, TypeError):
            abort(400)
        for value, stamp, card_id in validated:
            db().execute("UPDATE cards SET value=?,source='browser',updated_at=?,resets_at=NULL WHERE id=? AND source!='manual'", (value,stamp,card_id))
        db().commit()
        return jsonify(status="ok")

    @app.post("/api/ingest/codex")
    def ingest():
        token_hash = get_setting("ingest_token_hash")
        header = request.headers.get("Authorization", "")
        if not token_hash or not header.startswith("Bearer ") or len(header) > 200 or not check_password_hash(token_hash, header[7:]):
            abort(401)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("cards"), list) or not 1 <= len(payload["cards"]) <= 2:
            abort(400)
        validated = []
        try:
            seen = set()
            for card in payload["cards"]:
                if not isinstance(card, dict) or card.get("id") not in ("codex_primary", "codex_secondary") or card["id"] in seen:
                    raise ValueError()
                seen.add(card["id"])
                value = validate_value(card.get("remaining"), "percent")
                reset = card.get("resets_at")
                if reset:
                    parsed = datetime.fromisoformat(reset)
                    if parsed.tzinfo is None:
                        raise ValueError()
                    reset = parsed.astimezone(timezone.utc).isoformat()
                label = str(card.get("label", ""))[:40]
                validated.append((value, now() if value is not None else None, reset, label, card["id"]))
        except (ValueError, TypeError, OverflowError):
            abort(400)
        for value, stamp, reset, label, card_id in validated:
            db().execute("UPDATE cards SET value=?,source='codex',updated_at=?,resets_at=?,label=CASE WHEN ?='' THEN label ELSE ? END WHERE id=? AND source!='manual'",
                         (value, stamp, reset, label, label, card_id))
        db().commit()
        return jsonify(status="ok")

    @app.post("/admin/password")
    @admin_required
    def password_change():
        old, new = request.form.get("current_password", ""), request.form.get("new_password", "")
        rate_limit("password")
        if len(old) > 200 or not check_password_hash(get_setting("admin_password"), old) or not 10 <= len(new) <= 200:
            abort(400, "Ellenőrizd a jelenlegi jelszót. Az új jelszó legalább 10 karakter legyen.")
        set_setting("admin_password", generate_password_hash(new))
        set_setting("admin_version", secrets.token_hex(16))
        db().commit()
        session.clear()
        return redirect(url_for("login"))

    @app.errorhandler(400)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def friendly_error(error):
        return render_template("error.html", error=error), error.code

    return app


if __name__ == "__main__":
    from waitress import serve
    application = create_app()
    print(f"Mini PI: http://{os.environ.get('MINI_PI_HOST', '0.0.0.0')}:{os.environ.get('MINI_PI_PORT', '8080')}", flush=True)
    serve(application, host=os.environ.get("MINI_PI_HOST", "0.0.0.0"),
          port=int(os.environ.get("MINI_PI_PORT", "8080")), threads=4)
