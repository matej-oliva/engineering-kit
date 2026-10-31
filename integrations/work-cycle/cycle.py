#!/usr/bin/env python3
"""Development cycle for repositories that use the engineering kit: a task runner, delivery
through review requests, guards and local excludes.

Standard library only, Python 3.11 or later, plus the git command line. Installed by the
work-cycle integration as `.kit-cycle/cycle.py`; run it from the project root, as
`python3 .kit-cycle/cycle.py COMMAND` or `py .kit-cycle\\cycle.py COMMAND` on Windows.

    register [--name NAME]            add this repository to the runner's queue
    run [--once]                      serve every registered repository until the window closes
    queue                             show the queue and the claims
    claim ID [--hours N] / release ID keep the runner off a task you work on yourself
    deliver [--task ID]               run the checks, push the branch, open a review request
    exclude                           list the kit's files in Git's local exclude file
    guards install|remove             the pre-push guard in this repository's Git hooks
    guard-push / guard-edit           the guards themselves, run by Git and agent clients

The runner keeps its state in one folder per user: --home, KIT_CYCLE_HOME, or `.kit-cycle`
in the home folder. It is a foreground loop, never an operating-system scheduler entry. It
never merges a request and never pushes a default branch; the guide in `.kit-cycle/guide.md`
explains the setup.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import quote

DAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
CLASSES = ('routine', 'sensitive', 'owner-only')  # least attention first
READY_STATES = ('accepted', 'in_progress')
RUNNER = 'cycle-runner/1'
BEGIN, END = '# engineering-kit:begin', '# engineering-kit:end'
HOOK_MARK = 'engineering-kit work-cycle pre-push guard'
TOOLS = {'github': 'gh', 'gitlab': 'glab', 'azure': 'az'}


class CycleError(Exception):
    pass


def now_local() -> datetime:
    return datetime.now().astimezone()


def stamp(moment: datetime) -> str:
    return moment.strftime('%Y%m%dT%H%M%S')


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, encoding='utf-8')
    if check and result.returncode:
        raise CycleError(f'git {" ".join(args)} failed: {result.stderr.strip()}')
    return result.stdout.strip() if result.returncode == 0 else ''


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as error:
        raise CycleError(f'cannot read {path}: {error}') from error


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')
    os.replace(temporary, path)


# ------------------------------------------------------------- the project

def project_root(start: Path) -> Path:
    root = Path(git(start, 'rev-parse', '--show-toplevel'))
    return root.resolve()


def common_dir(root: Path) -> Path:
    """The repository's shared Git folder, the same for every worktree."""
    value = Path(git(root, 'rev-parse', '--git-common-dir'))
    return (value if value.is_absolute() else root / value).resolve()


def project_config(root: Path) -> dict:
    project = read_json(root / '.engineering-kit' / 'project.json')
    if not isinstance(project, dict):
        raise CycleError(f'{root} has no .engineering-kit/project.json; adopt the kit first')
    return project


def cycle_config(project: dict) -> dict:
    config = project.get('cycle', {})
    if not isinstance(config, dict):
        raise CycleError('"cycle" in project.json must be an object')
    return config


def default_branch(root: Path, config: dict) -> str:
    if config.get('default_branch'):
        return config['default_branch']
    remote = config.get('remote', 'origin')
    head = git(root, 'symbolic-ref', '--quiet', f'refs/remotes/{remote}/HEAD', check=False)
    if head:
        return head.split(f'refs/remotes/{remote}/', 1)[1]
    for name in ('main', 'master'):
        if git(root, 'rev-parse', '--verify', '--quiet', f'refs/heads/{name}', check=False):
            return name
    raise CycleError('cannot tell the default branch; set "default_branch" under "cycle" in project.json')


def protected(root: Path, config: dict) -> set[str]:
    return {default_branch(root, config), *config.get('protected', [])}


def task_files(root: Path, project: dict) -> list[Path]:
    folder = (project.get('paths') or {}).get('tasks')
    return sorted((root / folder).glob('*.json')) if folder else []


def handoff_path(root: Path, project: dict, task_id: str) -> Path:
    return root / project['paths']['handoffs'] / f'{task_id}.md'


