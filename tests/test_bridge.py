import tempfile
from pathlib import Path
import unittest

from tools.codex_bridge import counters, load_config, save_config


class BridgeTest(unittest.TestCase):
    def test_missing_and_zero_are_different(self):
        cards = counters({"rateLimits": {"primary": {"usedPercent":100,"windowDurationMins":300,"resetsAt":1792915200}}})
        self.assertEqual(cards[0]["remaining"], 0)
        self.assertEqual(cards[0]["label"], "Codex · 5 órás keret")
        self.assertIsNone(cards[1]["remaining"])

    def test_codex_bucket_has_priority_over_legacy(self):
        cards = counters({"rateLimits": {"primary":{"usedPercent":99}}, "rateLimitsByLimitId":{"codex":{"primary":{"usedPercent":20,"windowDurationMins":10080}}}})
        self.assertEqual(cards[0]["remaining"],80)
        self.assertEqual(cards[0]["label"],"Codex · heti keret")
        with self.assertRaises(RuntimeError):
            counters({"rateLimits": {"primary":None}})

    def test_config_round_trip_does_not_store_plaintext_on_windows(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"bridge.json"
            save_config(path,"http://localhost:8080","test-only-credential")
            self.assertEqual(load_config(path),("http://localhost:8080","test-only-credential"))
            self.assertNotIn("test-only-credential",path.read_text())
            if os.name=="nt":
                self.assertIn('"protected": true',path.read_text())
