"""Print one release's changelog section, for the release page's notes.

    python3 tests/release_notes.py X.Y.Z [CHANGELOG]
"""
from __future__ import annotations

from pathlib import Path
import sys

CHANGELOG = Path(__file__).resolve().parents[1] / 'CHANGELOG.md'


def notes(changelog: str, version: str) -> str:
    """The body under the heading '## VERSION, ...' up to the next heading of that level."""
    lines, body = changelog.splitlines(), None
    for line in lines:
        if line.startswith('## '):
            if body is not None:
                break
            if line[3:].split(',')[0].strip() == version:
                body = []
            continue
        if body is not None:
            body.append(line)
    if body is None:
        raise SystemExit(f'CHANGELOG.md has no section for {version}')
    return '\n'.join(body).strip() + '\n'


if __name__ == '__main__':
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else CHANGELOG
    sys.stdout.write(notes(path.read_text(encoding='utf-8'), sys.argv[1]))
