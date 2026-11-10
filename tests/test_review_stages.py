"""A source review can unblock integration without granting final acceptance."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'tools'))
import kit  # noqa: E402


class ReviewStages(unittest.TestCase):
    def test_staged_candidate_requires_integrated_evidence_and_fresh_review(self):
        root = KIT / 'examples/walkthrough/project/.engineering-kit'
        project = json.loads((root / 'project.json').read_text(encoding='utf-8'))
        task = json.loads((root / 'tasks/T-7.json').read_text(encoding='utf-8'))
        task['profile'] = 'change'
        project['checks']['integration'] = {'description': 'Combined candidate works'}
        project['profiles']['change']['required_checks'].append('integration')
        task['checks'].append({'id': 'integration', 'revision': task['candidate']['revision'],
                               'result': 'unknown', 'evidence': 'Not run; integrator owns this check'})
        # A source-ready report lives outside reviews: it cannot approve acceptance.
        self.assertEqual(kit.check_task(task, project), [])
        premature = copy.deepcopy(task)
        premature['state'] = 'reviewed'
        rules = {f.rule for f in kit.check_task(premature, project)}
        self.assertEqual(rules, {'UNKNOWN', 'REVIEW'})

        worker_revision = task['candidate']['revision']
        task['candidate']['revision'] = 'combined-revision'
        self.assertIn('CANDIDATE', {f.rule for f in kit.check_task(task, project)})
        for check in task['checks']:
            check.update(revision='combined-revision', result='pass', evidence='Combined candidate run')
        task['state'] = 'reviewed'
        task['reviews'] = [{'reviewer': 'independent-reviewer', 'revision': worker_revision,
                            'verdict': 'approve', 'findings': []}]
        self.assertIn('CANDIDATE', {f.rule for f in kit.check_task(task, project)})
        task['reviews'][0]['revision'] = 'combined-revision'
        self.assertEqual(kit.check_task(task, project), [])
        for result in ('unknown', 'skipped', 'fail'):
            with self.subTest(result=result):
                failed = copy.deepcopy(task)
                failed['checks'][-1]['result'] = result
                self.assertTrue(kit.check_task(failed, project))

    def test_procedure_explains_the_stage_boundary_before_formal_review(self):
        review = (KIT / 'procedures/review.md').read_text(encoding='utf-8')
        readiness = review.index('## Before formal acceptance review')
        formal = review.index('## Formal acceptance review')
        self.assertLess(readiness, formal)
        before = review[readiness:formal]
        for phrase in ('not a kit approval', 'not ready for formal review',
                       'does not consume a correction round', 'new evidence',
                       'specific unresolved dispute'):
            self.assertIn(phrase, before)
        self.assertIn('source readiness -> integrated candidate -> required checks -> acceptance review', review)


if __name__ == '__main__':
    unittest.main()
