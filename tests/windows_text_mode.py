"""Run the suite with Windows text-mode newlines on any host; run before every release.

On Windows, a file opened for writing in text mode turns each \\n into \\r\\n. Tests
that write a fixture that way and then compare its bytes pass on Linux and macOS
but fail on Windows. This makes every text-mode write in this process behave as
on Windows, so such a fixture fails here first. Commands the tests start as
subprocesses keep their normal behaviour; the native workflow covers them.

    python3 tests/windows_text_mode.py
"""
from __future__ import annotations

import builtins
import io
from pathlib import Path
import sys
import unittest

_open = io.open


def windows_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
                 opener=None):
    if 'b' not in mode and newline is None and any(flag in mode for flag in 'wax+'):
        newline = '\r\n'
    return _open(file, mode, buffering, encoding, errors, newline, closefd, opener)


def main() -> int:
    io.open = builtins.open = windows_open
    tests = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(tests), top_level_dir=str(tests))
    return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