def ready_tasks(root: Path, project: dict) -> list[dict]:
    """Tasks the runner may take: accepted or in progress, and marked for an agent."""
    ready = []
    for path in task_files(root, project):
        task = read_json(path, {})
        if (isinstance(task, dict) and task.get('kit') == 'task/1' and task.get('state') in READY_STATES
                and task.get('next_actor') == 'agent' and isinstance(task.get('id'), str)):
            ready.append({'id': task['id'], 'file': str(path), 'state': task['state']})
    return ready


# ------------------------------------------------------------- the runner's home

def runner_home(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    if os.environ.get('KIT_CYCLE_HOME'):
        return Path(os.environ['KIT_CYCLE_HOME']).resolve()
    return Path.home() / '.kit-cycle'


def load_runner(home: Path) -> dict:
    config = read_json(home / 'runner.json')
    if config is None:
        raise CycleError(f'{home / "runner.json"} does not exist; run register in a repository first')
    if not isinstance(config, dict) or config.get('kit') != RUNNER:
        raise CycleError(f'{home / "runner.json"} is not a {RUNNER} file')
    return config


def new_runner() -> dict:
    return {'kit': RUNNER, 'repositories': [],
            'window': {'days': list(DAYS[:5]), 'start': '09:00', 'end': '17:00'},
            'agent': {'command': [], 'timeout_minutes': 120},
            'minimum_minutes': 20, 'poll_minutes': 10}


def register(home: Path, root: Path, name: str | None) -> list[str]:
    project_config(root)
    config = read_json(home / 'runner.json') or new_runner()
    name = name or root.name
    for entry in config['repositories']:
        if entry['name'] == name and Path(entry['path']) != root:
            raise CycleError(f'another repository is registered as {name}; choose one with --name')
    if not any(Path(entry['path']) == root for entry in config['repositories']):
        config['repositories'].append({'name': name, 'path': str(root)})
    write_json(home / 'runner.json', config)
    lines = [f'Registered {name} ({root}) in {home / "runner.json"}.']
    if not config['agent']['command']:
        lines.append('Set agent.command in that file to the agent command line before starting the runner.')
    return lines


def window_end(window: dict, moment: datetime) -> datetime | None:
    """When the working-hours window that holds MOMENT closes, or None outside it."""
    if DAYS[moment.weekday()] not in window['days']:
        return None
    start = datetime.combine(moment.date(), datetime.strptime(window['start'], '%H:%M').time(), moment.tzinfo)
    end = datetime.combine(moment.date(), datetime.strptime(window['end'], '%H:%M').time(), moment.tzinfo)
    return end if start <= moment < end else None


def claim_path(home: Path, repository: str, task_id: str) -> Path:
    return home / 'claims' / f'{repository}--{task_id}.json'


def claimed(home: Path, repository: str, task_id: str, moment: datetime) -> dict | None:
    claim = read_json(claim_path(home, repository, task_id))
    if claim and datetime.fromisoformat(claim['until']) > moment:
        return claim
    return None


def claim(home: Path, repository: str, task_id: str, holder: str, until: datetime) -> None:
    write_json(claim_path(home, repository, task_id),
               {'repository': repository, 'task': task_id, 'holder': holder, 'until': until.isoformat()})


def release(home: Path, repository: str, task_id: str) -> None:
    claim_path(home, repository, task_id).unlink(missing_ok=True)


def refresh_queue(home: Path, config: dict, moment: datetime) -> list[dict]:
    """First in, first out: a task joins the tail when it becomes ready and leaves when it stops
    being ready, so the order is the order tasks became ready, across every repository."""
    queue = read_json(home / 'queue.json', [])
    ready = {}
    for entry in config['repositories']:
        root = Path(entry['path'])
        try:
            project = project_config(root)
        except CycleError:
            continue
        for task in ready_tasks(root, project):
            ready[(entry['name'], task['id'])] = task
    kept = [item for item in queue if (item['repository'], item['task']) in ready]
    known = {(item['repository'], item['task']) for item in kept}
    for key in ready:
        if key not in known:
            kept.append({'repository': key[0], 'task': key[1], 'queued': moment.isoformat()})
    write_json(home / 'queue.json', kept)
    return kept


def next_task(home: Path, config: dict, moment: datetime) -> dict | None:
    for item in refresh_queue(home, config, moment):
        if not claimed(home, item['repository'], item['task'], moment):
            return item
    return None


PROMPT = """You are working unattended on task {task} in {repository}.

- Your working folder is a fresh worktree on branch {branch}, made from {base}.
- The task record is {task_file}; the project's kit files are in {root}, and the
  kit's procedures in {root}/.engineering-kit/kit/procedures. Records and
  handoffs live there, not in this worktree.
- Follow the kit's procedures for the task's current state, and the project's own
  instructions. Ask no questions: if the next step needs a person, record the question in
  the task, set "next_actor" to "owner" and stop.
- Before you stop, write the handoff {handoff} and update the task record.
- Deliver finished work with: {python} {cycle} deliver --task {task}
  It runs the checks, pushes this branch and opens a review request. Never merge it and
  never push {base}.
- Stop by {deadline}.
"""


def run_one(home: Path, config: dict, item: dict, moment: datetime, deadline: datetime) -> dict:
    """Claim ITEM, run the agent in a fresh worktree until DEADLINE, and leave a handoff."""
    entry = next(e for e in config['repositories'] if e['name'] == item['repository'])
    root = Path(entry['path'])
    project = project_config(root)
    settings = cycle_config(project)
    task_id = item['task']
    run_id = f'{stamp(moment)}-{item["repository"]}-{task_id}'
    record = {'kit': 'cycle-run/1', 'id': run_id, 'repository': item['repository'], 'task': task_id,
              'started': moment.isoformat(), 'outcome': 'unknown'}
    claim(home, item['repository'], task_id, 'runner', deadline + timedelta(minutes=10))
    try:
        base = default_branch(root, settings)
        remote = settings.get('remote', 'origin')
        start = base
        if git(root, 'remote', check=False).split().count(remote):
            fetched = subprocess.run(['git', 'fetch', '--quiet', remote, base], cwd=root, capture_output=True,
                                     text=True)
            record['fetch'] = 'ok' if fetched.returncode == 0 else fetched.stderr.strip()[-400:]
            if git(root, 'rev-parse', '--verify', '--quiet', f'refs/remotes/{remote}/{base}', check=False):
                start = f'{remote}/{base}'
        branch = f'kit/{task_id}-{stamp(moment)}'
        worktree = home / 'worktrees' / run_id
        git(root, 'worktree', 'add', '--quiet', '-b', branch, str(worktree), start)
        record.update(branch=branch, base=start, worktree=str(worktree))
        task_file = next((p for p in task_files(root, project) if read_json(p, {}).get('id') == task_id), None)
        if task_file is None:
            raise CycleError(f'the task record {task_id} is gone')
        handoff = handoff_path(root, project, task_id)
        handoff.parent.mkdir(parents=True, exist_ok=True)
        before = handoff.stat().st_mtime_ns if handoff.exists() else None
        cycle = root / '.kit-cycle' / 'cycle.py'
        values = {'task': task_id, 'repository': item['repository'], 'root': str(root), 'branch': branch,
                  'base': base, 'worktree': str(worktree), 'task_file': str(task_file), 'handoff': str(handoff),
                  'cycle': str(cycle), 'python': sys.executable, 'deadline': deadline.strftime('%H:%M')}
        prompt = PROMPT.format(**values)
        run_folder = home / 'runs'
        run_folder.mkdir(parents=True, exist_ok=True)
        prompt_file = run_folder / f'{run_id}.prompt.md'
        prompt_file.write_text(prompt, encoding='utf-8')
        values.update(prompt=prompt, prompt_file=str(prompt_file))
        command = [part.format(**values) for part in config['agent']['command']]
        if not command:
            raise CycleError('agent.command in runner.json is empty')
        found = shutil.which(command[0])  # on Windows also finds the .cmd shims package managers install
        if found is None:
            raise CycleError(f'the agent command {command[0]} is not on PATH')
        command[0] = found
        environment = dict(os.environ, **{f'KIT_CYCLE_{key.upper()}': value for key, value in values.items()
                                         if key != 'prompt'})
        limit = min(timedelta(minutes=config['agent'].get('timeout_minutes', 120)), deadline - moment)
        record['exit'], record['timed_out'] = run_agent(command, worktree, environment, limit.total_seconds(),
                                                       run_folder / f'{run_id}.log')
        wrote = handoff.exists() and handoff.stat().st_mtime_ns != before
        record['handoff'] = str(handoff)
        if not wrote:
            write_handoff(handoff, read_json(task_file, {}), record)
            record['handoff_written_by'] = 'runner'
        record['outcome'] = ('timed_out' if record['timed_out'] else
                             'finished' if record['exit'] == 0 and wrote else 'unknown')
    except (CycleError, OSError) as error:  # OSError: the agent command cannot start
        record.update(outcome='refused', reason=str(error))
    finally:
        release(home, item['repository'], task_id)
        record['ended'] = now_local().isoformat()
        write_json(home / 'runs' / f'{run_id}.json', record)
    return record


def run_agent(command: list[str], cwd: Path, environment: dict, seconds: float, log: Path) -> tuple[int | None, bool]:
    with log.open('wb') as output:
        if os.name == 'nt':
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=output, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=output, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            return process.wait(timeout=max(seconds, 1)), False
        except subprocess.TimeoutExpired:
            if os.name == 'nt':  # the whole tree, as an agent starts tools of its own
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(process.pid)], capture_output=True)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return None, True


