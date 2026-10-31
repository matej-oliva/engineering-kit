"""The work-cycle integration on disposable repositories: delivery, the task runner, guards and
local excludes. Stand-in review tools and agents record what they were asked to do, so no hosting
service, agent client, network or credential is involved."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'tools'))
import kit  # noqa: E402
from native_release import QUIET_GIT, remove_tree  # noqa: E402
SOURCE = KIT / 'integrations' / 'work-cycle' / 'cycle.py'
spec = importlib.util.spec_from_file_location('cycle', SOURCE)
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)

ZONE = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 10, 0, tzinfo=ZONE)  # inside the default window
FAKE_TOOL = '''
import json, os, sys
with open(os.environ['FAKE_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps({'argv': [os.path.basename(sys.argv[0])] + sys.argv[1:],
                          'host': os.environ.get('GH_HOST') or os.environ.get('GITLAB_HOST')}) + '\\n')
if os.environ.get('FAKE_FAIL') and os.environ['FAKE_FAIL'] in sys.argv:
    sys.exit(1)
print('https://example.invalid/request/1')
'''
FAKE_AGENT = '''
import json, os, subprocess, sys, time
mode = os.environ.get('FAKE_AGENT', 'handoff')
with open(os.environ['FAKE_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:], 'task': os.environ.get('KIT_CYCLE_TASK')}) + '\\n')
if mode == 'sleep':
    time.sleep(60)
if mode == 'handoff':
    task, handoff = sys.argv[1], sys.argv[2]
    with open(handoff, 'w', encoding='utf-8') as out:
        out.write('agent handoff for ' + task)
    with open('work.txt', 'w', encoding='utf-8') as out:
        out.write('done')
    subprocess.run(['git', 'add', 'work.txt'], check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'Work'], check=True)
    path = os.environ['KIT_CYCLE_TASK_FILE']  # done for now: the owner reviews it
    with open(path, encoding='utf-8') as source:
        record = json.load(source)
    record['next_actor'] = 'owner'
    with open(path, 'w', encoding='utf-8') as out:
        json.dump(record, out)
'''


def git(*args, cwd, check=True):
    return subprocess.run(['git', *args], cwd=cwd, check=check, capture_output=True, text=True).stdout.strip()


def task(identifier, state='accepted', next_actor='agent'):
    return {'kit': 'task/1', 'id': identifier, 'title': f'Task {identifier}', 'state': state,
            'next_actor': next_actor, 'profile': 'change'}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='kit-cycle-'))
        self.addCleanup(remove_tree, self.temp)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'KIT_CYCLE_', 'GH_', 'GITLAB_'))}
        self.log = self.temp / 'log.jsonl'
        self.bin = self.temp / 'bin'
        self.bin.mkdir()
        env.update(QUIET_GIT, HOME=str(self.temp), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                   GIT_AUTHOR_NAME='Kit Test', GIT_AUTHOR_EMAIL='kit@example.invalid',
                   GIT_COMMITTER_NAME='Kit Test', GIT_COMMITTER_EMAIL='kit@example.invalid',
                   FAKE_LOG=str(self.log), PATH=str(self.bin) + os.pathsep + os.environ.get('PATH', ''))
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ('gh', 'glab', 'az'):
            self.tool(name, FAKE_TOOL)
        self.agent = self.temp / 'agent.py'
        self.agent.write_text(FAKE_AGENT, encoding='utf-8')
        self.home = self.temp / 'runner-home'

    def tool(self, name, body):
        script = self.bin / f'{name}.py'
        script.write_text(body, encoding='utf-8')
        if os.name == 'nt':
            (self.bin / f'{name}.cmd').write_text(f'@"{sys.executable}" "{script}" %*\n', encoding='utf-8')
        else:
            target = self.bin / name
            target.write_text(f'#!{sys.executable}\n' + body, encoding='utf-8', newline='\n')  # no \r after it
            target.chmod(0o755)

    def repository(self, name='billing', cycle_settings=None, tasks=(), url=None):
        """A clone of a bare remote, with the kit's project.json, the cycle script and TASKS."""
        remote = self.temp / f'{name}.git'
        git('init', '-q', '--bare', '-b', 'main', str(remote), cwd=self.temp)
        seed = self.temp / f'{name}-seed'
        git('init', '-q', '-b', 'main', str(seed), cwd=self.temp)
        (seed / 'README.md').write_text('readme\n', encoding='utf-8')
        git('add', '.', cwd=seed)
        git('commit', '-q', '-m', 'Start', cwd=seed)
        git('push', '-q', str(remote), 'main', cwd=seed)
        root = self.temp / name
        git('clone', '-q', str(remote), str(root), cwd=self.temp)
        project = {'kit': 'project/1', 'name': name,
                   'checks': {'tests': {'description': 'Tests pass', 'command': 'git --version'},
                              'notes': {'description': 'Read by hand'}},
                   'profiles': {'change': {'required_checks': ['tests', 'notes'], 'review': 'required'}},
                   'paths': {'tasks': '.engineering-kit/tasks', 'handoffs': '.engineering-kit/handoffs'},
                   'cycle': cycle_settings or {}}
        (root / '.engineering-kit' / 'tasks').mkdir(parents=True)
        (root / '.engineering-kit' / 'project.json').write_text(json.dumps(project), encoding='utf-8')
        for record in tasks:
            self.write_task(root, record)
        (root / '.kit-cycle').mkdir()
        (root / '.kit-cycle' / 'cycle.py').write_bytes(SOURCE.read_bytes())
        exclude = Path(git('rev-parse', '--git-common-dir', cwd=root))
        exclude = (exclude if exclude.is_absolute() else root / exclude) / 'info' / 'exclude'
        exclude.write_text('/.engineering-kit/\n/.kit-cycle/\n', encoding='utf-8')
        if url:  # the address names a host; pushes still go to the local remote
            git('remote', 'set-url', 'origin', url, cwd=root)
            git('remote', 'set-url', '--push', 'origin', str(remote), cwd=root)
        return root, remote

    def write_task(self, root, record):
        path = root / '.engineering-kit' / 'tasks' / f'{record["id"]}.json'
        path.write_text(json.dumps(record), encoding='utf-8')

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()]


