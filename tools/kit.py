#!/usr/bin/env python3
"""Reference tool for the engineering kit, contract version 1.

Standard library only, Python 3.11 or later; `scan-secrets` and
`integrated` also need the git command line. It reads records and never runs
a command that a project or a release supplies.

    kit.py check [--root DIR] [--json]     project, every task and handoff
    kit.py check-task FILE [--root DIR]    one task record
    kit.py check-handoff FILE [--root DIR] one handoff
    kit.py scan-secrets [--root DIR]       credential shapes in tracked files
    kit.py integrated CANDIDATE REVISION   do they differ outside the records?

Exit status: 0 when nothing is refused, 1 when something is, 2 for a usage
error. Each refusal names the contract rule it enforces (CONTRACT.md).
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

CONTRACT_VERSION = 1
# Contract rules and whether they are fixed (accept no exception).
RULES = {
    'ACCEPT': False, 'PROFILE': False, 'CANDIDATE': True, 'CHECKS': True,
    'REVIEW': False, 'EFFECTS': True, 'RELEASE': False, 'BOUNDARY': True,
    'UNKNOWN': True, 'REPRODUCE': False, 'DOCS': False, 'HANDOFF': False,
    'LESSON': False, 'ENFORCEMENT': False, 'SECRETS': True, 'AUTHORITY': True,
    'PRESERVE': False, 'DECIDE': False,
}
FORMAT = 'FORMAT'  # a record the reader cannot interpret; not a contract rule
STATES = ('proposed', 'accepted', 'in_progress', 'candidate', 'reviewed',
          'released', 'verified', 'closed')
STOPPED = ('blocked', 'failed', 'cancelled')
CHECK_RESULTS = ('pass', 'fail', 'skipped', 'unknown')
EFFECT_STATUSES = ('planned', 'done', 'failed', 'uncertain', 'rolled_back')
ENFORCED = ('guidance', 'partial', 'checked', 'integration')
HANDOFF_SECTIONS = ('State', 'Evidence', 'Open gates', 'Decisions and authority', 'Next action')
LIST_ITEM = re.compile(r'^(?:[-*+]|\d+[.)])\s+\S')
CLOCK_SKEW = timedelta(minutes=5)


@dataclass(frozen=True)
class Finding:
    rule: str
    where: str
    message: str

    def __str__(self) -> str:
        return f'refuse  {self.rule:<11} {self.where}: {self.message}'


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_time(value) -> datetime | None:
    if not text(value):
        return None
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def same_identity(first, second) -> bool:
    """Names in records are compared without case or surrounding space; the record cannot prove who acted."""
    return text(first) and text(second) and first.strip().casefold() == second.strip().casefold()


def parse_date(value) -> bool:
    return text(value) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None and (
        parse_time(value + 'T00:00:00+00:00') is not None)


def relative_path(value) -> bool:
    if not text(value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and '..' not in path.parts and '\\' not in value


# ---------------------------------------------------------------- project

def check_project(project, root: Path | None = None, where: str = 'project.json') -> list[Finding]:
    found: list[Finding] = []

    def refuse(rule, message):
        found.append(Finding(rule, where, message))

    if not isinstance(project, dict) or project.get('kit') != 'project/1':
        refuse(FORMAT, 'needs "kit": "project/1"')
        return found
    left = placeholders(project)
    if left:
        refuse(FORMAT, 'replace the template placeholders in ' + ', '.join(left))
    for field in ('name', 'scope'):
        if not text(project.get(field)):
            refuse(FORMAT, f'needs a {field}')
    boundaries = project.get('boundaries')
    if (not isinstance(boundaries, list) or not boundaries or not all(map(text, boundaries))
            or len(set(boundaries)) != len(boundaries)):
        refuse(FORMAT, 'boundaries must be a non-empty list of distinct names, weakest first')
    meaning = project.get('boundary_meaning', {})
    if not isinstance(meaning, dict) or not set(meaning) <= set(boundaries if isinstance(boundaries, list) else []):
        refuse(FORMAT, 'boundary_meaning describes only boundaries the project defines')
    checks = project.get('checks')
    if not isinstance(checks, dict) or not all(isinstance(v, dict) and text(v.get('description'))
                                               for v in checks.values()):
        refuse(FORMAT, 'checks must map each check ID to an object with a description')
        checks = {}
    authority = project.get('authority') if isinstance(project.get('authority'), dict) else {}
    roles = authority.get('roles')
    if not isinstance(roles, dict) or not roles:
        refuse(FORMAT, 'authority.roles must name at least one role')
        roles = {}
    effects = authority.get('effects')
    if not isinstance(effects, dict):
        refuse(FORMAT, 'authority.effects must map effect kinds to the roles that may authorize them')
    else:
        for kind, allowed in effects.items():
            if not isinstance(allowed, list) or not allowed or not set(allowed) <= set(roles):
                refuse('EFFECTS', f'effect kind "{kind}" must list roles defined in authority.roles')
    exceptions = project.get('exceptions', [])
    if not isinstance(exceptions, list):
        refuse(FORMAT, 'exceptions must be a list')
        exceptions = []
    excepted = set()
    for number, entry in enumerate(exceptions, 1):
        label = f'exception {number}'
        if not isinstance(entry, dict):
            refuse(FORMAT, f'{label} must be an object')
            continue
        rule = entry.get('rule')
        if rule not in RULES:
            refuse(FORMAT, f'{label} names unknown rule {rule!r}')
            continue
        if RULES[rule]:
            refuse(rule, f'{label}: {rule} is fixed and accepts no exception')
            continue
        if not (text(entry.get('reason')) and entry.get('approved_by') in roles
                and parse_date(entry.get('date')) and scope_ok(entry.get('scope'))):
            refuse(rule, f'{label} needs a scope (project, profile:NAME or task:ID), a reason, '
                         'an approving role from authority.roles and a date (YYYY-MM-DD)')
            continue
        excepted.add((rule, entry['scope']))
    profiles = project.get('profiles')
    if not isinstance(profiles, dict) or not profiles:
        refuse(FORMAT, 'profiles must define at least one delivery profile')
        profiles = {}
    for name, profile in profiles.items():
        label = f'profile "{name}"'
        if not isinstance(profile, dict):
            refuse(FORMAT, f'{label} must be an object')
            continue
        required = profile.get('required_checks')
        if not isinstance(required, list) or not set(required) <= set(checks):
            refuse('PROFILE', f'{label} must list required_checks defined in checks')
        if profile.get('review') not in ('required', 'none'):
            refuse('PROFILE', f'{label} review must be "required" or "none"')
        elif profile['review'] == 'none' and not ({('REVIEW', 'project'), ('REVIEW', f'profile:{name}')}
                                                  & excepted):
            refuse('REVIEW', f'{label} skips review without a recorded REVIEW exception')
        for flag in ('release', 'reproduction'):
            if not isinstance(profile.get(flag, False), bool):
                refuse('PROFILE', f'{label} {flag} must be true or false')
    instructions = project.get('instructions')
    if not isinstance(instructions, dict) or instructions.get('precedence') != 'stricter':
        refuse(FORMAT, 'instructions.precedence must be "stricter"')
    else:
        clients = instructions.get('clients')
        if not isinstance(clients, dict):
            refuse(FORMAT, 'instructions.clients must map each agent client to its instruction files')
        else:
            for client, files in clients.items():
                if not isinstance(files, list) or not files or not all(map(relative_path, files)):
                    refuse(FORMAT, f'instructions for "{client}" must list relative file paths')
                elif root is not None:
                    for name in files:
                        if not (root / name).is_file():
                            refuse(FORMAT, f'instruction file {name} for "{client}" does not exist')
    rules = project.get('rules', [])
    if not isinstance(rules, list):
        refuse(FORMAT, 'rules must be a list')
        rules = []
    seen = set()
    for number, rule in enumerate(rules, 1):
        if not isinstance(rule, dict) or not text(rule.get('id')) or not text(rule.get('text')):
            refuse(FORMAT, f'project rule {number} needs an id and text')
            continue
        if rule['id'] in seen or rule['id'] in RULES:
            refuse(FORMAT, f'project rule id {rule["id"]} is not unique')
        seen.add(rule['id'])
        if rule.get('enforced') not in ENFORCED:
            refuse('ENFORCEMENT', f'project rule {rule["id"]} must say how it is enforced: '
                                  + ', '.join(ENFORCED))
        elif rule['enforced'] != 'guidance' and not text(rule.get('by')):
            refuse('ENFORCEMENT', f'project rule {rule["id"]} must name what enforces it in "by"')
    paths = project.get('paths')
    if not isinstance(paths, dict) or not all(relative_path(paths.get(k)) for k in ('tasks', 'handoffs')):
        refuse(FORMAT, 'paths.tasks and paths.handoffs must be relative paths inside the project')
    integrations = project.get('integrations', {})
    if not isinstance(integrations, dict) or not all(
            isinstance(v, dict) and isinstance(v.get('grant', []), list) for v in integrations.values()):
        refuse(FORMAT, 'integrations must map each name to {"grant": [permissions]}')
    return found


PLACEHOLDER_TEXT = 'replace with'  # how every template marks a value the project must supply


def placeholders(value, path: str = '') -> list[str]:
    """Dotted paths of template placeholder values left in a record."""
    if isinstance(value, dict):
        return [p for key, item in value.items() for p in placeholders(item, f'{path}.{key}' if path else key)]
    if isinstance(value, list):
        return [p for number, item in enumerate(value) for p in placeholders(item, f'{path}.{number}')]
    return [path] if isinstance(value, str) and PLACEHOLDER_TEXT in value.casefold() else []


def scope_ok(scope) -> bool:
    return scope == 'project' or (text(scope) and re.fullmatch(r'(profile|task):\S+', scope) is not None)


def exceptions_for(project, task) -> set[str]:
    scopes = {'project', f'profile:{task.get("profile")}', f'task:{task.get("id")}'}
    return {e['rule'] for e in project.get('exceptions', [])
            if isinstance(e, dict) and e.get('scope') in scopes and e.get('rule') in RULES
            and not RULES[e['rule']]}


# ------------------------------------------------------------------- task

def check_task(task, project, where: str = 'task') -> list[Finding]:
    found: list[Finding] = []

    def refuse(rule, message):
        found.append(Finding(rule, where, message))

    if not isinstance(task, dict) or task.get('kit') != 'task/1':
        refuse(FORMAT, 'needs "kit": "task/1"')
        return found
    left = placeholders(task)
    if left:
        refuse(FORMAT, 'replace the template placeholders in ' + ', '.join(left))
    for field in ('id', 'title'):
        if not text(task.get(field)):
            refuse(FORMAT, f'needs {field}')
    state = task.get('state')
    if state not in STATES + STOPPED:
        refuse(FORMAT, f'state must be one of {", ".join(STATES + STOPPED)}')
        return found
    stage = STATES.index(state) if state in STATES else -1

    def reached(name):
        return stage >= STATES.index(name)

    if reached('accepted') and not text(task.get('author')):
        refuse(FORMAT, 'an accepted task names its author, who implements it')
    task = dict(task)
    for field in ('checks', 'not_applicable', 'reviews', 'effects', 'verification', 'contributors'):
        if not isinstance(task.setdefault(field, []), list):
            refuse('EFFECTS' if field == 'effects' else FORMAT, f'{field} must be a list')
            task[field] = []

    profiles = project.get('profiles', {}) if isinstance(project, dict) else {}
    boundaries = project.get('boundaries', []) if isinstance(project, dict) else []
    profile = profiles.get(task.get('profile')) if task.get('profile') in profiles else None
    if reached('accepted') and profile is None:
        refuse('PROFILE', f'profile {task.get("profile")!r} is not defined in project.json')
    profile = profile or {}
    required = [c for c in profile.get('required_checks', [])]
    not_applicable = {}
    for entry in task.get('not_applicable', []):
        if not isinstance(entry, dict) or entry.get('check') not in required or not text(entry.get('reason')):
            refuse('PROFILE', 'each not_applicable entry names a required check of the profile and a reason')
        else:
            not_applicable[entry['check']] = entry['reason']
    required = [c for c in required if c not in not_applicable]

    requirement = task.get('requirement')
    if reached('accepted'):
        if not isinstance(requirement, dict):
            refuse('ACCEPT', 'an accepted task records its requirement')
            requirement = {}
        missing = [f for f in ('revision', 'problem', 'decision_owner') if not text(requirement.get(f))]
        if missing:
            refuse('ACCEPT', 'requirement needs ' + ', '.join(missing))
        if not isinstance(requirement.get('excluded'), list):
            refuse('ACCEPT', 'requirement.excluded must list what is out of scope (it may be empty)')
        examples = requirement.get('acceptance')
        if (not isinstance(examples, list) or not examples
                or not all(isinstance(e, dict) and text(e.get('id')) and text(e.get('example')) for e in examples)):
            refuse('ACCEPT', 'requirement.acceptance needs at least one example with an id')
        if requirement.get('acceptance_boundary') not in boundaries:
            refuse('ACCEPT', 'requirement.acceptance_boundary must be one of the project boundaries: '
                             + ', '.join(map(str, boundaries)))
    requirement = requirement if isinstance(requirement, dict) else {}

    candidate = task.get('candidate') if isinstance(task.get('candidate'), dict) else {}
    revision = candidate.get('revision') if text(candidate.get('revision')) else None
    if reached('candidate') and (revision is None or not text(candidate.get('base'))):
        refuse('CANDIDATE', 'a candidate task names its candidate revision and the base it started from')
    # Revisions that differ from the candidate only in process files (records,
    # project configuration and kit files), such as the merge that lands it.
    # Releases and verification may name them; checks and reviews must name
    # the candidate itself.
    landed = {revision} if revision else set()
    integrated = candidate.get('integrated', [])
    for entry in integrated if isinstance(integrated, list) else [None]:
        if not (isinstance(entry, dict) and text(entry.get('revision')) and text(entry.get('evidence'))):
            refuse('CANDIDATE', 'each integrated revision names its revision and the evidence that it equals '
                                'the candidate outside the process files')
        else:
            landed.add(entry['revision'])

    # Evidence about another revision is history: it never counts, and a
    # refusal names CANDIDATE when stale evidence is all there is.
    def stale(rule, label, revisions, missing):
        if revisions:
            refuse('CANDIDATE', f'{label} examined {", ".join(sorted(revisions))}, not the candidate '
                                f'{revision!r}; repeat it on the candidate')
        else:
            refuse(rule, missing)

    latest_check, stale_checks = {}, {}
    for entry in task.get('checks', []):
        if (not isinstance(entry, dict) or not text(entry.get('id')) or not text(entry.get('revision'))
                or entry.get('result') not in CHECK_RESULTS):
            refuse(FORMAT, 'each check needs an id, a revision and a result: ' + ', '.join(CHECK_RESULTS))
            continue
        if revision is not None and entry.get('revision') == revision:
            latest_check[entry['id']] = entry
        else:
            stale_checks.setdefault(entry['id'], set()).add(str(entry.get('revision')))
    if reached('candidate'):  # a candidate has run its required checks; from review on they pass
        for check in required:
            entry = latest_check.get(check)
            if entry is None:
                stale('CHECKS', f'check "{check}"', stale_checks.get(check),
                      f'required check "{check}" has no result for the candidate')
            elif reached('reviewed') and entry['result'] != 'pass':
                rule = 'UNKNOWN' if entry['result'] == 'unknown' else 'CHECKS'
                outcome = {'fail': 'failed', 'skipped': 'was skipped', 'unknown': 'has an unknown result'}
                refuse(rule, f'required check "{check}" {outcome[entry["result"]]} on the candidate; '
                             'only a pass counts')

    if reached('reviewed') and profile.get('reproduction'):
        reproduction = task.get('reproduction')
        if not (isinstance(reproduction, dict) and text(reproduction.get('check'))
                and reproduction.get('base') == candidate.get('base') and reproduction.get('base') != revision
                and reproduction.get('base_result') == 'fail' and reproduction.get('candidate_result') == 'pass'):
            refuse('REPRODUCE', "a defect needs a reproduction check that failed on the candidate's base "
                                'revision and passes on the candidate')

    approvals, stale_approvals = [], set()
    for review in task.get('reviews', []):
        if not isinstance(review, dict) or not text(review.get('reviewer')) or review.get('verdict') not in (
                'approve', 'changes'):
            refuse(FORMAT, 'each review needs a reviewer, a revision and a verdict: approve or changes')
            continue
        findings = review.get('findings', [])
        if not isinstance(findings, list):
            refuse(FORMAT, 'review findings must be a list')
            findings = []
        for finding in findings:
            if not isinstance(finding, dict) or finding.get('status') not in ('open', 'resolved'):
                refuse(FORMAT, 'each finding needs a status: open or resolved')
            elif reached('reviewed') and finding.get('blocking') and finding['status'] == 'open':
                refuse('REVIEW', f'blocking finding {finding.get("id", "?")} from {review["reviewer"]} is open')
        if review['verdict'] != 'approve':
            continue
        if any(same_identity(review['reviewer'], name) for name in [task.get('author'), *task['contributors']]):
            refuse('REVIEW', f'{review["reviewer"]} reviewed work they wrote or recorded')
        elif revision is not None and review.get('revision') == revision:
            approvals.append(review)
        else:
            stale_approvals.add(str(review.get('revision')))
    if reached('reviewed') and profile.get('review', 'required') == 'required' and not approvals:
        stale('REVIEW', 'the approving review', stale_approvals,
              'no approving review of the candidate by someone other than the author')

    authority = project.get('authority', {}) if isinstance(project, dict) else {}
    allowed_effects = authority.get('effects', {}) if isinstance(authority, dict) else {}
    effects = task.get('effects', [])
    for number, effect in enumerate(effects if isinstance(effects, list) else [], 1):
        label = f'effect {number}'
        if not isinstance(effect, dict):
            refuse(FORMAT, f'{label} must be an object')
            continue
        kind = effect.get('kind')
        if kind not in allowed_effects:
            refuse('EFFECTS', f'{label}: kind {kind!r} is not in the project authority policy')
        elif effect.get('authorized_by') not in allowed_effects[kind]:
            refuse('EFFECTS', f'{label}: {effect.get("authorized_by")!r} may not authorize {kind}; '
                              f'allowed: {", ".join(allowed_effects[kind])}')
        if not text(effect.get('authorization')) or not text(effect.get('target')):
            refuse('EFFECTS', f'{label} names its target and the authorization it relies on')
        if effect.get('door') == 'two-way':
            if not text(effect.get('rollback')):
                refuse('EFFECTS', f'{label} is two-way but names no rollback')
        elif effect.get('door') == 'one-way':
            if not text(effect.get('irreversible')):
                refuse('EFFECTS', f'{label} is one-way but does not say what cannot be undone')
        else:
            refuse('EFFECTS', f'{label} door must be two-way or one-way')
        status = effect.get('status')
        if status not in EFFECT_STATUSES:
            refuse(FORMAT, f'{label} status must be one of {", ".join(EFFECT_STATUSES)}')
        elif reached('verified') and status in ('planned', 'uncertain'):
            refuse('UNKNOWN' if status == 'uncertain' else 'EFFECTS',
                   f'{label} is {status}; a verified task has no unapplied or uncertain effect')

    release = task.get('release')
    if state == 'released' and not profile.get('release', False):
        refuse('PROFILE', f'profile {task.get("profile")!r} has no release stage')
    if reached('released') and profile.get('release', False):
        if not isinstance(release, dict):
            refuse('RELEASE', 'a released task records its release')
        else:
            if not text(release.get('artifact')) or not text(release.get('rollback')):
                refuse('RELEASE', 'release names its artifact identity and rollback target')
            if not isinstance(release.get('checks'), list) or not set(required) <= set(release['checks']):
                refuse('RELEASE', 'release lists every required check it passed')
            if release.get('source') not in landed:
                refuse('CANDIDATE', f'the release was built from {release.get("source")!r}, not the candidate '
                                    f'{revision!r} or a recorded integrated revision')

    target = requirement.get('acceptance_boundary')
    strength = {name: number for number, name in enumerate(boundaries)}
    latest, stale_passes = {}, set()  # the newest result at each boundary decides
    for entry in task.get('verification', []):
        if not isinstance(entry, dict) or entry.get('boundary') not in strength or entry.get(
                'result') not in CHECK_RESULTS:
            refuse(FORMAT, 'each verification names a project boundary, a revision and a result')
            continue
        if target not in strength or strength[entry['boundary']] < strength[target]:
            continue
        if entry.get('revision') in landed:
            latest[entry['boundary']] = entry
        elif entry['result'] == 'pass':
            stale_passes.add(str(entry.get('revision')))
    passes = [e for e in latest.values() if e['result'] == 'pass']
    open_results = [e for e in latest.values() if e['result'] != 'pass']
    if reached('verified'):
        if not passes:
            stale('BOUNDARY', 'the passing verification', stale_passes,
                  f'no passing verification of the candidate at the acceptance boundary '
                  f'{target!r} or stronger')
        for entry in open_results:
            refuse('UNKNOWN' if entry['result'] == 'unknown' else 'BOUNDARY',
                   f'verification at {entry["boundary"]} is {entry["result"]}; it stays open until resolved')

    if state == 'closed':
        documentation = task.get('documentation')
        if not (isinstance(documentation, dict) and (
                (isinstance(documentation.get('updated'), list) and documentation['updated']
                 and all(map(text, documentation['updated']))) or text(documentation.get('none')))):
            refuse('DOCS', 'a closed task lists the documentation it updated, or why none changed')

    waived = exceptions_for(project if isinstance(project, dict) else {}, task)
    return [f for f in found if f.rule not in waived]


# ---------------------------------------------------------------- handoff

def check_handoff(source: str, task_states: dict[str, str] | None = None, where: str = 'handoff',
                  now: datetime | None = None) -> list[Finding]:
    found: list[Finding] = []

    def refuse(message):
        found.append(Finding('HANDOFF', where, message))

    head, _, body = source.partition('\n## ')
    body = '## ' + body if body else ''
    lines = head.splitlines()
    if not lines or not re.fullmatch(r'# .+ handoff', lines[0].strip()):
        refuse('the first line is "# <title> handoff"')
    fields = dict(re.findall(r'^(Task|Updated|State): *(.+?) *$', head, re.M))
    for field in ('Task', 'Updated', 'State'):
        if field not in fields:
            refuse(f'needs a "{field}:" line before the first section')
    moment = parse_time(fields.get('Updated'))
    if 'Updated' in fields and moment is None:
        refuse('Updated must be an ISO time with a time zone')
    elif moment is not None and moment > (now or datetime.now(timezone.utc)) + CLOCK_SKEW:
        refuse('Updated is in the future')
    if 'State' in fields and fields['State'] not in STATES + STOPPED:
        refuse(f'State must be a task state: {", ".join(STATES + STOPPED)}')
    sections = re.split(r'^## +(.+?) *$', body, flags=re.M)[1:]
    names = tuple(sections[0::2])
    if names != HANDOFF_SECTIONS:
        refuse('sections must be, in order: ' + ', '.join(HANDOFF_SECTIONS))
    else:
        content = dict(zip(names, sections[1::2]))
        for name in HANDOFF_SECTIONS[:-1]:
            if not content[name].strip():
                refuse(f'section "{name}" is empty; write "None" if there is nothing')
        items = [line for line in content['Next action'].splitlines() if LIST_ITEM.match(line)]
        if len(items) != 1:
            refuse(f'Next action holds exactly one list item, found {len(items)}')
    if task_states is not None and 'Task' in fields:
        actual = task_states.get(fields['Task'])
        if actual is None:
            refuse(f'task {fields["Task"]} has no record in the tasks folder')
        elif actual != fields.get('State'):
            refuse(f'the handoff says {fields.get("State")} but task {fields["Task"]} is {actual}; '
                   'update the handoff')
    return found


# ------------------------------------------------------------ whole project

def load_json(path: Path, where: str) -> tuple[object, list[Finding]]:
    try:
        return json.loads(path.read_text(encoding='utf-8')), []
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, [Finding(FORMAT, where, f'cannot read JSON: {error}')]


def check_all(root: Path) -> list[Finding]:
    config = root / '.engineering-kit' / 'project.json'
    project, found = load_json(config, '.engineering-kit/project.json')
    if project is None:
        return found
    found += check_project(project, root, '.engineering-kit/project.json')
    paths = project.get('paths') if isinstance(project, dict) else None
    if not isinstance(paths, dict) or not all(relative_path(paths.get(k)) for k in ('tasks', 'handoffs')):
        return found
    states = {}
    for path in sorted((root / paths['tasks']).glob('*.json')):
        where = path.relative_to(root).as_posix()
        task, problems = load_json(path, where)
        found += problems
        if task is not None:
            found += check_task(task, project, where)
            if isinstance(task, dict) and text(task.get('id')):
                if task['id'] in states:
                    found.append(Finding(FORMAT, where, f'task ID {task["id"]} is used by another record'))
                elif path.stem != task['id']:
                    found.append(Finding(FORMAT, where, f'name the file {task["id"]}.json after its task'))
                states[task['id']] = task.get('state')
    for path in sorted((root / paths['handoffs']).glob('*.md')):
        where = path.relative_to(root).as_posix()
        source = path.read_text(encoding='utf-8')
        found += check_handoff(source, states, where)
        named = re.search(r'^Task: *(.+?) *$', source, re.M)
        if named and named.group(1) != path.stem:
            found.append(Finding('HANDOFF', where, f'name the file {named.group(1)}.md after its task'))
    return found


# ----------------------------------------------------------- secret scan
# Each pattern is valid both as a Python regex and as a POSIX ERE for git grep.
SECRET_PATTERNS = (
    ('private-key', '-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY( BLOCK)?-----'),
    ('provider-token', 'sk-(ant|proj|svcacct|admin)-[A-Za-z0-9_-]{16,}'),
    ('provider-token', 'sk-[A-Za-z0-9]{40,}'),
    ('git-host-token', 'gh[pousr]_[A-Za-z0-9]{20,}'),
    ('git-host-token', 'github_pat_[A-Za-z0-9_]{22,}'),
    ('git-host-token', 'glpat-[A-Za-z0-9_-]{20,}'),
    ('cloud-key', '(AKIA|ASIA)[0-9A-Z]{16}'),
    ('cloud-key', 'AIza[0-9A-Za-z_-]{35}'),
    ('chat-token', 'xox[abprs]-[A-Za-z0-9-]{10,}'),
    ('network-key', 'tskey-[a-z]+-[A-Za-z0-9-]{10,}'),
    ('payment-key', '[sr]k_live_[A-Za-z0-9]{16,}'),
    ('package-token', 'npm_[A-Za-z0-9]{36}'),
    ('model-hub-token', 'hf_[A-Za-z0-9]{34}'),
)
SECRET_COMPILED = tuple((label, re.compile(pattern)) for label, pattern in SECRET_PATTERNS)
ENV_FILE = re.compile(r'(^|/)(\.env(\..+)?|[^/]+\.env)$')
ENV_LINE = re.compile(r'^\s*(export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=\s*(.*?)\s*$')
PLACEHOLDER = re.compile(
    r'(?i)(change[-_]?me[\w-]*|replace[-_]?me[\w-]*|<[^>]*>|\$\{[^}]*\}|x+|example[\w-]*|your[-_][\w-]*)?')
SECRET_ALLOWLIST = Path('.engineering-kit/secret-allowlist.json')


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True).stdout


def scan_secrets(root: Path) -> list[Finding]:
    """Findings name the file, line and kind, never the value; the allowlist holds value digests."""
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode('utf-8', 'surrogateescape')).hexdigest()

    hits = []
    argv = ['grep', '--cached', '-I', '-n', '-z', '-E', '--no-color']
    for _, pattern in SECRET_PATTERNS:
        argv += ['-e', pattern]
    result = subprocess.run(['git', '-C', str(root), *argv], capture_output=True)
    if result.returncode not in (0, 1):  # 1 means no match
        raise RuntimeError('git grep failed: ' + result.stderr.decode(errors='replace')[-500:])
    for record in filter(None, result.stdout.split(b'\n')):
        path, number, content = record.split(b'\0', 2)
        line = content.decode('utf-8', 'surrogateescape')
        for label, pattern in SECRET_COMPILED:
            for match in pattern.finditer(line):
                hits.append((path.decode('utf-8', 'surrogateescape'), int(number), label, digest(match.group(0))))
    for raw in git(root, 'ls-files', '--cached', '-z').split(b'\0'):
        name = raw.decode('utf-8', 'surrogateescape')
        if not name or not ENV_FILE.search(name):
            continue
        for number, line in enumerate(git(root, 'show', ':' + name).decode('utf-8', 'surrogateescape')
                                      .splitlines(), 1):
            match = ENV_LINE.match(line)
            if not match:
                continue
            value = match.group(2)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1]
            if not PLACEHOLDER.fullmatch(value):
                hits.append((name, number, 'filled-env-value', digest(value)))
    accepted = set()
    allowlist = root / SECRET_ALLOWLIST
    if allowlist.exists():
        for entry in json.loads(allowlist.read_text(encoding='utf-8')).get('entries', []):
            if not text(entry.get('reason')):
                raise ValueError(f'allowlist entry for {entry.get("path")!r} needs a reason')
            accepted |= {(entry['path'], value) for value in entry.get('sha256', [])}
    return [Finding('SECRETS', f'{path}:{number}', f'{kind} (sha256 {value[:12]}); remove it, or for a '
                                                   'fake test value add a reviewed allowlist entry')
            for path, number, kind, value in hits if (path, value) not in accepted]


def compare_integrated(root: Path, candidate: str, revision: str) -> list[Finding]:
    """Refuse every file where REVISION differs from CANDIDATE, outside the process files: the
    `.engineering-kit/` folder (records, project configuration and kit files) and the task and
    handoff folders wherever the project keeps them."""
    project, found = load_json(root / '.engineering-kit' / 'project.json', '.engineering-kit/project.json')
    paths = project.get('paths', {}) if isinstance(project, dict) else {}
    excludes = [':(exclude).engineering-kit'] + [
        f':(exclude){paths[k]}' for k in ('tasks', 'handoffs') if relative_path(paths.get(k))]
    result = subprocess.run(['git', '-C', str(root), 'diff', '--name-only', '-z', candidate, revision, '--', '.',
                             *excludes], capture_output=True)
    if result.returncode:
        return found + [Finding(FORMAT, 'git', result.stderr.decode(errors='replace').strip()[-300:])]
    return found + [Finding('CANDIDATE', name, f'differs between {candidate} and {revision}')
                    for name in result.stdout.decode('utf-8', 'surrogateescape').split('\0') if name]


# -------------------------------------------------------------------- CLI

def report(found: list[Finding], as_json: bool, success: str) -> int:
    if as_json:
        print(json.dumps({'result': 'refuse' if found else 'pass',
                          'contract': CONTRACT_VERSION,
                          'findings': [asdict(f) for f in found]}, indent=2))
    else:
        for finding in found:
            print(finding)
        print(f'{len(found)} refused; each names its rule in CONTRACT.md.' if found else success)
    return 1 if found else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='kit.py', description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'check-task', 'check-handoff', 'scan-secrets', 'integrated'):
        command = commands.add_parser(name)
        command.add_argument('--root', type=Path, default=Path.cwd())
        command.add_argument('--json', action='store_true')
        if name in ('check-task', 'check-handoff'):
            command.add_argument('file', type=Path)
        if name == 'integrated':
            command.add_argument('candidate')
            command.add_argument('revision')
    changes = {'adopt': 'adopt the kit from SOURCE at VERSION', 'update': 'move to another release',
               'rollback': 'return to the previously installed release', 'remove': 'remove the kit'}
    for name, summary in changes.items():
        command = commands.add_parser(name, help=summary)
        command.add_argument('--root', type=Path, default=Path.cwd())
        if name == 'adopt':
            command.add_argument('source', nargs='?', help='default: the repository this tool was cloned from')
            command.add_argument('version', nargs='?', help='default: the release this tool was cloned at')
            command.add_argument('--with', dest='with_integrations', action='append', default=[], metavar='NAME',
                                 help='enable an integration in the new project.json and grant what it declares')
        if name == 'update':
            command.add_argument('version')
        if name == 'update':
            command.add_argument('--source', help='fetch from here instead of the recorded source')
        if name in ('update', 'rollback'):
            command.add_argument('--accept-contract', type=int, metavar='N')
        command.add_argument('--apply', action='store_true', help='write the previewed changes')
        command.add_argument('--plan', metavar='DIGEST', help='apply only if the plan is still this preview')
        command.add_argument('--resolve', action='append', default=[], metavar='PATH=kit|local')
        command.add_argument('--diff', action='store_true', help='show each change as a diff')
    commands.add_parser('status').add_argument('--root', type=Path, default=Path.cwd())
    command = commands.add_parser('recover', help='undo the writes of an interrupted apply')
    command.add_argument('--root', type=Path, default=Path.cwd())
    command.add_argument('--abandon', action='store_true', help='drop the journal and keep the files as they are')
    command = commands.add_parser('release', help='write RELEASE.json in the kit source folder')
    command.add_argument('version')
    command.add_argument('--root', type=Path, default=Path.cwd())
    command.add_argument('--check', action='store_true', help='refuse if RELEASE.json is not current')
    command = commands.add_parser('contribute', help='offer locally changed kit files back')
    command.add_argument('files', nargs='+')
    command.add_argument('--root', type=Path, default=Path.cwd())
    command.add_argument('--out', type=Path, required=True)
    for field in ('need', 'evidence', 'limits', 'rights', 'owner'):
        command.add_argument(f'--{field}', required=True)
    command = commands.add_parser('check-contribution')
    command.add_argument('file', type=Path)
    command.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.command not in ('check', 'check-task', 'check-handoff', 'scan-secrets', 'integrated'):
        sys.dont_write_bytecode = True  # leave no compiled files inside the project's kit folder
        import kit_update  # only distribution needs it, and it needs the git command line
        return kit_update.cli(args)
    root = args.root.resolve()
    if args.command == 'check':
        return report(check_all(root), args.json, 'Project, tasks and handoffs pass the contract.')
    if args.command == 'scan-secrets':
        return report(scan_secrets(root), args.json, 'No unreviewed secrets in the tracked files.')
    if args.command == 'integrated':
        return report(compare_integrated(root, args.candidate, args.revision), args.json,
                      f'{args.revision} equals {args.candidate} outside the process files. If it is '
                      'the revision that lands the candidate, such as its merge, record it in '
                      'candidate.integrated with this command as its evidence.')
    project, found = load_json(root / '.engineering-kit' / 'project.json', '.engineering-kit/project.json')
    project = project if isinstance(project, dict) else {}
    if args.command == 'check-task':
        task, problems = load_json(args.file, str(args.file))
        found += problems + (check_task(task, project, str(args.file)) if task is not None else [])
        return report(found, args.json, 'The task passes the contract.')
    states = {}
    tasks = (project.get('paths') or {}).get('tasks')
    if relative_path(tasks):
        for path in (root / tasks).glob('*.json'):
            task, _ = load_json(path, str(path))
            if isinstance(task, dict) and text(task.get('id')):
                states[task['id']] = task.get('state')
    found += check_handoff(args.file.read_text(encoding='utf-8'), states if project else None, str(args.file))
    return report(found, args.json, 'The handoff passes the contract.')


if __name__ == '__main__':
    sys.exit(main())
