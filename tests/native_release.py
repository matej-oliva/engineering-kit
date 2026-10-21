"""Exercise published releases, or a release candidate, offline on a native host.

Without --candidate, the older of the two newest release tags is installed with its own tool and
updated to the newest. With --candidate X.Y.Z, a scratch clone of the source makes the release
commit and tag exactly as tests/release_commit.py does, and each of the two newest published
releases is installed with its own tool and updated to the candidate. The source is never modified.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile


def remove_tree(path):
    def writable(function, name, error):
        os.chmod(name, stat.S_IWRITE | stat.S_IREAD)
        function(name)
    shutil.rmtree(path, onerror=writable)


def newest_two(source: Path) -> tuple[str, str]:
    """The two supported releases: the newest release tag and the one before it."""
    tags = subprocess.run(['git', 'tag', '--list', 'v*'], cwd=source, capture_output=True, text=True,
                          check=True).stdout.split()
    versions = sorted((tuple(map(int, tag[1:].split('.'))) for tag in tags
                       if re.fullmatch(r'v\d+\.\d+\.\d+', tag)))
    if len(versions) < 2:
        raise RuntimeError('the source needs at least two release tags')
    return tuple('.'.join(map(str, version)) for version in versions[-2:])


def exercise(source: Path, report: Path, candidate: str | None = None):
    result = {'platform': platform.platform(), 'machine': platform.machine(),
              'python': platform.python_version(), 'image': os.environ.get('ImageOS'),
              'image_version': os.environ.get('ImageVersion'), 'steps': []}
    scratch = Path(tempfile.mkdtemp(prefix='kit native releases '))
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1', GIT_AUTHOR_NAME='Kit rehearsal',
               GIT_AUTHOR_EMAIL='kit@example.invalid', GIT_COMMITTER_NAME='Kit rehearsal',
               GIT_COMMITTER_EMAIL='kit@example.invalid')

    def run(*args, cwd=scratch):
        done = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
        print(done.stdout, end='')
        if done.returncode:
            raise RuntimeError(f'{args[0]} exited {done.returncode}: {done.stderr}')
        return done.stdout.strip()

    try:
        result['git'] = run('git', '--version')
        if candidate:
            origin = scratch / 'candidate source'
            run('git', 'clone', '--quiet', '--no-hardlinks', str(source), str(origin))
            # The candidate's own script, so it acts on the scratch clone and rehearses the real procedure.
            run(sys.executable, str(origin / 'tests' / 'release_commit.py'), candidate, cwd=origin)
            published = newest_two(source)
            pairs, releases = [(old, candidate) for old in published], [*published, candidate]
        else:
            origin = source
            older, newer = newest_two(source)
            pairs, releases = [(older, newer)], [older, newer]
        clones = {}
        for version in releases:
            clone = scratch / ('release ' + version)
            run('git', 'clone', '--quiet', '--no-hardlinks', '--branch', 'v' + version,
                str(origin), str(clone))
            run(sys.executable, str(clone / 'tools/kit.py'), 'release', version, '--check', cwd=clone)
            clones[version] = clone
            result[version] = run('git', 'rev-parse', 'HEAD', cwd=clone)
        for older, newer in pairs:
            lifecycle(origin, clones, result, older, newer, scratch / f'consumer from {older}', run)
        result['result'] = 'pass'
    except Exception as error:
        result.update(result='fail', error=str(error))
        raise
    finally:
        try:
            remove_tree(scratch)
            result['scratch_removed'] = True
        finally:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(result, indent=2))


def lifecycle(origin, clones, result, older, newer, project, run):
    """Install OLDER with its own tool, update to NEWER, roll back, update again and remove."""
    project.mkdir()
    run('git', 'init', '--quiet', cwd=project)
    instructions = b'# Local instructions\r\n\r\nKeep workshop records local.\r\n'
    (project / 'AGENTS.md').write_bytes(instructions)
    installer = clones[older] / 'tools/kit.py'

    def command(tool, *args):
        return run(sys.executable, str(tool), *args, cwd=project)

    def change(tool, *args):
        command(tool, *args)
        command(tool, *args, '--apply')

    change(installer, 'adopt', str(origin), older, '--with', 'claude-code')
    config_path = project / '.engineering-kit/project.json'

    def filled(value):
        if isinstance(value, dict):
            return {key: filled(item) for key, item in value.items()}
        if isinstance(value, list):
            return [filled(item) for item in value]
        return 'Local workshop fixture' if isinstance(value, str) and value.startswith('kit-placeholder:') else value

    config = filled(json.loads(config_path.read_text(encoding='utf-8')))
    config['rules'] = [{'id': 'LOCAL-DATA', 'text': 'Keep workshop records local.',
                        'enforced': 'guidance', 'by': 'Owner review'}]
    config_bytes = (json.dumps(config, indent=2) + '\n').encode()
    config_path.write_bytes(config_bytes)
    task = project / '.engineering-kit/tasks/T-1.json'
    task.parent.mkdir(parents=True, exist_ok=True)
    task_bytes = b'{"kit":"task/1","id":"T-1","title":"Future work","state":"proposed"}\n'
    task.write_bytes(task_bytes)
    installed = project / '.engineering-kit/kit/tools/kit.py'
    command(installed, 'check')
    result['steps'].append(f'adopt {older} and check')
    for operation, version in (('update', newer), ('rollback', older), ('update', newer)):
        args = (operation, version) if operation == 'update' else (operation,)
        change(installed, *args)
        lock = json.loads((project / '.engineering-kit/lock.json').read_text(encoding='utf-8'))
        assert lock['version'] == version
        assert lock['commit'] == result[version]
        assert config_path.read_bytes() == config_bytes
        assert (project / 'AGENTS.md').read_bytes().startswith(instructions)
        command(installed, 'check')
        result['steps'].append(f'{operation} {version} with the installed tool and check')
    skills = [root / 'kit-review' / 'SKILL.md' for root in (project / '.agents/skills', project / '.claude/skills')]
    if (clones[newer] / 'integrations' / 'agent-skills').is_dir():
        config['integrations']['agent-skills'] = {'grant': ['writes-skills']}
        config_bytes = (json.dumps(config, indent=2) + '\n').encode()
        config_path.write_bytes(config_bytes)
        change(installed, 'update')  # no version: the newest release, here NEWER, with the new grant
        lock = json.loads((project / '.engineering-kit/lock.json').read_text(encoding='utf-8'))
        assert lock['version'] == newer
        assert all(path.is_file() for path in skills)
        command(installed, 'check')
        result['steps'].append(f'grant agent-skills, update without a version and check: {newer} with skills')
    change(installed, 'remove')
    assert not any(path.exists() for path in skills)
    assert (project / 'AGENTS.md').read_bytes() == instructions
    assert config_path.read_bytes() == config_bytes
    assert task.read_bytes() == task_bytes
    assert not (project / 'CLAUDE.md').exists()
    assert not (project / '.engineering-kit/lock.json').exists()
    assert not any(path.is_file() for path in (project / '.engineering-kit/kit').rglob('*'))
    result['steps'].append(f'remove from {older}; original CRLF instructions, local policy and records preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--candidate', metavar='X.Y.Z', default=os.environ.get('KIT_CANDIDATE') or None,
                        help='rehearse this release before tagging it (default: KIT_CANDIDATE)')
    args = parser.parse_args()
    exercise(args.source.resolve(), args.report.resolve(), args.candidate)
