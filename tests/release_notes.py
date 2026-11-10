"""Print one release's changelog section, for the release page's notes.

    python3 tests/release_notes.py X.Y.Z [CHANGELOG]
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

CHANGELOG = Path(__file__).resolve().parents[1] / 'CHANGELOG.md'
REPO = 'matej-oliva/engineering-kit'


def notes(changelog: str, version: str, repo: str = REPO) -> str:
    """The body under the heading '## VERSION, ...' up to the next heading of that level."""
    lines, body, prev = changelog.splitlines(), None, None
    for line in lines:
        if line.startswith('## '):
            if body is not None:
                prev = line[3:].split(',')[0].strip()
                break
            if line[3:].split(',')[0].strip() == version:
                body = []
            continue
        if body is not None:
            body.append(line)
    if body is None:
        raise SystemExit(f'CHANGELOG.md has no section for {version}')
    text = '\n'.join(body).strip()
    if repo:
        text = re.sub(r'contribution #(\d+)', rf'[contribution #\1](https://github.com/{repo}/pull/\1)', text)
        if prev:
            text += f'\n\n**Full Changelog**: https://github.com/{repo}/compare/v{prev}...v{version}'
    return text + '\n'


if __name__ == '__main__':
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else CHANGELOG
    sys.stdout.write(notes(path.read_text(encoding='utf-8'), sys.argv[1]))
