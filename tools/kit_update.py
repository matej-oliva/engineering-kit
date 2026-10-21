"""Versioned distribution for the engineering kit, used by kit.py.

A release is a Git tag `vX.Y.Z` in the kit's repository whose tree holds
`RELEASE.json`: the version, the contract version, and the SHA-256 of every
payload file with a digest over all of them. Any Git host or a plain path
can serve it. A consuming project records what it installed in
`.engineering-kit/lock.json`.

Every change is previewed first and applied only with `--apply`. An update
merges three ways (the installed release, the project's current files and
the new release) and stops on any conflict without writing. Writes are
journaled so an interrupted apply can be undone with `recover`. Nothing from
a release is ever executed, paths outside the agreed area are refused, and
an integration is installed only with every permission it declares granted
in `project.json`.
"""
from __future__ import annotations

from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile

import kit

STATE = '.engineering-kit'
MANAGED_ROOT = f'{STATE}/kit'
LOCK = f'{STATE}/lock.json'
PROJECT = f'{STATE}/project.json'
JOURNAL = f'{STATE}/journal'
VERSION = re.compile(r'v?(\d+)\.(\d+)\.(\d+)')
SOURCE_ONLY = ('tests/', 'examples/', 'conformance/', '.github/')  # stay in the kit's repository
# All that the updaters of 0.1.0 to 1.0.0 leave out. A release tree may hold nothing else outside
# the payload: those updaters would count it as a kit file the manifest lacks and refuse the release.
EARLIER_SOURCE_ONLY = ('tests/', 'examples/', 'conformance/')
SOURCE_ONLY_FILES = ('RELEASE.json', 'SUPPORT.json')
BEGIN, END = '<!-- engineering-kit:begin -->', '<!-- engineering-kit:end -->'
RIGHTS = re.compile(r'owner-authored|licensed:[A-Za-z0-9.+-]+|cleared:\S.*')
NO_HOOKS = ('-c', 'core.hooksPath=/dev/null')


class KitError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args, cwd=None, data=None) -> bytes:
    result = subprocess.run(['git', *NO_HOOKS, *args], cwd=cwd, input=data, capture_output=True)
    if result.returncode:
        name = next((arg for number, arg in enumerate(args)  # the subcommand, not a -c option or its value
                     if not arg.startswith('-') and (number == 0 or args[number - 1] != '-c')), 'command')
        raise KitError(f'git {name} failed: {result.stderr.decode(errors="replace").strip()[-400:]}')
    return result.stdout


def tag_for(version: str) -> str:
    match = VERSION.fullmatch(version)
    if not match:
        raise KitError(f'version {version!r} is not MAJOR.MINOR.PATCH')
    return 'v' + '.'.join(match.groups())


def digest_of(files: dict[str, str]) -> str:
    return sha256(''.join(f'{files[path]}  {path}\n' for path in sorted(files)).encode())


def payload(path: str) -> bool:
    return not path.startswith(SOURCE_ONLY) and path not in SOURCE_ONLY_FILES and '__pycache__' not in path


# ------------------------------------------------------------- releases

def build_release(root: Path, version: str) -> dict:
    """Manifest for the kit files committed at HEAD in ROOT, the kit's source folder.

    It reads exactly the tree a tag on HEAD would hold, as fetch() verifies it. Working-copy
    bytes can differ from it: an editor may save CRLF that .gitattributes stores as LF."""
    entries = iter(git('status', '--porcelain=v1', '-z', '--untracked-files=all', cwd=root).decode().split('\0'))
    for entry in entries:
        if not entry:
            continue
        status, names = entry[:2], [entry[3:]]
        if 'R' in status or 'C' in status:  # a rename or copy is followed by its source path
            names.append(next(entries, ''))
        for name in names:
            if payload(name):
                raise KitError(f'{name} differs from the last commit; commit or discard it before making '
                               'a release')
    blobs = {}
    for record in git('ls-tree', '-r', '-z', '--full-tree', 'HEAD', cwd=root).decode().split('\0'):
        if not record:
            continue
        meta, name = record.split('\t', 1)
        mode, kind, blob = meta.split()
        if mode in ('120000', '160000') or kind != 'blob':  # fetch() refuses one anywhere in the tree
            raise KitError(f'{name} is a link or submodule; a release cannot contain one')
        if payload(name):
            blobs[name] = blob
        elif not name.startswith(EARLIER_SOURCE_ONLY) and name not in SOURCE_ONLY_FILES:
            raise KitError(f'{name} would look like a missing kit file to the updater of an earlier release; '
                           'make the release commit without it (MAINTAINING.md)')
    contents = {name: git('cat-file', 'blob', blob, cwd=root) for name, blob in blobs.items()}
    files = {name: sha256(data) for name, data in contents.items()}
    integrations = {}
    for name, data in contents.items():
        parts = PurePosixPath(name).parts
        if len(parts) == 3 and parts[0] == 'integrations' and parts[2] == 'integration.json':
            integrations[parts[1]] = json.loads(data.decode('utf-8'))['permissions']
    return {'kit': 'release/1', 'version': tag_for(version)[1:], 'contract': kit.CONTRACT_VERSION,
            'digest': digest_of(files), 'files': files, 'integrations': integrations,
            'notes': 'CHANGELOG.md'}


