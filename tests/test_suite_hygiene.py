"""The suite's own tests clean up in ways that also work on Windows and macOS."""
from __future__ import annotations

from pathlib import Path
import unittest

TESTS = Path(__file__).resolve().parent
HELPERS = TESTS / 'native_release.py'
CHECKED = [path for path in sorted(TESTS.glob('*.py')) if path not in (HELPERS, Path(__file__).resolve())]


class SuiteHygiene(unittest.TestCase):
    def test_folders_are_removed_with_remove_tree(self):
        # Git object files are read-only on Windows, where a plain rmtree is refused.
        offenders = [path.name for path in CHECKED if 'shutil.rmtree(' in path.read_text(encoding='utf-8')]
        self.assertEqual(offenders, [], 'use remove_tree from native_release')

    def test_scratch_git_runs_without_automatic_maintenance(self):
        # Background maintenance still writing in a scratch repository makes its removal fail.
        offenders = [path.name for path in CHECKED
                     if 'GIT_CONFIG_GLOBAL' in (text := path.read_text(encoding='utf-8')) and 'QUIET_GIT' not in text]
        self.assertEqual(offenders, [], 'add QUIET_GIT from native_release to the Git environment')


if __name__ == '__main__':
    unittest.main()
