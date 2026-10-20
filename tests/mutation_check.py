"""Break each guard on purpose and confirm the test suite notices; run before every release.

Each mutant replaces one exact piece of code in a throwaway copy of the kit and runs
the whole suite there. A mutant that leaves the suite passing names a guard no test
protects. Exit status 1 when any survives.

    python3 tests/mutation_check.py [LABEL ...]
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

KIT = Path(__file__).resolve().parents[1]

# (label, file under tools/, exact original text, replacement)
MUTANTS = [
    ('a skipped check counts as a pass', 'kit.py',
     "elif reached('reviewed') and entry['result'] != 'pass':",
     "elif reached('reviewed') and entry['result'] not in ('pass', 'skipped'):"),
    ('verification at any boundary', 'kit.py',
     "if target not in strength or strength[entry['boundary']] < strength[target]:", "if target not in strength:"),
    ('no three-way merge', 'kit_update.py',
     '    merged, clean = merge3(ours, base, theirs)', '    merged, clean = theirs, True'),
    ('links in the project are followed', 'kit_update.py', '        if current.is_symlink():', '        if False:'),
    ('no permission gate', 'kit_update.py', '            if missing:', '            if False:'),
    ('a moved installed tag is accepted', 'kit_update.py',
     "            if base.commit != lock['commit'] or base.manifest['digest'] != lock['digest']:", '            if False:'),
    ('recover reads converted bytes', 'kit_update.py',
     "            read_raw(root, step['path']))", "            read(root, step['path']))"),
    ('recover ignores later changes', 'kit_update.py', "        elif now != step.get('before'):", '        elif False:'),
    ('the journal records unstyled bytes', 'kit_update.py',
     "                      'after': digest_or_none(final)})", "                      'after': digest_or_none(action.content)})"),
    ('integration files need no permission', 'kit_update.py',
     "            if entry.get('permission') not in declared:", '            if False:'),
    ('.git matched with case', 'kit_update.py',
     '    folded = [part.casefold() for part in parts]', '    folded = list(parts)'),
    ('Windows line endings count as edits', 'kit_update.py',
     "    return data.replace(b'\\r\\n', b'\\n') if data is not None else None", '    return data'),
    ('the block keeps a CRLF line break', 'kit_update.py',
     "    for ending in ('\\r\\n', '\\n'):\n        if text.startswith(ending):",
     "    for ending in ('\\n',):\n        if text.startswith(ending):"),
    ('styled on any CRLF', 'kit_update.py', 'if content is not None and consistently_crlf(current):',
     "if content is not None and current is not None and b'\\r\\n' in current:"),
    ('the block is always LF', 'kit_update.py',
     "eol = '\\r\\n' if '\\r\\n' in ours or (not ours.strip() and consistently_crlf(current)) else '\\n'",
     "eol = '\\n'"),
    ('a changed lock is not verified', 'kit.py', '    if lock and lock != earlier:', '    if False:'),
    ('the later configuration names the records', 'kit.py',
     'project = json.loads(show(candidate, PROJECT_FILE)', 'project = json.loads(show(revision, PROJECT_FILE)'),
    ('record folders as patterns', 'kit.py', "(folders.get('tasks') == parent and",
     "(parent.startswith(folders.get('tasks', '\\0').rstrip('*')) and"),
    ('record folders may cover the kit', 'kit.py', 'if record_folder_ok(paths.get(kind))}',
     'if relative_path(paths.get(kind))}'),
    ('the secret allowlist is a process file', 'kit.py', 'if is_record(name) or name in (PROJECT_FILE, LOCK_FILE):',
     "if is_record(name) or name in (PROJECT_FILE, LOCK_FILE, '.engineering-kit/secret-allowlist.json'):"),
    ('the entry block digest is not checked', 'kit.py',
     "if outside[0] == outside[1] and digest(block.encode()) == lock['blocks'][name]:", 'if outside[0] == outside[1]:'),
    ('a second entry block is allowed', 'kit.py',
     'if all(text.count(KIT_BEGIN) == 1 and text.count(KIT_END) == 1 for text in texts):', 'if True:'),
    ('a removed kit file is always accepted', 'kit.py',
     '            if (now is None and expected is None) or (now is not None and digest(now) == expected):',
     '            if now is None or digest(now) == expected:'),
    ('record folders may hold anything', 'kit.py',
     "            if not (path.is_file() and path.suffix == suffix) and path.name != '.gitkeep':", '            if False:'),
    ('the placeholder marker anywhere in a handoff', 'kit.py',
     "if any(line.lstrip('#-* ').startswith(TEMPLATE_MARKER) for line in source.splitlines()):",
     'if TEMPLATE_MARKER in source:'),
]


def survives(label: str, name: str, old: str, new: str) -> bool:
    with tempfile.TemporaryDirectory(prefix='kit-mutant-') as directory:
        copy = Path(directory) / 'kit'
        shutil.copytree(KIT, copy, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        target = copy / 'tools' / name
        source = target.read_text(encoding='utf-8')
        if source.count(old) != 1:
            raise SystemExit(f'{label}: the original text is not in tools/{name} exactly once; update the mutant')
        target.write_text(source.replace(old, new), encoding='utf-8')
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests'], cwd=copy,
                                capture_output=True, text=True, timeout=600)
        return result.returncode == 0


def main(labels: list[str]) -> int:
    chosen = [m for m in MUTANTS if not labels or m[0] in labels]
    survivors = []
    for label, name, old, new in chosen:
        alive = survives(label, name, old, new)
        print(f'{"SURVIVES" if alive else "caught  "}  {label}', flush=True)
        if alive:
            survivors.append(label)
    print(f'{len(chosen) - len(survivors)} of {len(chosen)} mutants caught.')
    return 1 if survivors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