@dataclass
class Release:
    version: str
    commit: str
    manifest: dict
    files: dict[str, bytes]

    def text(self, path: str) -> str:
        return self.files[path].decode('utf-8')


def fetch(source: str, version: str, work: Path) -> Release:
    """Fetch tag vVERSION from SOURCE and verify it against its own manifest."""
    tag = tag_for(version)
    if not kit.text(source) or source.lstrip().startswith('-'):
        raise KitError(f'refusing the source {source!r}: it must be a repository address or path')
    repository = work / 'source.git'
    if not repository.exists():
        git('init', '--bare', '-q', str(repository))
    git('-c', 'protocol.ext.allow=never', 'fetch', '--quiet', '--no-tags', '--', source,
        f'+refs/tags/{tag}:refs/tags/{tag}', cwd=repository)
    commit = git('rev-parse', f'refs/tags/{tag}^{{commit}}', cwd=repository).decode().strip()
    tree = {}
    for record in git('ls-tree', '-r', '-z', '--full-tree', commit, cwd=repository).decode().split('\0'):
        if not record:
            continue
        meta, path = record.split('\t', 1)
        mode, kind, blob = meta.split()
        if mode in ('120000', '160000') or kind != 'blob':
            raise KitError(f'release {tag} contains {path}, which is a link or submodule; refusing')
        tree[path] = blob
    if 'RELEASE.json' not in tree:
        raise KitError(f'release {tag} has no RELEASE.json')

    def blob(path):
        return git('cat-file', 'blob', tree[path], cwd=repository)

    manifest = json.loads(blob('RELEASE.json'))
    if manifest.get('kit') != 'release/1' or manifest.get('version') != tag[1:]:
        raise KitError(f'release {tag} has a manifest for {manifest.get("version")!r}')
    listed = manifest.get('files', {})
    present = {path for path in tree if payload(path)}
    if set(listed) != present:
        raise KitError(f'release {tag} manifest does not match its files: '
                       f'{sorted(set(listed) ^ present)[:5]}')
    files = {}
    for path, expected in listed.items():
        if not kit.relative_path(path):
            raise KitError(f'release {tag} names an unsafe path {path!r}')
        files[path] = blob(path)
        if sha256(files[path]) != expected:
            raise KitError(f'release {tag}: {path} does not match its manifest digest')
    if digest_of(listed) != manifest.get('digest'):
        raise KitError(f'release {tag}: the manifest digest is wrong')
    return Release(tag[1:], commit, manifest, files)


# ------------------------------------------------------------- planning

def area(path: str) -> str:
    """Classify PATH as core, state, outside or unsafe, comparing names without case for
    file systems that ignore it."""
    parts = PurePosixPath(path).parts if kit.relative_path(path) else ()
    folded = [part.casefold() for part in parts]
    if not parts or '.git' in folded or any(part in ('.', '') for part in parts):
        return 'unsafe'
    if folded[0] != STATE.casefold():
        return 'outside'
    if path.startswith(MANAGED_ROOT + '/'):
        return 'core'
    return 'state' if path in (LOCK, PROJECT) else 'unsafe'


def safe_target(root: Path, path: str, *, core: bool, state: bool = False) -> None:
    """Refuse paths outside the project, in Git's or the project's kit state, or through a link.

    Core files live under MANAGED_ROOT; integration files and entry blocks live
    outside `.engineering-kit/`. The lock and project.json are written only by
    `change` itself, never on a release's say-so.
    """
    kind = area(path)
    if kind == 'unsafe':
        raise KitError(f'refusing unsafe path {path!r}')
    if kind != ('core' if core else 'state' if state else 'outside'):
        raise KitError(f'refusing {path!r}: outside the area the kit may write')
    current = root
    for part in PurePosixPath(path).parts:
        current = current / part
        if current.is_symlink():
            raise KitError(f'refusing {path!r}: {current.relative_to(root)} is a symbolic link')


def desired(release: Release, integrations: dict[str, list[str]] | None, names: list[str]):
    """Files and blocks RELEASE installs for NAMES.

    INTEGRATIONS maps names to granted permissions for a release about to be
    installed. None describes a release already installed: what it installed
    is known whatever this tool's contract version or the grants say now.
    A file or block an integration declares no permission for is refused.
    """
    files = {f'{MANAGED_ROOT}/{path}': content for path, content in release.files.items()}
    blocks, problems = {}, []
    block = release.text('templates/entry-block.md').strip() + '\n'
    for name in names:
        manifest_path = f'integrations/{name}/integration.json'
        if manifest_path not in release.files:
            problems.append(f'integration {name} is not in release {release.version}')
            continue
        manifest = json.loads(release.text(manifest_path))
        declared = set(manifest.get('permissions', []))
        if integrations is not None:
            if kit.CONTRACT_VERSION not in manifest.get('contract', []):
                problems.append(f'integration {name} does not support contract {kit.CONTRACT_VERSION}')
                continue
            missing = sorted(declared - set(integrations.get(name, [])))
            if missing:
                problems.append(f'integration {name} needs {", ".join(missing)} granted in project.json; '
                                'discovering it grants nothing')
                continue
        for entry in manifest.get('files', []):
            target, source = entry.get('target', ''), f'integrations/{name}/{entry.get("source")}'
            if entry.get('permission') not in declared:
                raise KitError(f'integration {name} installs {target!r} without a permission it declares')
            if area(target) != 'outside':
                raise KitError(f'integration {name} targets {target!r}, outside the area it may write')
            if source not in release.files or target in files:
                raise KitError(f'integration {name}: {target} has no source in the release or collides')
            files[target] = release.files[source]
        for entry in manifest.get('blocks', []):
            if 'writes-instructions' not in declared:
                raise KitError(f'integration {name} adds a block without declaring the writes-instructions permission')
            if area(entry.get('target', '')) != 'outside':
                raise KitError(f'integration {name} targets {entry.get("target")!r}, outside the area it may write')
            blocks[entry['target']] = block
    return files, blocks, problems


