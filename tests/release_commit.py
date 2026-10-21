"""Make the commit and annotated tag for release X.Y.Z from a clean checkout; never pushes.

The tagged commit leaves out repository-host files such as `.github/`, which the updaters
of earlier releases would count as kit files. It is made on a local branch `release/X.Y.Z`
from HEAD, so the current branch keeps those files. Push only the tag afterwards.

    python3 tests/release_commit.py X.Y.Z
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

KIT = Path(__file__).resolve().parents[1]
HOST_ONLY = ('.github',)


def git(*args, root: Path) -> str:
    done = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f'git {args[0]} failed: {done.stderr.strip()}')
    return done.stdout


def make(root: Path, version: str, python: str = sys.executable) -> str:
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise SystemExit(f'version {version!r} is not MAJOR.MINOR.PATCH')
    if git('status', '--porcelain', '--untracked-files=all', root=root).strip():
        raise SystemExit('the checkout has uncommitted changes; commit or discard them first')
    start = git('rev-parse', '--abbrev-ref', 'HEAD', root=root).strip()
    if start == 'HEAD':
        raise SystemExit('HEAD is detached; switch to the branch the release is made from')
    branch, tag = f'release/{version}', f'v{version}'
    for ref, kind in ((f'refs/heads/{branch}', 'branch'), (f'refs/tags/{tag}', 'tag')):
        if subprocess.run(['git', 'rev-parse', '--verify', '-q', ref], cwd=root, capture_output=True).returncode == 0:
            raise SystemExit(f'the {kind} {ref.split("/", 2)[2]} already exists; a published tag never moves')
    git('switch', '-q', '-c', branch, root=root)
    made = False
    try:
        present = [path for path in HOST_ONLY if (root / path).exists()]
        if present:
            git('rm', '-q', '-r', '--', *present, root=root)
            git('commit', '-q', '-m', f'Leave repository-host files out of release {version}', root=root)
        for args in (['release', version], ['release', version, '--check']):
            done = subprocess.run([python, str(root / 'tools' / 'kit.py'), *args], cwd=root,
                                  capture_output=True, text=True)
            if done.returncode:
                raise SystemExit(f'kit.py {" ".join(args)} failed: {done.stdout}{done.stderr}')
        git('add', 'RELEASE.json', root=root)
        git('commit', '-q', '-m', f'Release {version}', root=root)
        git('tag', '-a', tag, '-m', f'Engineering kit {version}', root=root)
        made = True
        return git('rev-parse', 'HEAD', root=root).strip()
    finally:
        git('switch', '-q', start, root=root)
        if not made:  # leave nothing half made behind, so a rerun starts clean
            git('branch', '-q', '-D', branch, root=root)


if __name__ == '__main__':
    commit = make(KIT, sys.argv[1])
    print(f'Tagged v{sys.argv[1]} at commit {commit} on branch release/{sys.argv[1]}. '
          f'Push the tag only: git push origin v{sys.argv[1]}')
