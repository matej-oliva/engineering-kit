"""Release page notes come from exactly one changelog section."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parent / 'release_notes.py'
CHANGELOG = """# Changelog

Intro.

## 1.1.0, 2026-11-01

- Newer.

## 1.0.10, 2026-10-30

- Not 1.0.1.

## 1.0.1, 2026-10-21

Contract unchanged.

- Fixed.

## 1.0.0, 2026-10-20, first supported release

- Older.
"""


class ReleaseNotes(unittest.TestCase):
    def run_script(self, version, tmp):
        path = Path(tmp) / 'CHANGELOG.md'
        path.write_bytes(CHANGELOG.encode())
        return subprocess.run([sys.executable, str(SCRIPT), version, str(path)], capture_output=True, text=True)

    def test_prints_only_the_named_section(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            done = self.run_script('1.0.1', tmp)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout, 'Contract unchanged.\n\n- Fixed.\n')
            self.assertEqual(self.run_script('1.0.0', tmp).stdout, '- Older.\n')

    def test_an_unknown_version_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            done = self.run_script('2.0.0', tmp)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn('no section for 2.0.0', done.stderr)


if __name__ == '__main__':
    unittest.main()