def split_block(text: str):
    """Return (before, block, after) for a marked block, None without one; refuse broken markers."""
    begins, ends = text.count(BEGIN), text.count(END)
    if begins == ends == 0:
        return None
    if begins != 1 or ends != 1 or text.index(BEGIN) > text.index(END):
        raise KitError('the engineering-kit block markers are damaged')
    before, rest = text.split(BEGIN, 1)
    block, after = rest.split(END, 1)
    return before, without_line_break(block), after


def without_line_break(text: str) -> str:
    """TEXT without the one line break the kit writes after a marker, in either style."""
    for ending in ('\r\n', '\n'):
        if text.startswith(ending):
            return text[len(ending):]
    return text


def merge3(ours: bytes, base: bytes, theirs: bytes) -> tuple[bytes, bool]:
    with tempfile.TemporaryDirectory(prefix='kit-merge-') as directory:
        paths = []
        for name, data in (('local', ours), ('base', base), ('kit', theirs)):
            path = Path(directory) / name
            path.write_bytes(data)
            paths.append(str(path))
        result = subprocess.run(['git', 'merge-file', '-p', '-L', 'local', '-L', 'installed', '-L', 'new kit',
                                 *paths], capture_output=True)
        if result.returncode < 0 or result.returncode >= 128:
            raise KitError('git merge-file failed')
        return result.stdout, result.returncode == 0


@dataclass
class Action:
    path: str
    kind: str  # add, update, merge, delete, adopt, keep-local, conflict
    content: bytes | None = None
    reason: str = ''
    exclude: bool = False  # the project keeps its own file here; the kit stops managing the path
    block: bool = False  # the action concerns the entry block in PATH, not the whole file
    raw: bool = False  # CONTENT is the exact bytes to write; do not adjust its line endings

    @property
    def key(self) -> str:
        return f'block:{self.path}' if self.block else self.path


def three_way(path: str, base: bytes | None, ours: bytes | None, theirs: bytes | None,
              resolution: str | None) -> Action | None:
    """Decide one file. None means nothing to do."""
    def resolved(reason):
        if resolution == 'kit':
            return Action(path, 'delete' if theirs is None else 'update', theirs, f'{reason}; taking the kit')
        if resolution == 'local':
            return Action(path, 'keep-local', None, f'{reason}; keeping the local version',
                          exclude=base is None or ours is None)
        return Action(path, 'conflict', None, reason)

    if base is None:  # new in this release
        if ours is None:
            return Action(path, 'add', theirs)
        if ours == theirs:
            return Action(path, 'adopt', None, 'the project already has this exact file; it stays if the kit '
                                               'is removed')
        return resolved('an unmanaged file is in the way')
    if ours == theirs:
        return None
    if theirs is None:  # the release dropped it
        if ours is None:
            return None
        return Action(path, 'delete') if ours == base else resolved('changed locally but dropped by the kit')
    if ours is None:
        return resolved('deleted locally but still provided by the kit')
    if ours == base:
        return Action(path, 'update', theirs)
    if base == theirs:
        return None  # a local change the kit did not touch
    merged, clean = merge3(ours, base, theirs)
    return Action(path, 'merge', merged) if clean else resolved('local and kit changes overlap')


def read_raw(root: Path, path: str) -> bytes | None:
    """The exact bytes on disk, for the recovery journal."""
    target = root / path
    return target.read_bytes() if target.is_file() else None


def read(root: Path, path: str) -> bytes | None:
    """Content for comparison. Windows line endings read as Unix ones, so a checkout that
    converts them, as Git for Windows usually does, is not a local change."""
    data = read_raw(root, path)
    return data.replace(b'\r\n', b'\n') if data is not None else None


def consistently_crlf(data: bytes | None) -> bool:
    return bool(data) and b'\r\n' in data and data.count(b'\n') == data.count(b'\r\n')


def styled(content: bytes | None, current: bytes | None) -> bytes | None:
    """CONTENT with Windows line endings when the file on disk uses them throughout."""
    if content is not None and consistently_crlf(current):
        return content.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    return content


