"""Windowless scheduled launcher; the bridge gets valid, hidden console pipes."""
import argparse
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collector-root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--log-path', type=Path)
    args = parser.parse_args()
    root = args.collector_root
    log = args.log_path or root / '.local' / 'bridge-run.jsonl'
    record = {'host': os.environ.get('COMPUTERNAME', ''),
              'launcher': 'windowless',
              'console_attached': bool(ctypes.windll.kernel32.GetConsoleWindow()),
              'started_at': datetime.now().astimezone().isoformat(),
              'exit_code': 1, 'status': 'failed', 'error_type': None,
              'config_readable': None}
    try:
        result = subprocess.run(
            [str(root / '.venv' / 'Scripts' / 'python.exe'), str(root / 'tools' / 'codex_bridge.py')],
            stdin=subprocess.DEVNULL, capture_output=True, encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=100)
        record['exit_code'] = result.returncode
        record['status'] = 'sent' if result.returncode == 0 else 'failed'
        if result.returncode:
            match = re.search(r'\b([A-Za-z]+Error)\b', result.stdout + result.stderr)
            record['error_type'] = match[1] if match else 'BridgeError'
    except Exception as error:
        record['error_type'] = type(error).__name__
    if record['exit_code']:
        try:
            with (root / '.local' / 'bridge-config.json').open('rb'):
                pass
            record['config_readable'] = True
        except OSError:
            record['config_readable'] = False
    record['finished_at'] = datetime.now().astimezone().isoformat()
    try:
        # Do not log raw subprocess output or pairing credentials.
        with log.open('a', encoding='utf-8') as output:
            output.write(json.dumps(record) + '\n')
    except OSError:
        return 1
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
