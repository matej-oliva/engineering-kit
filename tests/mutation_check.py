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
    ('a changed lock is not verified', 'kit.py', '    elif lock != earlier:', '    elif False:'),
    ('the later configuration names the records', 'kit.py',
     'project = json.loads(show(candidate, PROJECT_FILE)', 'project = json.loads(show(revision, PROJECT_FILE)'),
    ('records in subfolders count', 'kit.py', "if folders.get('tasks') == parent and leaf.endswith('.json'):",
     "if parent.startswith(folders.get('tasks', '\\0')) and leaf.endswith('.json'):"),
    ('task records of any suffix', 'kit.py', "if folders.get('tasks') == parent and leaf.endswith('.json'):",
     "if folders.get('tasks') == parent:"),
    ('handoffs of any suffix', 'kit.py', "elif folders.get('handoffs') == parent and leaf.endswith('.md'):",
     "elif folders.get('handoffs') == parent:"),
    ('record folders may cover the kit', 'kit.py', 'if record_folder_ok(paths.get(kind))}',
     'if relative_path(paths.get(kind))}'),
    ('the secret allowlist is a process file', 'kit.py', '        if name in (PROJECT_FILE, LOCK_FILE):',
     "        if name in (PROJECT_FILE, LOCK_FILE, '.engineering-kit/secret-allowlist.json'):"),
    ('the entry block digest is not checked', 'kit.py',
     'if now_outside is None or expected is None or digest(block.encode()) != expected:',
     'if now_outside is None or expected is None:'),
    ('entry markers in any order', 'kit.py',
     ' or text.index(KIT_BEGIN) > text.index(KIT_END):\n        return None, None', ':\n        return None, None'),
    ('a removed kit file is always accepted', 'kit.py',
     '            if (now is None and expected is None) or (now is not None and digest(now) == expected):',
     '            if now is None or digest(now) == expected:'),
    ('the placeholder marker anywhere in a handoff', 'kit.py',
     "if any(line.lstrip('#-* ').startswith(TEMPLATE_MARKER) for line in source.splitlines()):",
     'if TEMPLATE_MARKER in source:'),
    ('lock blocks not compared with the release', 'kit.py',
     "if expected_files != lock.get('files') or expected_blocks != lock.get('blocks'):",
     "if expected_files != lock.get('files'):"),
    ('lock commit not compared', 'kit.py', "if problems or release.commit != lock.get('commit') or",
     'if problems or'),
    ('lock release digest not compared', 'kit.py',
     " or release.manifest.get('digest') != lock.get('digest'):", ':'),
    ('unknown integrations ignored', 'kit.py', "if problems or release.commit", 'if release.commit'),
    ('excluded files not filtered', 'kit.py', 'for name, data in files.items() if name not in excluded}',
     'for name, data in files.items()}'),
    ('excluded blocks not filtered', 'kit.py', "if f'block:{name}' not in excluded}", '}'),
    ('a changed kit source is trusted', 'kit.py', "elif lock.get('source') != earlier.get('source'):", 'elif False:'),
    ('a kit adopted later is trusted', 'kit.py', '        if not earlier:', '        if False:'),
    ('records recognised by folder alone', 'kit.py', 'return bool(present) and all(map(record, present))',
     'return True'),
    ('lock lists not type-checked', 'kit.py', "for k in ('excluded', 'integrations', 'created', 'adopted'))):",
     "for k in ('excluded',))):"),
    ('a new instruction file is a difference', 'kit.py', "return created and now_outside == ''", 'return False'),
    ('a new instruction file need not be created by the kit', 'kit.py',
     "return created and now_outside == ''", "return now_outside == ''"),
    ('a removed block with the lock unchanged', 'kit.py',
     "        elif expected is not None:\n            return False\n", ''),
    ('a deleted instruction file is accepted', 'kit.py',
     "        if now is None:  # a file the kit created, removed with its block\n            return expected is None",
     "        if now is None:  # a file the kit created, removed with its block\n            return True or expected is None"),
    ('a removed integration file of any content', 'kit.py',
     "                digest(before) == earlier['files'][name]):", '                True):'),
    ('renames hide deletions', 'kit.py', "'--name-only', '-z', '--no-renames',", "'--name-only', '-z',"),
    ('a record in one version is enough', 'kit.py', 'return bool(present) and all(map(record, present))',
     'return bool(present) and any(map(record, present))'),
    ('the handoff title anywhere', 'kit.py', "return (re.match(r'# .+ handoff[ \\t]*\\n', source) is not None",
     "return (re.search(r'# .+ handoff[ \\t]*\\n', source) is not None"),
    ('a handoff named after any task', 'kit.py',
     "and named is not None and named.group(1) == leaf[:-len('.md')])", 'and named is not None)'),
    ('a task record named after any task', 'kit.py',
     "and task.get('id') == leaf[:-len('.json')]", ''),
    ('any JSON in the tasks folder is a record', 'kit.py', "return task.get('kit') == 'task/1' and task",
     'return task'),
    ('instruction-file names allowed for records', 'kit.py',
     '        if PurePosixPath(leaf).stem.casefold() in reserved:\n            return False', '        if False:\n            return False'),
    ('the project\'s own instruction files not reserved', 'kit.py', '                stems.add(PurePosixPath(name).stem.casefold())',
     '                pass'),
    ('check allows instruction-file names for tasks', 'kit.py', '        if path.stem.casefold() in reserved:\n            found.append(Finding(FORMAT',
     '        if False:\n            found.append(Finding(FORMAT'),
    ('check allows instruction-file names for handoffs', 'kit.py', "        if path.stem.casefold() in reserved:\n            found.append(Finding('HANDOFF'",
     "        if False:\n            found.append(Finding('HANDOFF'"),
    ('the Task line anywhere in a handoff', 'kit.py', "head = data.decode('utf-8', 'replace').partition('\\n## ')[0]",
     "head = data.decode('utf-8', 'replace')"),
    ('a whitespace-only instruction file gets a line break', 'kit.py',
     'if before_outside and before_outside.strip() and', 'if before_outside and'),
    ('a removed kit is trusted', 'kit.py', '        elif not lock:', '        elif False:'),
    ('lock maps not type-checked', 'kit.py', 'isinstance(lock.get(k, {}), dict) and all(map(text, lock.get(k, {}).values()))',
     'isinstance(lock.get(k, {}), dict)'),
    ('a removed integration file is a difference', 'kit.py',
     "        if now is None and name in earlier.get('files', {}) and before is not None and (",
     '        if False and ('),
    ('integrated keeps the line break after the begin marker', 'kit.py',
     "(block[1:] if block.startswith('\\n') else block)", 'block'),
    ('checking a lock leaves compiled files', 'kit.py',
     '    sys.dont_write_bytecode = True  # leave no compiled files inside a project\'s kit folder\n    import kit_update',
     '    import kit_update'),
]


