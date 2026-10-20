"""The reference tool at its real boundaries: the command line, files and Git."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
TOOL = KIT / 'tools' / 'kit.py'
EXAMPLE = KIT / 'examples' / 'walkthrough' / 'project'


def isolated_git_env(home: Path) -> dict:
    """Keep the caller's Git configuration and hooks out of the test."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(HOME=str(home), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    return env


def run(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd, env=env, capture_output=True, text=True)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='kit-tool-'))
        self.addCleanup(shutil.rmtree, self.temp)

    def copy_example(self) -> Path:
        root = self.temp / 'project'
        shutil.copytree(EXAMPLE, root)
        return root

    def test_check_passes_the_worked_project(self):
        result = run('check', '--root', str(EXAMPLE))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(run('check', '--json', '--root', str(EXAMPLE)).stdout)
        self.assertEqual((report['result'], report['findings'], report['contract']), ('pass', [], 1))

    def test_check_refuses_with_the_rule_and_exit_status_one(self):
        root = self.copy_example()
        task = root / '.engineering-kit' / 'tasks' / 'T-7.json'
        data = json.loads(task.read_text())
        data['checks'][0]['revision'] = 'ffff000'
        data['state'] = 'reviewed'
        task.write_text(json.dumps(data))
        result = run('check', '--json', '--root', str(root))
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report['result'], 'refuse')
        self.assertIn('HANDOFF', {f['rule'] for f in report['findings']})  # the handoff still says candidate
        self.assertIn('REVIEW', {f['rule'] for f in report['findings']})

    def test_unreadable_record_is_refused_not_crashed(self):
        root = self.copy_example()
        (root / '.engineering-kit' / 'tasks' / 'T-9.json').write_text('{not json')
        result = run('check', '--root', str(root))
        self.assertEqual(result.returncode, 1)
        self.assertIn('FORMAT', result.stdout)

    def test_check_task_and_handoff_commands(self):
        stage = KIT / 'examples' / 'walkthrough' / 'stages' / '07-closed.json'
        self.assertEqual(run('check-task', '--root', str(EXAMPLE), str(stage)).returncode, 0)
        handoff = EXAMPLE / '.engineering-kit' / 'handoffs' / 'T-7.md'
        self.assertEqual(run('check-handoff', '--root', str(EXAMPLE), str(handoff)).returncode, 0)

    def test_usage_error_exits_two(self):
        self.assertEqual(run('no-such-command').returncode, 2)

    def test_task_and_handoff_files_are_named_after_unique_tasks(self):
        root = self.copy_example()
        records = root / '.engineering-kit'
        shutil.copy(records / 'tasks' / 'T-7.json', records / 'tasks' / 'T-8.json')
        (records / 'handoffs' / 'T-7.md').rename(records / 'handoffs' / 'rounding.md')
        report = json.loads(run('check', '--json', '--root', str(root)).stdout)
        messages = {(f['rule'], f['message']) for f in report['findings']}
        self.assertIn(('FORMAT', 'task ID T-7 is used by another record'), messages)
        self.assertIn(('HANDOFF', 'name the file T-7.md after its task'), messages)

    def test_integrated_accepts_record_only_differences(self):
        env = isolated_git_env(self.temp)
        root = self.copy_example()

        def git(*args):
            return subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@example.invalid', *args],
                                  cwd=root, env=env, check=True, capture_output=True, text=True).stdout.strip()
        git('init', '-q')
        (root / 'total.py').write_text('ROUNDING = "half-up"\n')
        git('add', '-A')
        git('commit', '-q', '-m', 'candidate')
        candidate = git('rev-parse', 'HEAD')
        (root / '.engineering-kit' / 'tasks' / 'T-7.json').write_text('{"recorded": true}\n')
        config = root / '.engineering-kit' / 'project.json'
        config.write_text(config.read_text().replace('"published": "The package', '"published": "Our package'))
        git('commit', '-qam', 'record the candidate and correct a boundary meaning')
        records_only = git('rev-parse', 'HEAD')
        (root / 'total.py').write_text('ROUNDING = "half-even"\n')
        git('commit', '-qam', 'change code after review')
        changed = git('rev-parse', 'HEAD')
        self.assertEqual(run('integrated', candidate, records_only, '--root', str(root), env=env).returncode, 0)
        result = run('integrated', '--json', candidate, changed, '--root', str(root), env=env)
        self.assertEqual(result.returncode, 1)
        self.assertEqual([f['where'] for f in json.loads(result.stdout)['findings']], ['total.py'])


class SecretScan(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='kit-secrets-'))
        self.addCleanup(shutil.rmtree, self.temp)
        self.env = isolated_git_env(self.temp)
        self.repo = self.temp / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True, env=self.env)

    def stage(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        subprocess.run(['git', '-C', str(self.repo), 'add', name], check=True, env=self.env)

    def scan(self):
        return run('scan-secrets', '--json', '--root', str(self.repo), env=self.env)

    def test_clean_tree_passes(self):
        self.stage('README.md', 'Nothing secret here.\n')
        self.stage('.env.example', 'API_KEY=changeme\nTOKEN=<your token>\n')
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_token_and_filled_env_value_are_refused_without_printing_them(self):
        token = 'gh' + 'p_' + 'A1b2C3d4' * 5  # assembled so no scanner sees a literal token here
        self.stage('config.py', f'TOKEN = "{token}"\n')
        self.stage('.env', 'API_KEY=s3cr3t-value\n')
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual({f['rule'] for f in report['findings']}, {'SECRETS'})
        self.assertEqual(sorted(f['where'] for f in report['findings']), ['.env:1', 'config.py:1'])
        self.assertNotIn(token, result.stdout)
        self.assertNotIn('s3cr3t-value', result.stdout)

    def test_reviewed_allowlist_entry_accepts_one_value_only(self):
        token = 'gh' + 'p_' + 'Z9y8X7w6' * 5
        self.stage('tests/fixture.txt', f'{token}\n')
        digest = hashlib.sha256(token.encode()).hexdigest()
        self.stage('.engineering-kit/secret-allowlist.json', json.dumps(
            {'entries': [{'path': 'tests/fixture.txt', 'reason': 'Fake token for a parser test', 'sha256': [digest]}]}))
        self.assertEqual(self.scan().returncode, 0)
        self.stage('tests/fixture.txt', f'{token}\n{token[:-1]}Q\n')
        self.assertEqual(self.scan().returncode, 1)


if __name__ == '__main__':
    unittest.main()