def write_handoff(path: Path, task: dict, record: dict) -> None:
    """The handoff an agent that wrote none leaves, so the task never stops without one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    reason = ('the run reached its time limit' if record.get('timed_out')
              else f'the agent command exited with {record.get("exit")} and wrote no handoff')
    path.write_text(f"""# {task.get('title', record['task'])} handoff

Task: {record['task']}
Updated: {now_local().isoformat(timespec='seconds')}
State: {task.get('state', 'unknown')}

## State

The task runner stopped this run because {reason}. Its outcome is unknown.

## Evidence

- Run record: {record['id']}.json in the runner's runs folder.
- Worktree: {record.get('worktree')} on branch {record.get('branch')}.

## Open gates

- Nobody has checked what the run changed.

## Decisions and authority

- None recorded by the run.

## Next action

- Inspect the worktree and the run log before repeating the task; done when the task record says what happened.
""", encoding='utf-8')


def serve(home: Path, *, once: bool = False, clock=now_local, sleep=time.sleep, out=print) -> int:
    """Take tasks in queue order while the window is open; stop when it closes."""
    config = load_runner(home)
    window = config['window']
    minimum = timedelta(minutes=config.get('minimum_minutes', 20))
    runs = 0
    while True:
        moment = clock()
        end = window_end(window, moment)
        if end is None:
            out(f'Outside the working-hours window ({", ".join(window["days"])} {window["start"]} to '
                f'{window["end"]}); the runner stops. {runs} task runs.')
            return 0
        if end - moment < minimum:
            out(f'Less than {config.get("minimum_minutes", 20)} minutes remain before {window["end"]}; '
                f'the runner stops. {runs} task runs.')
            return 0
        item = next_task(home, config, moment)
        if item is None:
            if once:
                out('No task is ready; the runner stops.')
                return 0
            sleep(min(timedelta(minutes=config.get('poll_minutes', 10)), end - moment).total_seconds())
            continue
        out(f'{moment:%H:%M} {item["repository"]} {item["task"]}: starting')
        record = run_one(home, config, item, moment, end)
        runs += 1
        out(f'{clock():%H:%M} {item["repository"]} {item["task"]}: {record["outcome"]}'
            + (f' ({record["reason"]})' if record.get('reason') else ''))
        if record['outcome'] == 'refused':  # the same refusal would repeat at once
            return 1
        if once:
            return 0


# ------------------------------------------------------------- delivery

def parse_remote(url: str) -> tuple[str, str]:
    """Host and repository path of a remote address, for HTTPS and SSH forms."""
    match = (re.match(r'^[a-z+]+://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+?)(?:\.git)?/?$', url)
             or re.match(r'^(?:[^@/]+@)?([^/:]+):(.+?)(?:\.git)?/?$', url))
    if not match:
        raise CycleError(f'cannot read the remote address {url!r}')
    return match.group(1).lower(), match.group(2)


def host_kind(host: str, config: dict) -> str | None:
    if config.get('host'):
        return config['host']
    if host == 'github.com' or host in config.get('github_hosts', []):
        return 'github'
    if host in ('dev.azure.com', 'ssh.dev.azure.com') or host.endswith('.visualstudio.com'):
        return 'azure'
    if 'gitlab' in host or host in config.get('gitlab_hosts', []):
        return 'gitlab'
    return None


def compare_url(kind: str, host: str, path: str, base: str, branch: str) -> str:
    source, target = quote(branch, safe=''), quote(base, safe='')
    if kind == 'github':
        return f'https://{host}/{path}/compare/{target}...{source}?expand=1'
    if kind == 'gitlab':
        return (f'https://{host}/{path}/-/merge_requests/new?merge_request%5Bsource_branch%5D={source}'
                f'&merge_request%5Btarget_branch%5D={target}')
    if kind == 'azure':
        parts = path.split('/')
        if host == 'ssh.dev.azure.com':  # v3/ORG/PROJECT/REPO
            parts = parts[1:]
            host = 'dev.azure.com'
        else:  # ORG/PROJECT/_git/REPO
            parts = [part for part in parts if part != '_git']
        if host == 'dev.azure.com':
            organization, project, repository = parts[-3:]
            prefix = f'https://dev.azure.com/{organization}/{project}'
        else:  # ORG.visualstudio.com/PROJECT/_git/REPO
            project, repository = parts[-2:]
            prefix = f'https://{host}/{project}'
        return f'{prefix}/_git/{repository}/pullrequestcreate?sourceRef={source}&targetRef={target}'
    raise CycleError(f'no compare address for host kind {kind!r}')


def classify(paths: list[str], rules: dict) -> tuple[str, dict[str, list[str]]]:
    """The class of a change from its paths: the most demanding class any path falls in."""
    matched = {name: [path for path in paths if any(fnmatch.fnmatchcase(path, glob) for glob in rules.get(name, []))]
               for name in CLASSES[1:]}
    level = 'owner-only' if matched['owner-only'] else 'sensitive' if matched['sensitive'] else 'routine'
    return level, matched


def required_checks(project: dict, task: dict | None) -> list[tuple[str, str | None]]:
    checks = project.get('checks', {})
    if task:
        profile = project.get('profiles', {}).get(task.get('profile'))
        if not isinstance(profile, dict):
            raise CycleError(f'task {task["id"]} names no profile from project.json')
        names = profile.get('required_checks', [])
    else:
        names = list(checks)
    return [(name, checks[name].get('command')) for name in names]


def deliver(root: Path, worktree: Path, task_id: str | None, title: str | None, body: str | None,
            out=print) -> dict:
    project = project_config(root)
    settings = cycle_config(project)
    remote = settings.get('remote', 'origin')
    base = default_branch(root, settings)
    branch = git(worktree, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False)
    if not branch:
        raise CycleError('HEAD is not on a branch; deliver from the task branch')
    if branch in protected(root, settings):
        raise CycleError(f'{branch} is a protected branch; deliver from a task branch')
    if git(worktree, 'status', '--porcelain'):  # the checks would examine a state the push leaves out
        raise CycleError('the worktree has uncommitted changes; commit or remove them before delivering')
    task = None
    if task_id:
        task = next((t for t in map(lambda p: read_json(p, {}), task_files(root, project)) if t.get('id') == task_id),
                    None)
        if task is None:
            raise CycleError(f'no task record {task_id}')
    record = {'kit': 'cycle-delivery/1', 'branch': branch, 'base': base, 'task': task_id,
              'revision': git(worktree, 'rev-parse', 'HEAD'), 'at': now_local().isoformat(), 'checks': []}
    outcome_file = common_dir(root) / 'kit-cycle' / 'deliveries' / f'{stamp(now_local())}-{branch.replace("/", "-")}.json'
    try:
        host, path = parse_remote(git(worktree, 'remote', 'get-url', remote))
        kind = host_kind(host, settings)
        if kind not in TOOLS:
            raise CycleError(f'cannot tell which service hosts {host}; set "host" under "cycle" in project.json '
                             'to github, gitlab or azure')
        record.update(host=host, kind=kind, compare=compare_url(kind, host, path, base, branch))
        for name, command in required_checks(project, task):
            if not command:
                record['checks'].append({'id': name, 'result': 'unknown', 'evidence': 'performed by hand'})
                continue
            result = subprocess.run(command, shell=True, cwd=worktree, capture_output=True, text=True)
            passed = result.returncode == 0
            record['checks'].append({'id': name, 'result': 'pass' if passed else 'fail', 'command': command,
                                     'output': (result.stdout + result.stderr)[-2000:]})
            out(f'check {name}: {"pass" if passed else "fail"}')
            if not passed:
                record['outcome'] = 'checks_failed'
                return record
        fetched = git(worktree, 'rev-parse', '--verify', '--quiet', f'refs/remotes/{remote}/{base}', check=False)
        changed = git(worktree, 'diff', '--name-only', f'{fetched or base}...HEAD').splitlines()
        level, matched = classify(changed, settings.get('paths', {}))
        record.update({'class': level, 'matched': matched, 'changed': changed})
        if not changed:
            record['outcome'] = 'nothing_to_deliver'
            return record
        pushed = subprocess.run(['git', 'push', '--quiet', remote, f'HEAD:refs/heads/{branch}'], cwd=worktree,
                                capture_output=True, text=True)
        if pushed.returncode:
            record.update(outcome='push_failed', reason=pushed.stderr.strip()[-1000:])
            return record
        heading = f'[{level}] ' + (title or (task or {}).get('title') or git(worktree, 'log', '-1', '--format=%s'))
        text = body or describe(task, record)
        tool = shutil.which(TOOLS[kind])
        if tool is None:
            record.update(outcome='manual', reason=f'{TOOLS[kind]} is not installed; open the request by hand '
                                                   'at the compare address')
            return record
        record['request'] = open_request(kind, tool, host, worktree, base, branch, heading, text, level, record)
        record['outcome'] = 'opened' if record['request']['opened'] else 'manual'
        return record
    except CycleError as error:
        record.update(outcome='refused', reason=str(error))
        raise
    finally:
        write_json(outcome_file, record)
        out(f'delivery {record.get("outcome", "unknown")}: {outcome_file}')
        if record.get('compare') and record.get('outcome') == 'manual':
            out(f'open the request at {record["compare"]}')


def describe(task: dict | None, record: dict) -> str:
    lines = [f'Change class: {record["class"]}.', '']
    if task:
        lines += [f'Task: {task["id"]}, {task.get("title", "")}', '']
    lines += ['Checks:'] + [f'- {c["id"]}: {c["result"]}' for c in record['checks']]
    lines += ['', 'Opened by the work-cycle delivery command. It never merges; a person does.']
    return '\n'.join(lines)


def open_request(kind: str, tool: str, host: str, cwd: Path, base: str, branch: str, title: str, body: str,
                 level: str, record: dict) -> dict:
    """Open a review request; the class goes in the title on every host and as a label where the
    host's tool can add one after creation, so a missing label never stops delivery."""
    environment = dict(os.environ)
    if kind == 'github':
        if host != 'github.com':
            environment['GH_HOST'] = host
        create = [tool, 'pr', 'create', '--base', base, '--head', branch, '--title', title, '--body', body]
        label = [tool, 'pr', 'edit', branch, '--add-label', level]
    elif kind == 'gitlab':
        environment['GITLAB_HOST'] = host
        create = [tool, 'mr', 'create', '--source-branch', branch, '--target-branch', base, '--title', title,
                  '--description', body, '--yes']
        label = [tool, 'mr', 'update', branch, '--label', level]
    else:
        create = [tool, 'repos', 'pr', 'create', '--source-branch', branch, '--target-branch', base,
                  '--title', title, '--description', body, '--detect', 'true', '--output', 'json']
        label = None  # the class stays in the title
    made = subprocess.run(create, cwd=cwd, env=environment, capture_output=True, text=True)
    result = {'tool': Path(tool).name, 'opened': made.returncode == 0,
              'output': (made.stdout + made.stderr).strip()[-1000:]}
    if made.returncode:
        record['reason'] = f'{Path(tool).name} could not open the request; open it by hand at the compare address'
        return result
    if label:
        labelled = subprocess.run(label, cwd=cwd, env=environment, capture_output=True, text=True)
        result['label'] = level if labelled.returncode == 0 else f'not set: {labelled.stderr.strip()[-300:]}'
    else:
        result['label'] = 'in the title only'
    return result