def obstruction(root: Path, path: str) -> str | None:
    """Why PATH cannot be written as a file, such as a folder standing where it goes."""
    current = root
    parts = PurePosixPath(path).parts
    for number, part in enumerate(parts, 1):
        current = current / part
        if not current.exists():
            return None
        if number < len(parts) and not current.is_dir():
            return f'{current.relative_to(root).as_posix()} is not a folder; move it first'
    return None if current.is_file() else f'{path} is not a file; move it first'


def plan(root: Path, base: Release | None, target: Release | None, project: dict | None,
         lock: dict | None, resolutions: dict[str, str]):
    """Actions that move ROOT from BASE (None: not adopted) to TARGET (None: removed)."""
    problems, lock = [], lock or {}
    if base is not None:
        base_files, base_blocks, missing = desired(base, None, lock['integrations'])
        if missing:
            raise KitError('the installed release no longer matches the lock: ' + '; '.join(missing))
    else:
        base_files, base_blocks = {}, {}
    if target is not None:
        settings = (project or {}).get('integrations', {})
        grants = {name: value.get('grant', []) for name, value in settings.items()}
        target_files, target_blocks, problems = desired(target, grants, sorted(settings))
    else:
        target_files, target_blocks = {}, {}
    def maps(key):  # a lock key names a file, or with "block:" the entry block in a file
        if key.startswith('block:'):
            return base_blocks, target_blocks, key.removeprefix('block:')
        return base_files, target_files, key

    for key in lock.get('excluded', []):  # kept as the project's own: the kit leaves them alone
        base_map, target_map, name = maps(key)
        base_map.pop(name, None)
        target_map.pop(name, None)
    for key in lock.get('adopted', []):  # identical before the kit came: kept when the kit stops providing it
        base_map, target_map, name = maps(key)
        if name not in target_map:
            base_map.pop(name, None)
    actions = []
    core = {path for path in set(base_files) | set(target_files) if path.startswith(MANAGED_ROOT + '/')}
    for path in sorted(set(base_files) | set(target_files)):
        safe_target(root, path, core=path in core)
        blocked = obstruction(root, path)
        action = Action(path, 'conflict', None, blocked) if blocked else three_way(
            path, base_files.get(path), read(root, path), target_files.get(path), resolutions.get(path))
        if action:
            actions.append(action)
    for path in sorted(set(base_blocks) | set(target_blocks)):
        safe_target(root, path, core=False)
        actions += block_actions(root, path, base_blocks.get(path), target_blocks.get(path), resolutions.get(path),
                                 created=path in lock.get('created', []))
    return actions, problems


def block_actions(root: Path, path: str, base: str | None, theirs: str | None, resolution: str | None,
                  created: bool) -> list[Action]:
    """Actions for the entry block in PATH; CREATED means the kit created the file for it."""
    blocked = obstruction(root, path)
    if blocked:
        return [Action(path, 'conflict', None, blocked, block=True)]
    # Work on the exact text so every byte outside the block, line endings included, stays
    # as the project wrote it; compare block contents with Unix line endings.
    current = read_raw(root, path)
    text = current.decode('utf-8') if current is not None else None
    parts = split_block(text) if text is not None else None

    def action(kind, body, reason):
        return Action(path, kind, body.encode() if body is not None else None, reason, block=True, raw=True)

    if parts is None:  # no file, or a file without the block
        if theirs is None:
            return []
        if base is not None:  # the block, or its whole file, was removed after the kit installed it
            decided = three_way(path, base.encode(), None, theirs.encode(), resolution)
            decided.block = True
            if decided.kind != 'update':
                return [decided]
        eol = '\r\n' if text and consistently_crlf(current) else '\n'
        prefix = text + ('' if text.endswith('\n') else eol) + eol if text and text.strip() else (text or '')
        block = theirs.replace('\n', eol)
        return [action('add' if text is None else 'update', f'{prefix}{BEGIN}{eol}{block}{END}{eol}',
                       'add the entry block')]
    before, ours, after = parts
    eol = '\r\n' if '\r\n' in ours or (not ours.strip() and consistently_crlf(current)) else '\n'
    decided = three_way(path, base.encode() if base else None, ours.replace('\r\n', '\n').encode(),
                        theirs.encode() if theirs else None, resolution)
    if decided is None:
        return []
    decided.block = True
    if decided.kind in ('conflict', 'keep-local', 'adopt'):
        return [decided]
    if decided.content is None:  # remove the block and the one blank line added before it
        for ending in ('\r\n', '\n'):
            if before.endswith(ending) and before[:-len(ending)].endswith('\n'):
                before = before[:-len(ending)]
                break
        new = before + without_line_break(after)
        if not new.strip() and created:
            return [action('delete', None, 'remove the entry block and the file the kit created')]
        return [action('update', new, 'remove the entry block')]
    block = decided.content.decode().replace('\n', eol)
    return [action(decided.kind, f'{before}{BEGIN}{eol}{block}{END}{after}', 'update the entry block')]


def plan_digest(actions: list[Action], version: str | None) -> str:
    lines = [f'{a.kind} {a.path} {sha256(a.content) if a.content is not None else "-"}' for a in actions]
    return sha256('\n'.join([str(version)] + lines).encode())[:16]


# ---------------------------------------------------------------- apply