class Delivery(Fixture):
    def branch_with(self, root, *paths, branch='kit/T1'):
        git('switch', '-q', '-c', branch, cwd=root)
        for path in paths:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text('change\n', encoding='utf-8')
        git('add', *paths, cwd=root)
        git('commit', '-q', '-m', 'Change', cwd=root)

    def deliver(self, root, task_id='T1', **options):
        return cycle.deliver(root, root, task_id, options.get('title'), None, out=lambda *_: None)

    def test_opens_a_labelled_request_and_never_merges_or_pushes_main(self):
        root, remote = self.repository(tasks=[task('T1')], url='https://github.com/acme/billing.git')
        main_before = git('rev-parse', 'main', cwd=remote)
        self.branch_with(root, 'docs/guide.md')
        record = self.deliver(root)
        self.assertEqual(record['outcome'], 'opened')
        self.assertEqual(record['class'], 'routine')
        self.assertEqual([c['result'] for c in record['checks']], ['pass', 'unknown'])
        self.assertEqual(git('rev-parse', 'kit/T1', cwd=remote), git('rev-parse', 'HEAD', cwd=root))
        self.assertEqual(git('rev-parse', 'main', cwd=remote), main_before)
        create, label = self.calls()
        self.assertEqual(create['argv'][:7], ['gh.py' if os.name == 'nt' else 'gh', 'pr', 'create', '--base', 'main',
                                              '--head', 'kit/T1'])
        self.assertEqual(create['argv'][8], '[routine] Task T1')
        self.assertIsNone(create['host'])
        self.assertEqual(label['argv'][1:], ['pr', 'edit', 'kit/T1', '--add-label', 'routine'])
        self.assertFalse([c for c in self.calls() if 'merge' in c['argv'] or '--auto' in c['argv']])
        saved = list((root / '.git' / 'kit-cycle' / 'deliveries').glob('*.json'))
        self.assertEqual(json.loads(saved[0].read_text(encoding='utf-8'))['outcome'], 'opened')

    def test_the_most_demanding_path_sets_the_class(self):
        rules = {'owner-only': ['deploy/*'], 'sensitive': ['migrations/*']}
        self.assertEqual(cycle.classify(['src/a.py'], rules)[0], 'routine')
        self.assertEqual(cycle.classify(['src/a.py', 'migrations/1.sql'], rules)[0], 'sensitive')
        self.assertEqual(cycle.classify(['migrations/1.sql', 'deploy/prod.yml'], rules)[0], 'owner-only')
        root, _ = self.repository(cycle_settings={'paths': rules}, tasks=[task('T1')],
                                  url='git@github.com:acme/billing.git')
        self.branch_with(root, 'migrations/2.sql')
        record = self.deliver(root)
        self.assertEqual(record['class'], 'sensitive')
        self.assertEqual(self.calls()[0]['argv'][8], '[sensitive] Task T1')

    def test_default_and_protected_branches_are_refused(self):
        root, remote = self.repository(cycle_settings={'protected': ['release']}, tasks=[task('T1')],
                                       url='https://github.com/acme/billing.git')
        for branch in ('main', 'release'):
            with self.subTest(branch):
                if branch != 'main':
                    git('switch', '-q', '-c', branch, cwd=root)
                (root / 'x.txt').write_text(branch, encoding='utf-8')
                git('add', 'x.txt', cwd=root)
                git('commit', '-q', '-m', 'x', cwd=root)
                with self.assertRaisesRegex(cycle.CycleError, 'protected'):
                    self.deliver(root)
        self.assertEqual(git('branch', '--format=%(refname:short)', cwd=remote), 'main')
        self.assertEqual(self.calls(), [])

    def test_uncommitted_changes_are_refused_before_the_checks(self):
        root, remote = self.repository(tasks=[task('T1')], url='https://github.com/acme/billing.git')
        self.branch_with(root, 'src/a.py')
        (root / 'src' / 'a.py').write_text('not committed\n', encoding='utf-8')
        with self.assertRaisesRegex(cycle.CycleError, 'uncommitted'):
            self.deliver(root)
        self.assertEqual(git('branch', '--format=%(refname:short)', cwd=remote), 'main')

    def test_a_failed_check_stops_before_the_push(self):
        root, remote = self.repository(tasks=[task('T1')], url='https://github.com/acme/billing.git')
        project = json.loads((root / '.engineering-kit' / 'project.json').read_text(encoding='utf-8'))
        project['checks']['tests']['command'] = 'git no-such-command'
        (root / '.engineering-kit' / 'project.json').write_text(json.dumps(project), encoding='utf-8')
        self.branch_with(root, 'src/a.py')
        record = self.deliver(root)
        self.assertEqual(record['outcome'], 'checks_failed')
        self.assertEqual(git('branch', '--format=%(refname:short)', cwd=remote), 'main')
        self.assertEqual(self.calls(), [])

    def test_a_missing_tool_records_a_manual_outcome_with_the_compare_address(self):
        root, remote = self.repository(tasks=[task('T1')], url='https://gitlab.example.invalid/team/billing.git')
        self.branch_with(root, 'src/a.py')
        with mock.patch.object(cycle.shutil, 'which', return_value=None):
            record = self.deliver(root)
        self.assertEqual(record['outcome'], 'manual')
        self.assertEqual(record['compare'], 'https://gitlab.example.invalid/team/billing/-/merge_requests/new?'
                                            'merge_request%5Bsource_branch%5D=kit%2FT1'
                                            '&merge_request%5Btarget_branch%5D=main')
        self.assertEqual(git('rev-parse', 'kit/T1', cwd=remote), git('rev-parse', 'HEAD', cwd=root))

    def test_each_host_gets_its_own_tool(self):
        cases = [
            ('https://git.corp.example.invalid/team/billing.git', {'github_hosts': ['git.corp.example.invalid']},
             ['pr', 'create'], 'git.corp.example.invalid'),
            ('ssh://git@gitlab.corp.example.invalid:2222/team/billing.git', {},
             ['mr', 'create', '--source-branch', 'kit/T1', '--target-branch', 'main'], 'gitlab.corp.example.invalid'),
            ('https://acme@dev.azure.com/acme/Payments/_git/billing', {},
             ['repos', 'pr', 'create', '--source-branch', 'kit/T1', '--target-branch', 'main'], None),
        ]
        for number, (url, settings, expected, host) in enumerate(cases):
            with self.subTest(url):
                self.log.unlink(missing_ok=True)
                root, _ = self.repository(f'repo{number}', settings, [task('T1')], url=url)
                self.branch_with(root, 'src/a.py')
                record = self.deliver(root)
                self.assertEqual(record['outcome'], 'opened')
                first = self.calls()[0]
                self.assertEqual(first['argv'][1:1 + len(expected)], expected)
                self.assertEqual(first['host'], host)
                if 'repos' in expected:  # Azure DevOps sets labels as it creates the request
                    self.assertEqual(first['argv'][-2:], ['--labels', 'routine'])
                    self.assertEqual(record['request']['label'], 'routine')
                    self.assertEqual(len(self.calls()), 1)

    def test_a_label_that_cannot_be_set_still_leaves_the_request_open(self):
        root, _ = self.repository(tasks=[task('T1')], url='https://github.com/acme/billing.git')
        self.branch_with(root, 'src/a.py')
        with mock.patch.dict(os.environ, FAKE_FAIL='--add-label'):
            record = self.deliver(root)
        self.assertEqual(record['outcome'], 'opened')
        self.assertTrue(record['request']['label'].startswith('not set'))
        root, _ = self.repository('azure', tasks=[task('T1')], url='https://dev.azure.com/acme/Payments/_git/billing')
        self.branch_with(root, 'src/a.py')
        self.log.unlink()
        with mock.patch.dict(os.environ, FAKE_FAIL='--labels'):
            record = self.deliver(root)
        self.assertEqual(record['outcome'], 'opened')
        self.assertTrue(record['request']['label'].startswith('not set'))
        labelled, plain = self.calls()
        self.assertEqual(plain['argv'], labelled['argv'][:-2])

    def test_an_unknown_host_is_refused_before_checks_or_push(self):
        root, remote = self.repository(tasks=[task('T1')], url='https://code.example.invalid/team/billing.git')
        self.branch_with(root, 'src/a.py')
        with self.assertRaisesRegex(cycle.CycleError, 'set "host"'):
            self.deliver(root)
        self.assertEqual(git('branch', '--format=%(refname:short)', cwd=remote), 'main')

    def test_compare_addresses(self):
        cases = [
            ('https://github.com/acme/billing.git', 'github',
             'https://github.com/acme/billing/compare/main...kit%2FT1?expand=1'),
            ('git@ssh.dev.azure.com:v3/acme/Payments/billing', 'azure',
             'https://dev.azure.com/acme/Payments/_git/billing/pullrequestcreate?sourceRef=kit%2FT1&targetRef=main'),
            ('https://acme.visualstudio.com/Payments/_git/billing', 'azure',
             'https://acme.visualstudio.com/Payments/_git/billing/pullrequestcreate?sourceRef=kit%2FT1'
             '&targetRef=main'),
        ]
        for url, kind, expected in cases:
            with self.subTest(url):
                host, path = cycle.parse_remote(url)
                self.assertEqual(cycle.host_kind(host, {}), kind)
                self.assertEqual(cycle.compare_url(kind, host, path, 'main', 'kit/T1'), expected)