# ------------------------------------------------------------- guards and excludes

def guard_push(root: Path, remote: str, lines: list[str]) -> list[str]:
    """Refusals for a push: a protected branch is never pushed, created or deleted."""
    try:  # a worktree holds no kit files in a shared repository; the registered checkout does
        settings = cycle_config(project_config(main_checkout(root)))
    except CycleError:
        settings = {}
    try:
        names = protected(root, dict(settings, remote=remote))
    except CycleError:  # no default branch to read: guard the usual names
        names = {'main', 'master', *settings.get('protected', [])}
    refused = []
    for line in lines:
        parts = line.split()
        if len(parts) == 4 and parts[2].startswith('refs/heads/') and parts[2][len('refs/heads/'):] in names:
            refused.append(f'refusing to push {parts[2][len("refs/heads/"):]}: protected branches change only '
                           'through a reviewed request that a person merges')
    return refused


SHELL_SPLIT = re.compile(r'&&|\|\||[;|\n]')


def guard_edit(command: str, protected_names: set[str]) -> list[str]:
    """Refusals for an agent's shell command: in-place stream edits, bypassed hooks and pushes to a
    protected branch. A command that cannot be read is allowed; the pre-push guard still applies."""
    refused = []
    for part in SHELL_SPLIT.split(command):
        words = part.split()
        if not words:
            continue
        program = PurePosixPath(words[0]).name
        if program in ('sed', 'perl') and any(re.fullmatch(r'-[a-zA-Z]*i\S*|--in-place\S*', w) for w in words[1:]):
            refused.append(f'{program} -i rewrites files in place; use the agent\'s edit tool')
        if program == 'git':
            if 'core.hooksPath' in part or '--no-verify' in words:
                refused.append('the command bypasses Git hooks, which run the pre-push guard')
            if 'push' in words:
                after = words[words.index('push') + 1:]
                targets = [w.rsplit(':', 1)[-1].removeprefix('+').removeprefix('refs/heads/')
                           for w in after if not w.startswith('-')][1:]
                if any(target in protected_names for target in targets):
                    refused.append('the command pushes a protected branch; deliver a task branch instead')
                if any(w in ('-f', '--force', '--mirror') for w in after):
                    refused.append('the command force-pushes or mirrors; deliver a task branch instead')
    return refused


