"""Exercise published tags offline on a native host; never modify the source repository."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
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


def exercise(source: Path, report: Path):
    result = {'platform': platform.platform(), 'machine': platform.machine(),
              'python': platform.python_version(), 'image': os.environ.get('ImageOS'),
              'image_version': os.environ.get('ImageVersion'), 'steps': []}
    scratch = Path(tempfile.mkdtemp(prefix='kit native releases '))
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1')

    def run(*args, cwd=scratch):
        done = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
        print(done.stdout, end='')
        if done.returncode:
            raise RuntimeError(f'{args[0]} exited {done.returncode}: {done.stderr}')
        return done.stdout.strip()

    try:
        result['git'] = run('git', '--version')
        clones = {}
        for version in ('0.1.1', '1.0.0'):
            clone = scratch / ('release ' + version)
            run('git', 'clone', '--quiet', '--no-hardlinks', '--branch', 'v' + version,
                str(source), str(clone))
            run(sys.executable, str(clone / 'tools/kit.py'), 'release', version, '--check', cwd=clone)
            clones[version] = clone
            result[version] = run('git', 'rev-parse', 'HEAD', cwd=clone)
        project = scratch / 'consumer with spaces'
        project.mkdir()
        run('git', 'init', '--quiet', cwd=project)
        instructions = b'# Local instructions\r\n\r\nKeep workshop records local.\r\n'
        (project / 'AGENTS.md').write_bytes(instructions)
        installer = clones['0.1.1'] / 'tools/kit.py'

        def command(tool, *args):
            return run(sys.executable, str(tool), *args, cwd=project)

        def change(tool, *args):
            command(tool, *args)
            command(tool, *args, '--apply')

        change(installer, 'adopt', str(source), '0.1.1', '--with', 'claude-code')
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
        result['steps'].append('adopt 0.1.1 and check')
        for operation, version in (('update', '1.0.0'), ('rollback', '0.1.1'), ('update', '1.0.0')):
            args = (operation, version) if operation == 'update' else (operation,)
            change(installed, *args)
            lock = json.loads((project / '.engineering-kit/lock.json').read_text(encoding='utf-8'))
            assert lock['version'] == version
            assert lock['commit'] == result[version]
            assert config_path.read_bytes() == config_bytes
            assert (project / 'AGENTS.md').read_bytes().startswith(instructions)
            command(installed, 'check')
            result['steps'].append(operation + ' ' + version + ' and check')
        change(installed, 'remove')
        assert (project / 'AGENTS.md').read_bytes() == instructions
        assert config_path.read_bytes() == config_bytes
        assert task.read_bytes() == task_bytes
        assert not (project / 'CLAUDE.md').exists()
        assert not (project / '.engineering-kit/lock.json').exists()
        assert not any(path.is_file() for path in (project / '.engineering-kit/kit').rglob('*'))
        result['steps'].append('remove; original CRLF instructions, local policy and records preserved')
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    exercise(args.source.resolve(), args.report.resolve())