def flush(path: Path) -> None:
    """Ask the system to put PATH, a file or folder, on disk; some systems cannot open folders."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.kit-tmp')
    with open(temporary, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    flush(path.parent)


def digest_or_none(data: bytes | None) -> str | None:
    return sha256(data) if data is not None else None


def apply(root: Path, writes: list[Action], *, fail_after: int | None = None) -> None:
    """Journal every original and the digests before and after, then write.
    `recover` undoes a partial apply. FAIL_AFTER is for tests."""
    journal = root / JOURNAL
    if journal.exists():
        raise KitError('an earlier apply was interrupted; run "kit.py recover" first')
    journal.mkdir(parents=True)
    steps, finals = [], []
    for number, action in enumerate(writes):
        before = read_raw(root, action.path)
        final = action.content if action.raw else styled(action.content, before)
        finals.append(final)
        backup = None
        if before is not None:
            backup = f'{number}.orig'
            write_atomic(journal / backup, before)
        steps.append({'path': action.path, 'backup': backup, 'before': digest_or_none(before),
                      'after': digest_or_none(final)})
    write_atomic(journal / 'journal.json', json.dumps({'kit': 'journal/1', 'steps': steps}).encode())
    for number, (action, final) in enumerate(zip(writes, finals)):  # nothing is written before the journal
        if fail_after is not None and number == fail_after:
            raise KitError('simulated interruption')
        target = root / action.path
        if final is None:
            target.unlink(missing_ok=True)
            flush(target.parent)
        else:
            write_atomic(target, final)
    shutil.rmtree(journal)
    flush(journal.parent)


def recover(root: Path, abandon: bool = False) -> int:
    """Undo the writes of an interrupted apply and return how many. ABANDON drops the journal and
    keeps the files as they are. Paths the kit never writes, and files changed since, are refused."""
    journal = root / JOURNAL
    record = journal / 'journal.json'
    if not journal.exists():
        return 0
    if abandon or not record.exists():  # without a complete journal, no write had started
        shutil.rmtree(journal)
        return 0
    try:
        data = json.loads(record.read_text(encoding='utf-8'))
        steps = data['steps'] if data.get('kit') == 'journal/1' else None
        if not isinstance(steps, list):
            raise ValueError
    except (ValueError, KeyError, AttributeError):
        raise KitError('the journal is unreadable; check the files the apply was changing, then run '
                       '"kit.py recover --abandon"') from None
    for step in steps:
        path, backup = step.get('path'), step.get('backup')
        if (not isinstance(path, str) or area(path) == 'unsafe'
                or (backup is not None and not (isinstance(backup, str) and re.fullmatch(r'\d+\.orig', backup)
                                                and (journal / backup).is_file()))):
            raise KitError(f'the journal names {path!r}, which the kit never writes; refusing to recover from it')
        safe_target(root, path, core=area(path) == 'core', state=area(path) == 'state')
    applied, changed = [], []
    for step in steps:
        target = root / step['path']
        now = 'not a file' if target.exists() and not target.is_file() else digest_or_none(
            read_raw(root, step['path']))
        if now == step.get('after'):
            applied.append(step)
        elif now != step.get('before'):
            changed.append(step['path'])
    if changed:
        raise KitError('these files changed since the interrupted apply: ' + ', '.join(changed) +
                       '. Save those changes elsewhere and run recover again, or keep the files as they are '
                       'with "kit.py recover --abandon"')
    for step in reversed(applied):
        target = root / step['path']
        if step['backup']:
            write_atomic(target, (journal / step['backup']).read_bytes())
        else:
            target.unlink(missing_ok=True)
    shutil.rmtree(journal)
    flush(journal.parent)
    return len(applied)


# ------------------------------------------------------------- commands

def load_lock(root: Path) -> dict | None:
    path = root / LOCK
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def new_lock(root: Path, source: str, release: Release, project: dict, actions: list[Action],
             previous: dict | None) -> bytes:
    names = sorted((project or {}).get('integrations', {}))
    files, blocks, _ = desired(release, None, names)
    previous = previous or {}
    excluded = sorted(set(previous.get('excluded', [])) | {a.key for a in actions if a.exclude})
    files = {path: data for path, data in files.items() if path not in excluded}
    blocks = {path: text for path, text in blocks.items() if f'block:{path}' not in excluded}
    adopted = sorted(key for key in set(previous.get('adopted', [])) | {a.key for a in actions if a.kind == 'adopt'}
                     if (key.removeprefix('block:') in blocks if key.startswith('block:') else key in files))
    created = sorted((set(previous.get('created', [])) | {a.path for a in actions if a.block and a.kind == 'add'})
                     - {a.path for a in actions if a.block and a.kind == 'delete'})
    history = list(previous.get('history', []))
    if not history or history[-1]['version'] != release.version:
        history.append({'version': release.version, 'commit': release.commit,
                        'digest': release.manifest['digest']})
    lock = {'kit': 'lock/1', 'source': source, 'version': release.version, 'commit': release.commit,
            'digest': release.manifest['digest'], 'contract': release.manifest['contract'],
            'integrations': names, 'files': {path: sha256(data) for path, data in sorted(files.items())},
            'blocks': {path: sha256(text.encode()) for path, text in sorted(blocks.items())},
            'excluded': excluded, 'adopted': adopted, 'created': created, 'history': history}
    return (json.dumps(lock, indent=2) + '\n').encode()


def describe(actions: list[Action], problems: list[str], root: Path, show_diff: bool) -> list[str]:
    lines = [f'  {a.kind:<10} {a.path}' + (f'  ({a.reason})' if a.reason else '') for a in actions]
    lines += [f'  refused    {problem}' for problem in problems]
    if show_diff:
        for action in actions:
            if action.kind in ('add', 'update', 'merge', 'delete'):
                old = (read(root, action.path) or b'').decode('utf-8', 'replace').splitlines(keepends=True)
                new = (action.content or b'').decode('utf-8', 'replace').splitlines(keepends=True)
                lines += [line.rstrip('\n') for line in difflib.unified_diff(
                    old, new, f'a/{action.path}', f'b/{action.path}')]
    return lines or ['  nothing to change']


def change(root: Path, source: str, version: str | None, *, adopting: bool = False, apply_now: bool = False,
           resolutions: dict[str, str] | None = None, expected_plan: str | None = None,
           accept_contract: int | None = None, show_diff: bool = False,
           fail_after: int | None = None, with_integrations: list[str] | None = None) -> tuple[int, list[str]]:
    """Adopt, update, roll back or remove. Returns an exit status and report lines.

    WITH_INTEGRATIONS, only when adopting into a project without project.json,
    enables those integrations in the new file and grants exactly what each
    declares; naming one is the grant, and the preview lists it."""
    root = root.resolve()
    resolutions = resolutions or {}
    if (root / JOURNAL).exists():
        raise KitError('an earlier apply was interrupted; run "kit.py recover" first')
    lock = load_lock(root)
    if adopting and lock:
        raise KitError(f'already adopted at {lock["version"]}; use update')
    if not adopting and not lock:
        raise KitError('this project has not adopted the kit; use adopt')
    with tempfile.TemporaryDirectory(prefix='kit-fetch-') as work:
        base = None
        if lock:
            base = fetch(lock['source'], lock['version'], Path(work))
            if base.commit != lock['commit'] or base.manifest['digest'] != lock['digest']:
                raise KitError(f'release {lock["version"]} at {lock["source"]} is not what was installed '
                               f'(commit {base.commit[:12]}, recorded {lock["commit"][:12]}); refusing')
        target = fetch(source, version, Path(work)) if version else None
        for entry in (lock or {}).get('history', []) if target else []:
            if entry['version'] == target.version and (entry['commit'], entry['digest']) != (
                    target.commit, target.manifest['digest']):
                raise KitError(f'release {target.version} at {source} is not what was installed before '
                               f'(commit {target.commit[:12]}, recorded {entry["commit"][:12]}); refusing')
        project_bytes = read(root, PROJECT)
        writes_project = adopting and project_bytes is None
        if with_integrations and not writes_project:
            raise KitError('--with only shapes a new project.json; enable integrations in the existing '
                           'project.json instead')
        granted = []
        if writes_project:
            project_bytes = target.files['templates/project.json']
            if with_integrations:
                project = json.loads(project_bytes)
                for name in with_integrations:
                    manifest = target.files.get(f'integrations/{name}/integration.json')
                    if manifest is None:
                        raise KitError(f'release {target.version} has no integration {name!r}')
                    permissions = json.loads(manifest)['permissions']
                    project['integrations'][name] = {'grant': permissions}
                    granted.append(f'  grant      {name}: {", ".join(permissions)}')
                project_bytes = (json.dumps(project, indent=2) + '\n').encode()
        project = json.loads(project_bytes) if project_bytes else {}
        actions, problems = plan(root, base, target, project, lock, resolutions)
        if target and lock and target.manifest['contract'] != lock['contract'] \
                and accept_contract != target.manifest['contract']:
            problems.append(f'the contract changes from {lock["contract"]} to {target.manifest["contract"]}; '
                            f'read the release notes, then rerun with --accept-contract '
                            f'{target.manifest["contract"]}')
        if writes_project:
            actions.insert(0, Action(PROJECT, 'add', project_bytes, 'project-owned from now on'))
        heading = (f'{lock["version"] if lock else "not adopted"} -> '
                   f'{target.version if target else "removed"} from {source}')
        digest = plan_digest(actions, target.version if target else None)
        lines = [heading, *granted, *describe(actions, problems, root, show_diff), f'plan {digest}']
        conflicts = [a for a in actions if a.kind == 'conflict']
        if conflicts:
            lines.append('Stopped: resolve each conflict by editing the local file, or rerun with '
                         '--resolve PATH=kit or --resolve PATH=local. Nothing was written.')
        if problems or conflicts:
            return 1, lines
        if not apply_now:
            lines.append('Preview only; rerun with --apply to write these changes.')
            return 0, lines
        if expected_plan and expected_plan != digest:
            raise KitError(f'the plan is {digest}, not the previewed {expected_plan}; preview again')
        writes = [a for a in actions if a.kind in ('add', 'update', 'merge', 'delete')]
        lock_bytes = new_lock(root, source, target, project, actions, lock) if target else None
        if not writes and lock_bytes == read(root, LOCK):
            return 0, lines + ['Already at this release; nothing written.']
        writes.append(Action(LOCK, 'update', lock_bytes) if target else Action(LOCK, 'delete'))
        apply(root, writes, fail_after=fail_after)
        lines.append(f'Applied {len(writes) - 1} changes and recorded the release in {LOCK}.'
                     if target else f'Removed the kit; {PROJECT}, tasks and handoffs stay.')
        if writes_project:
            lines.append(f'Next: replace every "{kit.TEMPLATE_MARKER}" value in {PROJECT} with this project\'s '
                         'facts, then run kit.py check.')
        return 0, lines


def local_source(source: str | None) -> str | None:
    """A source naming a folder here, made absolute: Git reads it from a temporary repository."""
    if source and not source.lstrip().startswith('-') and Path(source).is_dir():
        return str(Path(source).resolve())
    return source


def version_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in VERSION.fullmatch(version).groups())


def newest_release(source: str) -> str:
    """The highest vMAJOR.MINOR.PATCH tag at SOURCE, compared as numbers; other tags are ignored."""
    if not kit.text(source) or source.lstrip().startswith('-'):
        raise KitError(f'refusing the source {source!r}: it must be a repository address or path')
    listed = git('-c', 'protocol.ext.allow=never', 'ls-remote', '--tags', '--refs', '--', source).decode()
    versions = [ref.rsplit('/', 1)[1][1:] for ref in (line.split('\t')[-1] for line in listed.splitlines())
                if ref.startswith('refs/tags/v') and VERSION.fullmatch(ref.rsplit('/', 1)[1])]
    if not versions:
        raise KitError(f'{source} has no release tags vMAJOR.MINOR.PATCH')
    return max(versions, key=version_key)


def own_release() -> tuple[str, str]:
    """The repository and release this tool was cloned at, so adopting needs neither typed."""
    kit_root = Path(__file__).resolve().parents[1]
    try:
        top = Path(git('rev-parse', '--show-toplevel', cwd=kit_root).decode().strip()).resolve()
    except (KitError, OSError):
        top = None
    if top is None or not os.path.samefile(top, kit_root):  # same folder, whatever its spelling on Windows
        raise KitError('this tool is not running from a clone of the kit; give SOURCE and VERSION')
    tags = [tag for tag in git('tag', '--points-at', 'HEAD', cwd=kit_root).decode().split()
            if VERSION.fullmatch(tag) and tag.startswith('v')]
    if len(tags) != 1:
        raise KitError('the kit clone is not at exactly one release; clone with --branch vX.Y.Z, or give '
                       'SOURCE and VERSION')
    try:
        source = git('remote', 'get-url', 'origin', cwd=kit_root).decode().strip()
    except KitError:
        source = str(kit_root)
    return source, tags[0][1:]


def previous_version(root: Path) -> str:
    lock = load_lock(root)
    if not lock or len(lock['history']) < 2:
        raise KitError('there is no earlier installed release to roll back to')
    return lock['history'][-2]['version']


def status(root: Path) -> tuple[int, list[str]]:
    lock = load_lock(root)
    if (root / JOURNAL).exists():
        return 1, ['An apply was interrupted. Run "kit.py recover" to restore the earlier files.']
    if not lock:
        return 0, ['The kit is not adopted here.']
    lines = [f'Kit {lock["version"]} (contract {lock["contract"]}) from {lock["source"]}, '
             f'commit {lock["commit"][:12]}', f'Integrations: {", ".join(lock["integrations"]) or "none"}']
    for path, expected in lock['files'].items():
        data = read(root, path)
        state = 'missing' if data is None else 'ok' if sha256(data) == expected else 'modified locally'
        if state != 'ok':
            lines.append(f'  {state:<16} {path}')
    for path, expected in lock['blocks'].items():
        data = read(root, path)
        parts = split_block(data.decode('utf-8')) if data is not None else None
        state = 'missing' if not parts else 'ok' if sha256(parts[1].encode()) == expected else 'modified locally'
        if state != 'ok':
            lines.append(f'  {state:<16} entry block in {path}')
    if len(lines) == 2:
        lines.append('  every kit-managed file matches the installed release')
    lines += [f"  kept as the project's own: entry block in {key.removeprefix('block:')}"
              if key.startswith('block:') else f"  kept as the project's own: {key}"
              for key in lock.get('excluded', [])]
    return 0, lines


# --------------------------------------------------------- contributions

def check_contribution(record) -> list[kit.Finding]:
    found = []

    def refuse(message):
        found.append(kit.Finding('LESSON', 'contribution', message))

    if not isinstance(record, dict) or record.get('kit') != 'contribution/1':
        return [kit.Finding(kit.FORMAT, 'contribution', 'needs "kit": "contribution/1"')]
    for field in ('project', 'source_revision', 'kit_version', 'need', 'evidence', 'limits', 'owner'):
        if not kit.text(record.get(field)):
            refuse(f'names its {field.replace("_", " ")}')
    if not (kit.text(record.get('rights')) and RIGHTS.fullmatch(record['rights'])):
        refuse('rights must be owner-authored, licensed:SPDX-ID or cleared:REFERENCE; unknown rights stay out')
    if record.get('status') not in ('proposal', 'proven'):
        refuse('status is proposal until evidence shows the lesson works, then proven')
    if not isinstance(record.get('files'), list) or not record['files'] or not all(
            kit.relative_path(path) for path in record['files']):
        refuse('lists the kit files it changes')
    return found


def contribute(root: Path, paths: list[str], out: Path, details: dict) -> list[str]:
    """Write OUT/contribution.json and OUT/change.patch for locally changed kit files."""
    root = root.resolve()
    lock = load_lock(root)
    if not lock:
        raise KitError('this project has not adopted the kit')
    project = json.loads(read(root, PROJECT) or b'{}')
    with tempfile.TemporaryDirectory(prefix='kit-fetch-') as work:
        base = fetch(lock['source'], lock['version'], Path(work))
        patch, files = [], []
        for path in paths:
            relative = path.removeprefix(MANAGED_ROOT + '/')
            if relative not in base.files:
                raise KitError(f'{path} is not a kit file of release {base.version}')
            current = read(root, f'{MANAGED_ROOT}/{relative}')
            if current is None or current == base.files[relative]:
                raise KitError(f'{path} has no local change to contribute')
            patch += difflib.unified_diff(base.text(relative).splitlines(keepends=True),
                                          current.decode('utf-8').splitlines(keepends=True),
                                          f'a/{relative}', f'b/{relative}')
            files.append(relative)
    try:
        revision = git('rev-parse', 'HEAD', cwd=root).decode().strip()
    except (KitError, OSError):
        revision = ''
    record = {'kit': 'contribution/1', 'project': project.get('name', ''), 'source_revision': revision,
              'kit_version': lock['version'], 'files': files, 'status': 'proposal', **details}
    found = check_contribution(record)
    if found:
        raise KitError('; '.join(f.message for f in found))
    out.mkdir(parents=True, exist_ok=True)
    (out / 'change.patch').write_text(''.join(patch), encoding='utf-8', newline='')  # exact bytes for git apply
    (out / 'contribution.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return [f'Wrote {out / "contribution.json"} and {out / "change.patch"} for {", ".join(files)}.',
            'Apply the patch in the kit repository with "git apply", add its evidence, review and release it.']


# ------------------------------------------------------------------ CLI

def cli(args) -> int:
    """Run a distribution command parsed by kit.py; a refusal exits 1 with its reason."""
    try:
        if args.command == 'check-contribution':
            record = json.loads(args.file.read_text(encoding='utf-8'))
            return kit.report(check_contribution(record), args.json, 'The contribution can be reviewed.')
        root = args.root.resolve()
        if args.command == 'status':
            code, lines = status(root)
        elif args.command == 'recover':
            restored = recover(root, abandon=args.abandon)
            code, lines = 0, ['Dropped the journal; the files stay as they are.' if args.abandon
                              else f'Restored {restored} files from the interrupted apply.' if restored
                              else 'Nothing to recover.']
        elif args.command == 'release':
            manifest = build_release(root, args.version)
            path = root / 'RELEASE.json'
            current = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
            if args.check:
                code = 0 if current == manifest else 1
                lines = ['RELEASE.json matches the tracked files.' if code == 0
                         else 'RELEASE.json does not match the tracked files; run release without --check.']
            else:
                path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
                code, lines = 0, [f'Wrote RELEASE.json for {manifest["version"]}, digest {manifest["digest"][:16]}.',
                                  f'Commit it, then tag the commit v{manifest["version"]}.']
        elif args.command == 'contribute':
            details = {field: getattr(args, field) for field in ('need', 'evidence', 'limits', 'rights', 'owner')}
            code, lines = 0, contribute(root, args.files, args.out, details)
        else:
            resolutions = {}
            for item in args.resolve:
                path, _, choice = item.rpartition('=')
                if choice not in ('kit', 'local') or not path:
                    raise KitError(f'--resolve takes PATH=kit or PATH=local, not {item!r}')
                resolutions[path] = choice
            lock = load_lock(root)
            if args.command == 'adopt':
                source, version = local_source(args.source), args.version
                if source is None:
                    source, version = own_release()
                elif version is None:
                    version = newest_release(source)
            elif args.command == 'update':
                source, version = local_source(args.source) or (lock or {}).get('source', ''), args.version
                if version is None and lock:
                    version = newest_release(source)
                    if version_key(version) <= version_key(lock['version']):
                        newer = '' if version == lock['version'] else f'; the newest at the source is {version}'
                        print(f'Nothing to update: this project is already at the newest release, '
                              f'{lock["version"]}{newer}.')
                        return 0
            elif args.command == 'rollback':
                source, version = (lock or {}).get('source', ''), previous_version(root)
            else:
                source, version = (lock or {}).get('source', ''), None
            code, lines = change(root, source, version, adopting=args.command == 'adopt', apply_now=args.apply,
                                 resolutions=resolutions, expected_plan=args.plan,
                                 accept_contract=getattr(args, 'accept_contract', None), show_diff=args.diff,
                                 with_integrations=getattr(args, 'with_integrations', []))
    except (KitError, OSError, ValueError) as error:
        print(f'refused: {error}')
        return 1
    print('\n'.join(lines))
    return code