HOOK = """#!/bin/sh
# {mark}. Installed by {cycle} guards install; remove with guards remove.
exec "{python}" "{cycle}" guard-push "$@"
"""


def hooks_folder(root: Path) -> Path:
    configured = git(root, 'config', '--get', 'core.hooksPath', check=False)
    if configured:
        raise CycleError(f'core.hooksPath is set to {configured}; add `{Path(sys.executable).as_posix()} '
                         f'.kit-cycle/cycle.py guard-push "$@"` to that pre-push hook yourself')
    return common_dir(root) / 'hooks'


def install_guards(root: Path) -> list[str]:
    hook = hooks_folder(root) / 'pre-push'
    if hook.exists() and HOOK_MARK not in hook.read_text(encoding='utf-8', errors='replace'):
        raise CycleError(f'{hook} already exists; call `.kit-cycle/cycle.py guard-push "$@"` from it yourself')
    hook.parent.mkdir(parents=True, exist_ok=True)
    cycle = (root / '.kit-cycle' / 'cycle.py').as_posix()
    hook.write_text(HOOK.format(mark=HOOK_MARK, cycle=cycle, python=Path(sys.executable).as_posix()),
                    encoding='utf-8', newline='\n')
    hook.chmod(0o755)
    command = f'{Path(sys.executable).as_posix()} {cycle} guard-edit'
    return [f'Installed the pre-push guard in {hook}.',
            'For the edit guard, register this command as a hook that runs before each shell command in the '
            f'agent client, as .kit-cycle/guide.md shows: {command}']