class Runner(Fixture):
    def runner(self, *roots, command=None):
        for root in roots:
            cycle.register(self.home, root, None)
        config = cycle.load_runner(self.home)
        config['agent']['command'] = command or [sys.executable, str(self.agent), '{task}', '{handoff}',
                                                 '{prompt_file}']
        cycle.write_json(self.home / 'runner.json', config)
        return cycle.load_runner(self.home)

    def test_the_queue_is_first_in_first_out_across_repositories(self):
        first, _ = self.repository('first', tasks=[task('A2')])
        second, _ = self.repository('second', tasks=[task('B1'), task('B2', state='proposed'),
                                                    task('B3', next_actor='owner')])
        config = self.runner(first, second)
        order = lambda moment: [(i['repository'], i['task']) for i in cycle.refresh_queue(self.home, config, moment)]
        self.assertEqual(order(MONDAY), [('first', 'A2'), ('second', 'B1')])
        self.write_task(first, task('A1'))  # ready later, so behind B1 although it sorts first
        self.write_task(second, task('B2'))
        self.assertEqual(order(MONDAY), [('first', 'A2'), ('second', 'B1'), ('first', 'A1'), ('second', 'B2')])
        self.write_task(first, task('A2', next_actor='owner'))  # leaves the queue, and rejoins at its tail
        self.assertEqual(order(MONDAY)[0], ('second', 'B1'))
        self.write_task(first, task('A2'))
        self.assertEqual(order(MONDAY)[-1], ('first', 'A2'))

    def test_a_claimed_task_is_skipped_until_its_claim_ends(self):
        root, _ = self.repository(tasks=[task('T1'), task('T2')])
        config = self.runner(root)
        cycle.claim(self.home, 'billing', 'T1', 'person', MONDAY + timedelta(hours=1))
        self.assertEqual(cycle.next_task(self.home, config, MONDAY)['task'], 'T2')
        self.assertEqual(cycle.next_task(self.home, config, MONDAY + timedelta(hours=2))['task'], 'T1')
        cycle.release(self.home, 'billing', 'T1')
        self.assertEqual(cycle.next_task(self.home, config, MONDAY)['task'], 'T1')

    def test_a_run_works_in_a_fresh_worktree_and_the_runner_stops_with_the_window(self):
        root, remote = self.repository(tasks=[task('T1')])
        self.runner(root)
        moments = iter([MONDAY, MONDAY + timedelta(minutes=5), MONDAY.replace(hour=17, minute=1)])
        printed = []
        status = cycle.serve(self.home, clock=lambda: next(moments), sleep=lambda _: self.fail('slept'),
                             out=printed.append)
        self.assertEqual(status, 0)
        self.assertIn('the runner stops. 1 task runs', printed[-1])
        run = json.loads(next((self.home / 'runs').glob('*.json')).read_text(encoding='utf-8'))
        self.assertEqual(run['outcome'], 'finished')
        worktree = Path(run['worktree'])
        self.assertEqual(Path(self.calls()[0]['cwd']).resolve(), worktree.resolve())
        self.assertEqual(self.calls()[0]['task'], 'T1')
        self.assertTrue(run['branch'].startswith('kit/T1-'))
        self.assertEqual(run['base'], 'origin/main')
        self.assertEqual(git('rev-parse', 'HEAD~1', cwd=worktree), git('rev-parse', 'main', cwd=remote))
        self.assertEqual(git('rev-parse', 'HEAD', cwd=root), git('rev-parse', 'main', cwd=remote))
        self.assertIn('agent handoff', (root / '.engineering-kit' / 'handoffs' / 'T1.md').read_text(encoding='utf-8'))
        prompt = Path(self.calls()[0]['argv'][2]).read_text(encoding='utf-8')
        self.assertIn('deliver --task T1', prompt)
        self.assertIn('never push main', prompt)
        self.assertIsNone(cycle.claimed(self.home, 'billing', 'T1', MONDAY))

    def test_a_run_without_a_handoff_gets_one_that_passes_the_contract(self):
        root, _ = self.repository(tasks=[task('T1', state='in_progress')])
        config = self.runner(root)
        with mock.patch.dict(os.environ, FAKE_AGENT='silent'):
            record = cycle.run_one(self.home, config, {'repository': 'billing', 'task': 'T1'}, MONDAY,
                                   MONDAY + timedelta(hours=1))
        self.assertEqual(record['outcome'], 'unknown')
        self.assertEqual(record['handoff_written_by'], 'runner')
        handoff = (root / '.engineering-kit' / 'handoffs' / 'T1.md').read_text(encoding='utf-8')
        self.assertEqual(kit.check_handoff(handoff, {'T1': 'in_progress'}, 'T1.md'), [])
        self.assertIn('outcome is unknown', handoff)

    def test_a_task_that_stays_ready_runs_once_per_session(self):
        root, _ = self.repository(tasks=[task('T1', state='in_progress')])
        self.runner(root)
        moments = iter([MONDAY, MONDAY + timedelta(minutes=1), MONDAY + timedelta(minutes=2),
                        MONDAY.replace(hour=17, minute=1)])
        waits = []
        with mock.patch.dict(os.environ, FAKE_AGENT='silent'):  # exits at once and leaves the task ready
            status = cycle.serve(self.home, clock=lambda: next(moments), sleep=waits.append, out=lambda _: None)
        self.assertEqual(status, 0)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(len(list((self.home / 'worktrees').iterdir())), 1)
        self.assertEqual(waits, [600.0])

    def test_the_time_limit_stops_the_agent(self):
        root, _ = self.repository(tasks=[task('T1')])
        config = self.runner(root)
        with mock.patch.dict(os.environ, FAKE_AGENT='sleep'):
            started = datetime.now()
            record = cycle.run_one(self.home, config, {'repository': 'billing', 'task': 'T1'}, MONDAY,
                                   MONDAY + timedelta(seconds=2))
        self.assertLess(datetime.now() - started, timedelta(seconds=40))
        self.assertEqual(record['outcome'], 'timed_out')
        self.assertTrue(record['timed_out'])
        self.assertTrue((root / '.engineering-kit' / 'handoffs' / 'T1.md').exists())

    def test_the_runner_starts_nothing_outside_the_window_or_near_its_end(self):
        root, _ = self.repository(tasks=[task('T1')])
        self.runner(root)
        window = {'days': ['mon', 'tue', 'wed', 'thu', 'fri'], 'start': '09:00', 'end': '17:00'}
        self.assertEqual(cycle.window_end(window, MONDAY), MONDAY.replace(hour=17))
        self.assertIsNone(cycle.window_end(window, MONDAY.replace(hour=8, minute=59)))
        self.assertIsNone(cycle.window_end(window, MONDAY.replace(hour=17)))
        self.assertIsNone(cycle.window_end(window, MONDAY + timedelta(days=5)))  # Saturday
        for moment in (MONDAY + timedelta(days=5), MONDAY.replace(hour=16, minute=45)):
            with self.subTest(moment):
                printed = []
                self.assertEqual(cycle.serve(self.home, clock=lambda: moment, sleep=lambda _: self.fail('slept'),
                                             out=printed.append), 0)
                self.assertIn('the runner stops', printed[0])
        self.assertEqual(self.calls(), [])

    def test_an_idle_runner_waits_no_longer_than_the_window(self):
        root, _ = self.repository()
        self.runner(root)
        moments = iter([MONDAY.replace(hour=16, minute=30), MONDAY.replace(hour=17)])
        waits = []
        cycle.serve(self.home, clock=lambda: next(moments), sleep=waits.append, out=lambda _: None)
        self.assertEqual(waits, [600.0])

    def test_registration_refuses_a_second_repository_under_the_same_name(self):
        first, _ = self.repository('first')
        second, _ = self.repository('second')
        cycle.register(self.home, first, 'billing')
        cycle.register(self.home, first, 'billing')
        with self.assertRaisesRegex(cycle.CycleError, 'another repository'):
            cycle.register(self.home, second, 'billing')
        self.assertEqual(len(cycle.load_runner(self.home)['repositories']), 1)


