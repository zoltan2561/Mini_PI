import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from contextlib import closing

from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app


class MiniPiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = create_app(self.directory.name, testing=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.directory.cleanup()

    def setting(self, name, value):
        with closing(sqlite3.connect(Path(self.directory.name) / "mini_pi.sqlite")) as db:
            with db:
                db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (name, json.dumps(value)))

    def token(self, path="/admin/setup"):
        page = self.client.get(path).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page)[1]

    def login(self):
        code = self.client.get("/api/display").json["setup_code"]
        response = self.client.post("/admin/setup", data={"csrf_token": self.token(), "code": code, "password": "my-test-password-123"})
        self.assertEqual(response.status_code, 302)

    def post(self, path, data):
        return self.client.post(path, data={"csrf_token": self.token("/admin"), **data})

    def test_setup_code_is_only_available_on_device(self):
        self.assertRegex(self.client.get("/api/display").json["setup_code"], r"^\d{6}$")
        state = self.client.get("/api/display", environ_overrides={"REMOTE_ADDR": "192.168.50.99"}).json
        self.assertIsNone(state["setup_code"])
        self.assertTrue(state["needs_setup"])
        self.assertNotIn("session.key", state)

    def test_setup_requires_code_password_and_csrf(self):
        self.assertEqual(self.client.post("/admin/setup", data={}).status_code, 400)
        bad = self.client.post("/admin/setup", data={"csrf_token": self.token(), "code": "wrong", "password": "my-test-password-123"})
        self.assertEqual(bad.status_code, 200)
        self.assertTrue(self.client.get("/api/display").json["needs_setup"])
        self.login()
        self.assertFalse(self.client.get("/api/display").json["needs_setup"])
        self.assertEqual(self.client.get("/admin").status_code, 200)
        other = self.app.test_client()
        self.assertEqual(other.get("/admin").status_code, 302)
        self.assertEqual(other.post("/admin/cards/codex_primary", data={}).status_code, 400)

    def test_manual_value_and_settings_survive_restart(self):
        self.login()
        self.assertEqual(self.post("/admin/cards/facebook", {"label": "Saját Facebook", "value": "12345", "enabled": "on"}).status_code, 302)
        settings = {"title": "Zoli TFT", "mode": "mixed", "slide_seconds": "5", "photo_seconds": "10", "photo_fit": "contain", "font_scale": "100", "orientation": "auto", "night_start": "23:00", "night_end": "07:00"}
        self.assertEqual(self.post("/admin/settings", settings).status_code, 302)
        other = create_app(self.directory.name, testing=True).test_client()
        state = other.get("/api/display").json
        self.assertEqual(state["settings"]["title"], "Zoli TFT")
        card = next(c for c in state["cards"] if c["id"] == "facebook")
        self.assertEqual((card["label"], card["value"], card["source"]), ("Saját Facebook", "12345", "manual"))
        self.assertEqual(self.post("/admin/settings", {**settings, "slide_seconds": "0"}).status_code, 400)
        self.assertEqual(other.get("/api/display").json["settings"]["slide_seconds"], 5)

    def test_ingest_auth_validation_and_atomicity(self):
        self.assertEqual(self.client.post("/api/ingest/codex", json={"cards": []}).status_code, 401)
        self.setting("ingest_token_hash", generate_password_hash("test-bridge-secret"))
        headers = {"Authorization": "Bearer test-bridge-secret"}
        payload = {"cards": [{"id": "codex_primary", "remaining": 82, "resets_at": "2026-10-25T15:00:00+00:00", "label": "Codex · 5 óra"}]}
        self.assertEqual(self.client.post("/api/ingest/codex", json=payload, headers=headers).status_code, 200)
        invalid = {"cards": [{"id": "codex_primary", "remaining": 10}, {"id": "facebook", "remaining": 99}]}
        self.assertEqual(self.client.post("/api/ingest/codex", json=invalid, headers=headers).status_code, 400)
        card = self.client.get("/api/display").json["cards"][0]
        self.assertEqual((card["value"], card["source"]), ("82", "codex"))
        for bad in (-1, 101, "nan", "inf"):
            self.assertEqual(self.client.post("/api/ingest/codex", json={"cards": [{"id": "codex_primary", "remaining": bad}]}, headers=headers).status_code, 400)
        self.login()
        self.post("/admin/cards/codex_primary", {"label": "Codex új név", "value": "82", "enabled": "on"})
        self.assertEqual(self.client.get("/api/display").json["cards"][0]["source"], "codex")
        self.post("/admin/cards/codex_primary", {"label": "Kézi Codex", "value": "42", "enabled": "on"})
        self.client.post("/api/ingest/codex", json=payload, headers=headers)
        self.assertEqual(self.client.get("/api/display").json["cards"][0]["value"], "42")
        self.post("/admin/cards/codex_primary", {"label": "Codex", "value": "42", "enabled": "on", "resume_auto":"on"})
        self.client.post("/api/ingest/codex", json=payload, headers=headers)
        self.assertEqual(self.client.get("/api/display").json["cards"][0]["value"], "82")

    def test_photos_are_reencoded_ordered_and_deleted(self):
        self.login()
        image = io.BytesIO()
        Image.new("RGB", (2400, 1200), "#b8f28b").save(image, "PNG")
        image.seek(0)
        upload = self.post("/admin/photos", {"photo": (image, "../../unsafe.png"), "caption": "Tesztkép"})
        self.assertEqual(upload.status_code, 302)
        photos = self.client.get("/api/display").json["photos"]
        self.assertEqual(len(photos), 1)
        photo = photos[0]
        self.assertRegex(photo["url"], r"^/photos/[a-f0-9]{24}\.jpg$")
        response = self.client.get(photo["url"])
        self.assertEqual(response.status_code, 200)
        with Image.open(io.BytesIO(response.data)) as saved:
            self.assertEqual(saved.size, (1920, 960))
            self.assertEqual(saved.format, "JPEG")
        response.close()
        self.assertEqual(self.post("/admin/photos", {"photo": (io.BytesIO(b"<svg></svg>"), "fake.png")}).status_code, 400)
        self.post(f"/admin/photos/{photo['id']}/toggle", {})
        self.assertEqual(self.client.get("/api/display").json["photos"], [])
        self.post(f"/admin/photos/{photo['id']}/delete", {})
        self.assertEqual(self.client.get(photo["url"]).status_code, 404)

    def test_password_change_invalidates_sessions(self):
        self.login()
        second = self.app.test_client()
        token = re.search(r'name="csrf_token" value="([^"]+)"', second.get("/admin/login").get_data(as_text=True))[1]
        second.post("/admin/login", data={"csrf_token": token, "password": "my-test-password-123"})
        self.assertEqual(second.get("/admin").status_code, 200)
        self.post("/admin/password", {"current_password": "my-test-password-123", "new_password": "new-test-password-456"})
        self.assertEqual(second.get("/admin").status_code, 302)

    def test_reordering_and_visibility(self):
        self.login()
        self.post("/admin/cards/tiktok/move/up", {})
        ids = [c["id"] for c in self.client.get("/api/display").json["cards"]]
        self.assertEqual(ids[-2:], ["tiktok", "instagram"])
        self.post("/admin/cards/tiktok", {"label": "TikTok", "value": ""})
        self.assertNotIn("tiktok", [c["id"] for c in self.client.get("/api/display").json["cards"]])


if __name__ == "__main__":
    unittest.main()