def remove_guards(root: Path) -> list[str]:
    hook = hooks_folder(root) / 'pre-push'
    if hook.exists() and HOOK_MARK in hook.read_text(encoding='utf-8', errors='replace'):
        hook.unlink()
        return [f'Removed {hook}.']
    return ['No work-cycle pre-push guard is installed.']


def exclude(root: Path) -> list[str]:
    """List the kit's files in Git's local exclude file, which is never committed or shared."""
    project = project_config(root)
    lock = read_json(root / '.engineering-kit' / 'lock.json', {}) or {}
    paths = {'.engineering-kit/', '.kit-cycle/', *(f'{p}/' for p in (project['paths']['tasks'],
                                                                   project['paths']['handoffs']))}
    paths |= {name for name in lock.get('files', {}) if not name.startswith('.engineering-kit/')}
    tracked = sorted(name for name in (n.rstrip('/') for n in paths)
                     if git(root, 'ls-files', '--', name, check=False))
    blocks = sorted(key.split(':', 1)[1] for key in lock.get('blocks', {}))
    target = common_dir(root) / 'info' / 'exclude'
    current = target.read_text(encoding='utf-8') if target.exists() else ''
    if BEGIN in current:
        before, rest = current.split(BEGIN, 1)
        current = before + (rest.split(END, 1)[1].lstrip('\n') if END in rest else '')
    lines = [BEGIN, *sorted('/' + p for p in paths), END]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(current.rstrip('\n') + ('\n' if current.strip() else '') + '\n'.join(lines) + '\n',
                      encoding='utf-8', newline='\n')
    report = [f'Listed {len(paths)} kit paths in {target}; colleagues see none of them.']
    if tracked:
        report.append('Already tracked, so the exclude does not hide them: ' + ', '.join(tracked))
    if blocks:
        report.append('These instruction files carry the kit\'s entry block and stay visible if they are '
                      'tracked: ' + ', '.join(blocks))
    return report


