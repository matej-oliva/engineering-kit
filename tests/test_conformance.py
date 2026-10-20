"""Run the portable conformance cases against the reference checker."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'tools'))
import kit  # noqa: E402

CASES = json.loads((KIT / 'conformance' / 'cases.json').read_text(encoding='utf-8'))
NOW = datetime(2026, 10, 20, 13, 0, tzinfo=timezone.utc)


def walk(document, path):
    *parents, last = [int(p) if p.isdigit() else p for p in path.split('.')]
    for part in parents:
        document = document[part]
    return document, last


def patched(document, case):
    document = copy.deepcopy(document)
    for path, value in case.get('set', {}).items():
        parent, key = walk(document, path)
        if isinstance(parent, list) and key == len(parent):
            parent.append(value)
        else:
            parent[key] = value
    for path in case.get('remove', []):
        parent, key = walk(document, path)
        del parent[key]
    return document


def load(relative):
    return json.loads((KIT / relative).read_text(encoding='utf-8'))


def rules(findings):
    return sorted({finding.rule for finding in findings})


class ConformanceCases(unittest.TestCase):
    def test_task_cases(self):
        project = load(CASES['project'])
        for case in CASES['tasks']:
            with self.subTest(case['name']):
                found = kit.check_task(patched(load(case['task']), case), project, case['name'])
                self.assertEqual(rules(found), sorted(case['expect']), '\n'.join(map(str, found)))

    def test_project_cases(self):
        root = KIT / CASES['project_root']
        for case in CASES['projects']:
            with self.subTest(case['name']):
                found = kit.check_project(patched(load(CASES['project']), case), root, case['name'])
                self.assertEqual(rules(found), sorted(case['expect']), '\n'.join(map(str, found)))

    def test_handoff_cases(self):
        states = {'T-7': load(f'{CASES["project_root"]}/.engineering-kit/tasks/T-7.json')['state']}
        for case in CASES['handoffs']:
            with self.subTest(case['name']):
                source = (KIT / case['file']).read_text(encoding='utf-8')
                for old, new in case.get('replace', []):
                    self.assertIn(old, source, 'the replacement must apply')
                    source = source.replace(old, new)
                found = kit.check_handoff(source, states, case['name'], now=NOW)
                self.assertEqual(rules(found), sorted(case['expect']), '\n'.join(map(str, found)))

    def test_every_checked_rule_has_a_planted_failure(self):
        """A rule labelled checked must be shown refusing something, or the label is a claim."""
        expected = {rule for group in ('tasks', 'projects', 'handoffs') for case in CASES[group]
                    for rule in case['expect']}
        checked = {line.split('|')[1].strip().strip('`') for line in
                   (KIT / 'CONTRACT.md').read_text(encoding='utf-8').splitlines()
                   if line.startswith('| `') and line.split('|')[3].strip() == 'checked'}
        self.assertEqual(checked - expected, set(), 'checked rules without a conformance case')


if __name__ == '__main__':
    unittest.main()
