"""Exercise the real hidden-task runner without Codex or pairing credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import venv


@unittest.skipUnless(os.name == 'nt', 'Windows Task Scheduler runner')
class BridgeRunnerTest(unittest.TestCase):
    def test_exit_status_and_fail_closed_logging(self):
        runner = Path(__file__).resolve().parents[1] / 'tools' / 'run_bridge.ps1'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venv.EnvBuilder(with_pip=False).create(root / '.venv')
            (root / 'tools').mkdir()
            bridge = root / 'tools' / 'codex_bridge.py'
            log = root / 'result.jsonl'

            def run(log_path=log):
                return subprocess.run([
                    'powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(runner),
                    '-CollectorRoot', str(root), '-LogPath', str(log_path),
                ], capture_output=True, timeout=30)

            bridge.write_text('print("sent")\n', encoding='utf-8')
            self.assertEqual(run().returncode, 0)
            record = json.loads(log.read_text(encoding='utf-8-sig').splitlines()[-1])
            self.assertEqual(record['status'], 'sent')
            self.assertEqual(record['exit_code'], 0)
            self.assertTrue(record['host'])

            bridge.write_text('print("secret must not be logged")\nraise SystemExit(7)\n', encoding='utf-8')
            self.assertEqual(run().returncode, 7)
            self.assertNotIn('secret', log.read_text(encoding='utf-8-sig'))
            record = json.loads(log.read_text(encoding='utf-8-sig').splitlines()[-1])
            self.assertEqual(record['status'], 'failed')
            self.assertEqual(record['exit_code'], 7)

            bridge.write_text('pass\n', encoding='utf-8')
            self.assertEqual(run(root / 'missing' / 'result.jsonl').returncode, 1)

            bridge.unlink()
            self.assertNotEqual(run().returncode, 0)