class Guards(Fixture):
    def test_the_pre_push_guard_refuses_protected_branches_from_every_worktree(self):
        root, remote = self.repository(cycle_settings={'protected': ['release']})
        lines = cycle.install_guards(root)
        self.assertIn('pre-push', lines[0])
        (root / 'a.txt').write_text('a', encoding='utf-8')
        git('add', 'a.txt', cwd=root)
        git('commit', '-q', '-m', 'a', cwd=root)
        for target in ('main', 'release'):
            with self.subTest(target):
                pushed = subprocess.run(['git', 'push', 'origin', f'HEAD:{target}'], cwd=root, capture_output=True,
                                        text=True)
                self.assertNotEqual(pushed.returncode, 0)
                self.assertIn('protected branches change only through a reviewed request', pushed.stderr)
        worktree = self.temp / 'side'
        git('worktree', 'add', '-q', '-b', 'kit/T1', str(worktree), cwd=root)
        self.assertNotEqual(subprocess.run(['git', 'push', 'origin', 'HEAD:main'], cwd=worktree,
                                           capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(['git', 'push', 'origin', 'kit/T1'], cwd=worktree,
                                        capture_output=True).returncode, 0)
        self.assertEqual(git('branch', '--format=%(refname:short)', cwd=remote).split(), ['kit/T1', 'main'])
        self.assertEqual(cycle.remove_guards(root)[0][:7], 'Removed')
        self.assertFalse((root / '.git' / 'hooks' / 'pre-push').exists())

    def test_another_hook_or_hooks_path_is_left_alone(self):
        root, _ = self.repository()
        hook = root / '.git' / 'hooks' / 'pre-push'
        hook.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        with self.assertRaisesRegex(cycle.CycleError, 'already exists'):
            cycle.install_guards(root)
        self.assertEqual(hook.read_text(encoding='utf-8'), '#!/bin/sh\nexit 0\n')
        self.assertEqual(cycle.remove_guards(root), ['No work-cycle pre-push guard is installed.'])
        git('config', 'core.hooksPath', '.husky', cwd=root)
        with self.assertRaisesRegex(cycle.CycleError, 'core.hooksPath'):
            cycle.install_guards(root)

    def test_the_edit_guard(self):
        names = {'main', 'release'}
        refused = {
            "sed -i 's/a/b/' src/a.py": 'sed -i',
            'perl -pi -e s/a/b/ x': 'perl -i',
            'git commit --no-verify -m x': 'bypasses',
            'git -c core.hooksPath=/dev/null push origin kit/T1': 'bypasses',
            'npm test && git push origin HEAD:main': 'protected branch',
            'git push origin +release': 'protected branch',
            'git push --force origin kit/T1': 'force',
        }
        for command, reason in refused.items():
            with self.subTest(command):
                self.assertIn(reason, ' '.join(cycle.guard_edit(command, names)))
        for command in ('sed s/a/b/ x', 'git push origin kit/T1', 'git push -u origin kit/T1', 'grep -i main x'):
            with self.subTest(command):
                self.assertEqual(cycle.guard_edit(command, names), [])
        root, _ = self.repository()
        payload = json.dumps({'tool_input': {'command': 'git push origin main'}, 'cwd': str(root)})
        with mock.patch.object(cycle.sys, 'stderr'):
            self.assertEqual(cycle.edit_hook(payload), 2)
            self.assertEqual(cycle.edit_hook(json.dumps({'tool_input': {'command': 'ls'}, 'cwd': str(root)})), 0)
            self.assertEqual(cycle.edit_hook('not json'), 0)


class Exclude(Fixture):
    def test_kit_files_stay_out_of_a_shared_repository(self):
        root, _ = self.repository(tasks=[task('T1')])
        (root / 'AGENTS.md').write_text('team rules\n', encoding='utf-8')
        git('add', 'AGENTS.md', cwd=root)
        git('commit', '-q', '-m', 'Team rules', cwd=root)
        lock = {'files': {'.engineering-kit/kit/CONTRACT.md': 'x', 'kit': 'x', '.claude/skills/kit-first-run/SKILL.md': 'x',
                          '.kit-cycle/cycle.py': 'x'}, 'blocks': {'block:AGENTS.md': 'x'}}
        (root / '.engineering-kit' / 'lock.json').write_text(json.dumps(lock), encoding='utf-8')
        info = root / '.git' / 'info' / 'exclude'
        info.write_text('*.log\n', encoding='utf-8')
        for name in ('kit', '.claude/skills/kit-first-run/SKILL.md'):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text('x', encoding='utf-8')
        cycle.exclude(root)
        report = cycle.exclude(root)  # a second run replaces its block
        self.assertIn('AGENTS.md', report[-1])
        text = info.read_text(encoding='utf-8')
        self.assertEqual(text.count(cycle.BEGIN), 1)
        self.assertTrue(text.startswith('*.log\n'))
        self.assertEqual(git('status', '--porcelain', '--untracked-files=all', cwd=root), '')


if __name__ == '__main__':
    unittest.main()
