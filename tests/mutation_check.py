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
    ('the interview allows automatic model invocation',
     'integrations/agent-skills/skills/kit-grill-me/SKILL.md',
     'disable-model-invocation: true', 'disable-model-invocation: false'),
    ('the interview allows implicit invocation in its companion policy',
     'integrations/agent-skills/skills/kit-grill-me/agents/openai.yaml',
     'allow_implicit_invocation: false', 'allow_implicit_invocation: true'),
    ('a release hashes the working copy, not what Git stores', 'kit_update.py',
     "contents = dict(zip(blobs, read_blobs(list(blobs.values()), root)))",
     "contents = {name: (root / name).read_bytes() for name in blobs}"),
    ('a batch read takes the wrong length for a file', 'kit_update.py',
     "contents.append(out[start:start + int(header[2])])", "contents.append(out[start:start + int(header[2]) - 1])"),
    ('a release ignores uncommitted kit files', 'kit_update.py',
     "            if payload(name):\n                raise KitError(f'{name} differs from the last commit",
     "            if False:\n                raise KitError(f'{name} differs from the last commit"),
    ('a release accepts a link it will fail to install', 'kit_update.py',
     "        if mode in ('120000', '160000') or kind != 'blob':  # fetch() refuses one anywhere in the tree\n            raise KitError(f'{name} is a link",
     "        if False:\n            raise KitError(f'{name} is a link"),
    ('the newest release is chosen by text, so 0.9.0 beats 0.10.0', 'kit_update.py',
     'return max(versions, key=version_key)', 'return max(versions)'),
    ('a tag with leading zeros counts as a release', 'kit_update.py',
     r"RELEASE_REF = re.compile(r'refs/tags/v((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))')",
     r"RELEASE_REF = re.compile(r'refs/tags/v(\d+\.\d+\.\d+)')"),
    ('an update without a version can move back', 'kit_update.py',
     "if version_key(version) < version_key(lock['version']):  # never move back",
     "if False:"),
    ('an update without a version skips a newly granted integration', 'kit_update.py',
     "if version_key(version) < version_key(lock['version']):  # never move back",
     "if version_key(version) <= version_key(lock['version']):"),
    ('a relative source path is read from the temporary repository', 'kit_update.py',
     '        return str(Path(source).resolve())', '        return source'),
    ('a release tree may hold files that earlier updaters count as kit files', 'kit_update.py',
     '        elif not name.startswith(EARLIER_SOURCE_ONLY) and name not in SOURCE_ONLY_FILES:',
     '        elif False:'),
    ('a failed release commit leaves its branch behind', 'tests/release_commit.py',
     "        if not made:\n            git('branch', '-q', '-D', branch, root=root)",
     "        if False:\n            git('branch', '-q', '-D', branch, root=root)"),
    ('a refused plan still offers a digest to apply', 'kit_update.py',
     "            return 1, lines  # no plan line: a refused plan cannot be applied\n        lines.append(f'plan {digest}')",
     "            return 1, lines + [f'plan {digest}']\n        lines.append(f'plan {digest}')"),
    ('the removal preview hides the lock', 'kit_update.py',
     "        shown = actions + ([Action(LOCK, 'delete')] if not target and lock else [])",
     "        shown = actions"),
    ('--source cannot reach a kit that moved', 'kit_update.py',
     "            installed_from = moved_to or lock['source']", "            installed_from = lock['source']"),
    ('--source must also hold the installed release', 'kit_update.py',
     '                if not moved_to:\n                    raise', '                raise'),
    ('a one-tag clone cannot be a source', 'kit_update.py',
     "'fetch', '--quiet', '--update-shallow', '--no-tags'", "'fetch', '--quiet', '--no-tags'"),
    ('removal leaves the folders it emptied', 'kit_update.py',
     '            while folder != root and folder.is_dir() and not any(folder.iterdir()):',
     '            while False:'),
    ('a failed release commit leaves a new file behind', 'tests/release_commit.py',
     "            git('clean', '-q', '-f', '-d', root=root)", '            pass'),
    ('the launcher imports a project module of the same name', 'integrations/launcher/kit',
     'sys.path[0] = str(tools)', 'sys.path.append(str(tools))'),
    ('a refusal names a recover command the person did not type', 'kit_update.py',
     "return f'\"{kit.invocation()} recover{options}\"'", "return f'\"kit.py recover{options}\"'"),
    ('a failed release commit leaves its deletions staged', 'tests/release_commit.py',
     "            git('reset', '-q', '--hard', root=root)", '            pass'),
    ('the release commit keeps repository-host files', 'tests/release_commit.py',
     "HOST_ONLY = ('.github',)", 'HOST_ONLY = ()'),
    ('repository workflows become installed payload', 'kit_update.py',
     "'conformance/', '.github/'", "'conformance/'"),
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
    ('the handoff title on any line', 'kit.py', "re.fullmatch(r'# .+ handoff', lines[0].strip()) is not None",
     "any(re.fullmatch(r'# .+ handoff', line.strip()) for line in lines)"),
    ('a handoff named after any task', 'kit.py',
     "and named is not None and named.group(1) == leaf[:-len('.md')])", 'and named is not None)'),
    ('a task record named after any task', 'kit.py',
     "and task.get('id') == leaf[:-len('.json')]", ''),
    ('any JSON in the tasks folder is a record', 'kit.py', "return task.get('kit') == 'task/1' and task",
     'return task'),
    ('instruction-file names allowed for records', 'kit.py',
     '        if first_component(leaf) in reserved:\n            return False', '        if False:\n            return False'),
    ('reserved names compared with case', 'kit.py', "    return PurePosixPath(name).name.split('.', 1)[0].casefold()",
     "    return PurePosixPath(name).name.split('.', 1)[0]"),
    ('reserved names compared by stem', 'kit.py', "    return PurePosixPath(name).name.split('.', 1)[0].casefold()",
     '    return PurePosixPath(name).stem.casefold()'),
    ('only Claude and README reserved', 'kit.py', "INSTRUCTION_STEMS = ('agents', 'claude', 'gemini', 'copilot-instructions', 'readme')",
     "INSTRUCTION_STEMS = ('claude', 'readme')"),
    ('instructions of any type', 'kit.py', "    clients = instructions.get('clients') if isinstance(instructions, dict) else None",
     "    clients = instructions.get('clients')"),
    ('the last Task line counts', 'kit.py', '        fields.setdefault(field, value)', '        fields[field] = value'),
    ('the project\'s own instruction files not reserved', 'kit.py', '                stems.add(first_component(name))',
     '                pass'),
    ('check allows instruction-file names for tasks', 'kit.py', '        if first_component(path.name) in reserved:\n            found.append(Finding(FORMAT',
     '        if False:\n            found.append(Finding(FORMAT'),
    ('check allows instruction-file names for handoffs', 'kit.py', "        if first_component(path.name) in reserved:\n            found.append(Finding('HANDOFF'",
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


def mutant_path(name: str) -> str:
    """A bare name is a file in tools/; a name with a slash is relative to the kit."""
    return name if '/' in name else f'tools/{name}'


def survives(snapshot: Path, name: str, old: str, new: str) -> bool:
    with tempfile.TemporaryDirectory(prefix='kit-mutant-') as directory:
        copy = Path(directory) / 'kit'
        shutil.copytree(snapshot, copy)
        target = copy / mutant_path(name)
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
                 if (snapshot / mutant_path(name)).read_text(encoding='utf-8').count(old) != 1]
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