def survives(snapshot: Path, name: str, old: str, new: str) -> bool:
    with tempfile.TemporaryDirectory(prefix='kit-mutant-') as directory:
        copy = Path(directory) / 'kit'
        shutil.copytree(snapshot, copy)
        target = copy / 'tools' / name
        target.write_text(target.read_text(encoding='utf-8').replace(old, new), encoding='utf-8')
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests'], cwd=copy,
                                capture_output=True, text=True, timeout=600)
        return result.returncode == 0


def main(labels: list[str]) -> int:
    chosen = [m for m in MUTANTS if not labels or m[0] in labels]
    unknown = sorted(set(labels) - {m[0] for m in MUTANTS})
    if unknown:
        raise SystemExit('No such mutant: ' + ', '.join(unknown))
    with tempfile.TemporaryDirectory(prefix='kit-snapshot-') as directory:
        # One copy taken before any run, so edits made meanwhile do not mix into later mutants.
        snapshot = Path(directory) / 'kit'
        shutil.copytree(KIT, snapshot, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        stale = [label for label, name, old, _ in chosen
                 if (snapshot / 'tools' / name).read_text(encoding='utf-8').count(old) != 1]
        if stale:
            raise SystemExit('The original text is not in its file exactly once; update these mutants: '
                             + ', '.join(stale))
        survivors = []
        for label, name, old, new in chosen:
            alive = survives(snapshot, name, old, new)
            print(f'{"SURVIVES" if alive else "caught  "}  {label}', flush=True)
            if alive:
                survivors.append(label)
    print(f'{len(chosen) - len(survivors)} of {len(chosen)} mutants caught.')
    return 1 if survivors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