# ------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='cycle.py', description=__doc__.splitlines()[0])
    parser.add_argument('--home', help='the runner\'s state folder (default: KIT_CYCLE_HOME or ~/.kit-cycle)')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('register').add_argument('--name')
    commands.add_parser('run').add_argument('--once', action='store_true')
    commands.add_parser('queue')
    for name in ('claim', 'release'):
        command = commands.add_parser(name)
        command.add_argument('task')
        command.add_argument('--repository', help='default: the name this repository is registered under')
        if name == 'claim':
            command.add_argument('--hours', type=float, default=8)
    command = commands.add_parser('deliver')
    command.add_argument('--task')
    command.add_argument('--title')
    command.add_argument('--body')
    commands.add_parser('exclude')
    commands.add_parser('guards').add_argument('action', choices=('install', 'remove'))
    command = commands.add_parser('guard-push')
    command.add_argument('remote', nargs='?', default='origin')
    command.add_argument('url', nargs='?')
    commands.add_parser('guard-edit')
    args = parser.parse_args(argv)
    try:
        if args.command == 'guard-edit':
            return edit_hook(sys.stdin.read())
        root = project_root(Path.cwd())
        if args.command == 'guard-push':
            refused = guard_push(root, args.remote, sys.stdin.read().splitlines())
            for line in refused:
                print(line, file=sys.stderr)
            return 1 if refused else 0
        home = runner_home(args.home)
        if args.command == 'register':
            lines = register(home, root, args.name)
        elif args.command == 'run':
            return serve(home, once=args.once)
        elif args.command == 'queue':
            config = load_runner(home)
            moment = now_local()
            queue = refresh_queue(home, config, moment)
            lines = [f'{n}. {i["repository"]} {i["task"]} (queued {i["queued"]})'
                     + (' claimed' if claimed(home, i['repository'], i['task'], moment) else '')
                     for n, i in enumerate(queue, 1)] or ['No task is ready.']
        elif args.command in ('claim', 'release'):
            config = load_runner(home)
            name = args.repository or next((e['name'] for e in config['repositories']
                                            if Path(e['path']) == root), None)
            if name is None:
                raise CycleError('this repository is not registered; run register or pass --repository')
            if args.command == 'claim':
                until = now_local() + timedelta(hours=args.hours)
                claim(home, name, args.task, 'person', until)
                lines = [f'The runner skips {name} {args.task} until {until:%Y-%m-%d %H:%M}.']
            else:
                release(home, name, args.task)
                lines = [f'Released {name} {args.task}.']
        elif args.command == 'deliver':
            record = deliver(main_checkout(root), root, args.task, args.title, args.body)
            return 0 if record.get('outcome') in ('opened', 'manual', 'nothing_to_deliver') else 1
        elif args.command == 'exclude':
            lines = exclude(root)
        else:
            lines = install_guards(root) if args.action == 'install' else remove_guards(root)
    except CycleError as error:
        print(f'refused: {error}', file=sys.stderr)
        return 1
    print('\n'.join(lines))
    return 0


def main_checkout(root: Path) -> Path:
    """The registered checkout that holds the kit files, also when run from one of its worktrees."""
    script = Path(__file__).resolve().parent.parent
    if (script / '.engineering-kit' / 'project.json').is_file():
        return script
    return root


def edit_hook(payload: str) -> int:
    try:
        data = json.loads(payload)
        command = (data.get('tool_input') or {}).get('command') or ''
        root = project_root(Path(data.get('cwd') or Path.cwd()))
        try:
            settings = cycle_config(project_config(main_checkout(root)))
        except CycleError:
            settings = {}
        try:
            names = protected(root, settings)
        except CycleError:
            names = {'main', 'master', *settings.get('protected', [])}
    except (ValueError, AttributeError, CycleError, OSError):
        return 0  # fail open; the pre-push guard still refuses protected pushes
    refused = guard_edit(command, names) if isinstance(command, str) else []
    for line in refused:
        print(f'refused by the work-cycle edit guard: {line}', file=sys.stderr)
    return 2 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
