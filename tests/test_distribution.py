"""Versioned distribution on disposable consumers: adopt, update, conflicts, recovery, removal,
integration swaps and a contribution back. Releases come from a local Git repository, so no
hosting service, network or credential is involved."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'tools'))
import kit  # noqa: E402
import kit_update as ku  # noqa: E402

REVIEW = '.engineering-kit/kit/procedures/review.md'
CONTRACT = '.engineering-kit/kit/CONTRACT.md'
REVIEW_STEP = 'Use when a candidate is ready. The reviewer is not the author.'


def sh(*args, cwd):
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, check=True, capture_output=True)


def edit(path: Path, old: str, new: str):
    text = path.read_text(encoding='utf-8')
    assert text.count(old) == 1, (path, old)
    path.write_text(text.replace(old, new), encoding='utf-8')


class Distribution(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='kit-distribution-'))
        self.addCleanup(shutil.rmtree, self.temp)
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(HOME=str(self.temp), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                   GIT_AUTHOR_NAME='Kit Test', GIT_AUTHOR_EMAIL='kit@example.invalid',
                   GIT_COMMITTER_NAME='Kit Test', GIT_COMMITTER_EMAIL='kit@example.invalid')
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.source = self.temp / 'kit-source'
        shutil.copytree(KIT, self.source, ignore=shutil.ignore_patterns('__pycache__', '.git'))
        sh('init', '-q', '-b', 'main', cwd=self.source)
        self.release('0.1.0')

    # ---------------------------------------------------------- helpers

    def release(self, version, change=None):
        if change:
            change(self.source)
        sh('add', '-A', cwd=self.source)
        manifest = ku.build_release(self.source, version)
        (self.source / 'RELEASE.json').write_text(json.dumps(manifest, indent=2) + '\n')
        sh('add', '-A', cwd=self.source)
        sh('commit', '-q', '--allow-empty', '-m', f'Release {version}', cwd=self.source)
        sh('tag', f'v{version}', cwd=self.source)

    def second_release(self):
        def change(root):
            edit(root / 'procedures' / 'review.md', REVIEW_STEP,
                 'Use when a candidate is ready. The reviewer is never the author.')
            edit(root / 'templates' / 'entry-block.md', 'Read it before you plan',
                 'Read it before you start, plan')
        self.release('0.2.0', change)

    def consumer(self, name='app', files=None):
        root = self.temp / name
        root.mkdir()
        for path, content in (files or {}).items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(content)
        sh('init', '-q', cwd=root)
        return root

    def run_change(self, root, version, **options):
        lock = ku.load_lock(root)
        source = options.pop('source', str(self.source))
        status, lines = ku.change(root, source, version, adopting=lock is None and version is not None, **options)
        return status, '\n'.join(lines)

    def adopt(self, root, version='0.1.0', **options):
        status, report = self.run_change(root, version, apply_now=True, **options)
        self.assertEqual(status, 0, report)
        return report

    def snapshot(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob('*'))
                if p.is_file() and '.git' not in p.relative_to(root).parts}

    def set_integrations(self, root, integrations):
        path = root / ku.PROJECT
        project = json.loads(path.read_text())
        project['integrations'] = integrations
        path.write_text(json.dumps(project, indent=2))

    # ------------------------------------------------------------ tests

    def test_new_project_preview_writes_nothing_and_apply_installs_the_core(self):
        root = self.consumer()
        status, report = self.run_change(root, '0.1.0')
        self.assertEqual(status, 0, report)
        self.assertIn('Preview only', report)
        self.assertEqual(self.snapshot(root), {})
        self.adopt(root)
        self.assertTrue((root / CONTRACT).is_file())
        self.assertIn(ku.BEGIN, (root / 'AGENTS.md').read_text())
        lock = ku.load_lock(root)
        self.assertEqual((lock['version'], lock['integrations']), ('0.1.0', ['agents-md']))
        self.assertNotIn('.engineering-kit/kit/tests/test_distribution.py', lock['files'])
        self.assertEqual(kit.check_all(root), [])
        self.assertIn('every kit-managed file matches', '\n'.join(ku.status(root)[1]))

    def test_existing_instructions_survive_adoption_byte_for_byte(self):
        local = '# Shop\n\nNever deploy on Fridays.\n'
        root = self.consumer(files={'AGENTS.md': local})
        self.adopt(root)
        text = (root / 'AGENTS.md').read_text()
        self.assertTrue(text.startswith(local))
        before, block, after = ku.split_block(text)
        self.assertEqual(before, local + '\n')
        self.assertIn('stricter one applies', block)

    def test_repeated_apply_changes_nothing(self):
        root = self.consumer()
        self.adopt(root)
        first = self.snapshot(root)
        status, report = self.run_change(root, '0.1.0', apply_now=True)
        self.assertEqual(status, 0, report)
        self.assertIn('nothing written', report)
        self.assertEqual(self.snapshot(root), first)

    def test_update_merges_local_policy_and_never_touches_project_files(self):
        root = self.consumer(files={'AGENTS.md': '# Shop\n\nNever deploy on Fridays.\n'})
        self.adopt(root)
        with open(root / REVIEW, 'a') as handle:
            handle.write('\nLocal: payments changes also need the finance owner.\n')
        project = (root / ku.PROJECT).read_text().replace('replace with the project', 'Shop')
        (root / ku.PROJECT).write_text(project)
        self.second_release()
        status, report = self.run_change(root, '0.2.0')
        self.assertEqual(status, 0, report)
        self.assertIn('merge', report)
        self.adopt(root, '0.2.0')
        review = (root / REVIEW).read_text()
        self.assertIn('never the author', review)
        self.assertIn('finance owner', review)
        self.assertEqual((root / ku.PROJECT).read_text(), project)
        agents = (root / 'AGENTS.md').read_text()
        self.assertTrue(agents.startswith('# Shop\n\nNever deploy on Fridays.\n'))
        self.assertIn('before you start, plan', agents)
        self.assertEqual(ku.load_lock(root)['version'], '0.2.0')
        self.assertIn('modified locally', '\n'.join(ku.status(root)[1]))

    def test_overlapping_changes_stop_without_writing_until_resolved(self):
        root = self.consumer()
        self.adopt(root)
        edit(root / REVIEW, REVIEW_STEP, 'Use when a candidate is ready. Two reviewers, never the author.')
        self.second_release()
        before = self.snapshot(root)
        status, report = self.run_change(root, '0.2.0', apply_now=True)
        self.assertEqual(status, 1)
        self.assertIn('conflict', report)
        self.assertIn('Nothing was written', report)
        self.assertEqual(self.snapshot(root), before)
        status, report = self.run_change(root, '0.2.0', apply_now=True, resolutions={REVIEW: 'local'})
        self.assertEqual(status, 0, report)
        self.assertIn('Two reviewers', (root / REVIEW).read_text())
        self.assertEqual(ku.load_lock(root)['version'], '0.2.0')

    def test_conflict_resolved_in_favour_of_the_kit(self):
        root = self.consumer()
        self.adopt(root)
        edit(root / REVIEW, REVIEW_STEP, 'Use when a candidate is ready. Two reviewers, never the author.')
        self.second_release()
        self.adopt(root, '0.2.0', resolutions={REVIEW: 'kit'})
        self.assertIn('never the author.', (root / REVIEW).read_text())
        self.assertNotIn('Two reviewers', (root / REVIEW).read_text())

    def test_interrupted_apply_is_recovered_to_the_exact_earlier_state(self):
        root = self.consumer(files={'AGENTS.md': '# Shop\n'})
        self.adopt(root)
        self.second_release()
        before = self.snapshot(root)
        with self.assertRaises(ku.KitError):
            self.run_change(root, '0.2.0', apply_now=True, fail_after=1)
        self.assertNotEqual(self.snapshot(root), before)
        self.assertEqual(ku.status(root)[0], 1)
        with self.assertRaisesRegex(ku.KitError, 'recover'):
            self.run_change(root, '0.2.0', apply_now=True)
        self.assertGreater(ku.recover(root), 0)
        self.assertEqual(self.snapshot(root), before)
        self.adopt(root, '0.2.0')
        self.assertEqual(ku.load_lock(root)['version'], '0.2.0')

    def test_rollback_returns_to_the_earlier_release_and_keeps_local_changes(self):
        root = self.consumer()
        self.adopt(root)
        with open(root / REVIEW, 'a') as handle:
            handle.write('\nLocal: payments changes also need the finance owner.\n')
        self.second_release()
        self.adopt(root, '0.2.0')
        self.assertEqual(ku.previous_version(root), '0.1.0')
        self.adopt(root, ku.previous_version(root))
        review = (root / REVIEW).read_text()
        self.assertIn('is not the author', review)
        self.assertIn('finance owner', review)
        self.assertEqual(ku.load_lock(root)['version'], '0.1.0')

    def test_removal_keeps_project_records_and_local_changes(self):
        local = '# Shop\n\nNever deploy on Fridays.\n'
        root = self.consumer(files={'AGENTS.md': local})
        self.adopt(root)
        task = root / '.engineering-kit' / 'tasks' / 'T-1.json'
        task.parent.mkdir(parents=True)
        task.write_text('{}')
        with open(root / REVIEW, 'a') as handle:
            handle.write('\nLocal note.\n')
        status, report = self.run_change(root, None)
        self.assertEqual(status, 1, report)  # the changed procedure needs a decision
        self.adopt(root, None, resolutions={REVIEW: 'local'})
        self.assertEqual((root / 'AGENTS.md').read_text(), local)
        self.assertFalse((root / CONTRACT).exists())
        self.assertTrue((root / REVIEW).exists())
        self.assertTrue((root / ku.PROJECT).exists())
        self.assertTrue(task.exists())
        self.assertIsNone(ku.load_lock(root))

    def test_application_code_and_unrelated_files_stay_byte_identical(self):
        unrelated = {'src/app.py': 'print("shop")\n', '.github/workflows/ci.yml': 'name: ci\n',
                     'notes.txt': 'uncommitted thoughts\n'}
        root = self.consumer(files=unrelated)
        github = {'agents-md': {'grant': ['writes-instructions']},
                  'github': {'grant': ['review-template', 'ci-workflow']}}

        def unchanged():
            for path, content in unrelated.items():
                self.assertEqual((root / path).read_text(), content, path)
        self.adopt(root)
        self.set_integrations(root, github)
        self.adopt(root)
        unchanged()
        self.second_release()
        self.adopt(root, '0.2.0')
        unchanged()
        self.adopt(root, ku.previous_version(root))
        unchanged()
        self.adopt(root, None)
        unchanged()
        self.assertFalse((root / '.github' / 'workflows' / 'engineering-kit.yml').exists())

    def test_an_unmanaged_file_in_the_way_stops_the_change(self):
        root = self.consumer(files={'.github/pull_request_template.md': 'Our own template\n'})
        self.adopt(root)
        self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']},
                                     'github': {'grant': ['review-template', 'ci-workflow']}})
        status, report = self.run_change(root, '0.1.0', apply_now=True)
        self.assertEqual(status, 1)
        self.assertIn('unmanaged file is in the way', report)
        self.assertEqual((root / '.github' / 'pull_request_template.md').read_text(), 'Our own template\n')
        self.adopt(root, '0.1.0', resolutions={'.github/pull_request_template.md': 'local'})
        self.assertEqual((root / '.github' / 'pull_request_template.md').read_text(), 'Our own template\n')
        self.assertTrue((root / '.github' / 'workflows' / 'engineering-kit.yml').is_file())
        self.assertIn("kept as the project's own: .github/pull_request_template.md", '\n'.join(ku.status(root)[1]))
        self.release('0.2.0', lambda source: edit(source / 'integrations' / 'github' / 'pull_request_template.md',
                                                  '## Review', '## Review and evidence'))
        self.adopt(root, '0.2.0')  # the kit's template changed, and the project's own still wins
        self.adopt(root, None)
        self.assertEqual((root / '.github' / 'pull_request_template.md').read_text(), 'Our own template\n')

    def test_integrations_need_every_permission_granted(self):
        root = self.consumer()
        self.adopt(root)
        self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']},
                                     'github': {'grant': ['review-template']}})
        status, report = self.run_change(root, '0.1.0', apply_now=True)
        self.assertEqual(status, 1)
        self.assertIn('needs ci-workflow granted', report)
        self.assertFalse((root / '.github').exists())
        self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']},
                                     'github': {'grant': ['review-template', 'ci-workflow']}})
        self.adopt(root, '0.1.0')
        self.assertTrue((root / '.github' / 'workflows' / 'engineering-kit.yml').is_file())

        def widen(source):
            manifest = source / 'integrations' / 'github' / 'integration.json'
            data = json.loads(manifest.read_text())
            data['permissions'].append('deploy')
            manifest.write_text(json.dumps(data, indent=2))
        self.release('0.2.0', widen)
        status, report = self.run_change(root, '0.2.0', apply_now=True)
        self.assertEqual(status, 1)
        self.assertIn('needs deploy granted', report)
        self.assertEqual(ku.load_lock(root)['version'], '0.1.0')

    def test_swapping_the_git_host_integration_leaves_the_core_unchanged(self):
        github, gitlab = self.consumer('on-github'), self.consumer('on-gitlab')
        for root, name in ((github, 'github'), (gitlab, 'gitlab')):
            self.adopt(root)
            self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']},
                                         name: {'grant': ['review-template', 'ci-workflow']}})
            self.adopt(root)

        def core(root):
            return {k: v for k, v in self.snapshot(root).items() if k.startswith(ku.MANAGED_ROOT)}
        self.assertEqual(core(github), core(gitlab))
        before = self.snapshot(github)
        self.set_integrations(github, {'agents-md': {'grant': ['writes-instructions']},
                                       'gitlab': {'grant': ['review-template', 'ci-workflow']}})
        self.adopt(github)
        after = self.snapshot(github)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        self.assertEqual(changed, {'.github/pull_request_template.md', '.github/workflows/engineering-kit.yml',
                                   '.gitlab/merge_request_templates/engineering-kit.md',
                                   '.gitlab/engineering-kit-ci.yml', ku.PROJECT, ku.LOCK})
        self.assertEqual(core(github), core(gitlab))

    def test_unsafe_targets_and_links_are_refused(self):
        root = self.consumer()
        self.adopt(root)
        for target in ('../outside.txt', '/etc/kit.txt', '.git/hooks/pre-commit', '.engineering-kit/project.json'):
            with self.subTest(target):
                def escape(source, target=target):
                    manifest = source / 'integrations' / 'github' / 'integration.json'
                    data = json.loads(manifest.read_text())
                    data['files'][0]['target'] = target
                    manifest.write_text(json.dumps(data, indent=2))
                version = f'0.{len(list(self.source.glob(".git/refs/tags/*"))) + 1}.0'
                self.release(version, escape)
                self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']},
                                             'github': {'grant': ['review-template', 'ci-workflow']}})
                before = self.snapshot(root)
                with self.assertRaisesRegex(ku.KitError, 'outside the area|unsafe'):
                    self.run_change(root, version, apply_now=True)
                self.assertEqual(self.snapshot(root), before)
                self.assertFalse((self.temp / 'outside.txt').exists())

    def test_a_linked_folder_in_the_consumer_is_refused(self):
        root = self.consumer()
        outside = self.temp / 'elsewhere'
        outside.mkdir()
        (root / '.engineering-kit').mkdir()
        (root / '.engineering-kit' / 'kit').symlink_to(outside)
        with self.assertRaisesRegex(ku.KitError, 'symbolic link'):
            self.run_change(root, '0.1.0', apply_now=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_a_release_containing_a_link_is_refused(self):
        (self.source / 'procedures' / 'link.md').symlink_to('/etc/hostname')
        self.release('0.2.0')
        root = self.consumer()
        with self.assertRaisesRegex(ku.KitError, 'link or submodule'):
            self.run_change(root, '0.2.0')

    def test_a_moved_release_tag_is_refused(self):
        root = self.consumer()
        self.adopt(root)
        edit(self.source / 'CONTRACT.md', 'Contract version: 1', 'Contract version: 1 (quietly changed)')
        sh('tag', '-d', 'v0.1.0', cwd=self.source)
        self.release('0.1.0')
        self.second_release()
        with self.assertRaisesRegex(ku.KitError, 'not what was installed'):
            self.run_change(root, '0.2.0')

    def test_apply_is_bound_to_the_previewed_plan(self):
        root = self.consumer()
        status, report = self.run_change(root, '0.1.0')
        digest = report.rsplit('plan ', 1)[1].split()[0]
        (root / 'AGENTS.md').write_text('# Changed after the preview\n')
        with self.assertRaisesRegex(ku.KitError, 'preview again'):
            self.run_change(root, '0.1.0', apply_now=True, expected_plan=digest)
        self.assertIsNone(ku.load_lock(root))

    def test_a_contract_change_needs_acknowledgement(self):
        root = self.consumer()
        self.adopt(root)

        def bump(source):
            edit(source / 'tools' / 'kit.py', 'CONTRACT_VERSION = 1', 'CONTRACT_VERSION = 2')
            for manifest in (source / 'integrations').glob('*/integration.json'):
                data = json.loads(manifest.read_text())
                data['contract'] = [1, 2]
                manifest.write_text(json.dumps(data, indent=2))
        with mock.patch.object(kit, 'CONTRACT_VERSION', 2):
            self.release('1.0.0', bump)
        status, report = self.run_change(root, '1.0.0', apply_now=True)
        self.assertEqual(status, 1)
        self.assertIn('--accept-contract 2', report)
        self.adopt(root, '1.0.0', accept_contract=2)
        self.assertEqual(ku.load_lock(root)['contract'], 2)

    def test_a_contribution_returns_upstream_and_reaches_another_project(self):
        donor, receiver = self.consumer('donor'), self.consumer('receiver')
        self.adopt(donor)
        self.adopt(receiver)
        lesson = '\nRecord which requirement revision each review judged.\n'
        with open(donor / REVIEW, 'a') as handle:
            handle.write(lesson)
        sh('add', '-A', cwd=donor)
        sh('commit', '-q', '-m', 'Improve the review procedure', cwd=donor)
        details = {'need': 'Reviews of an older requirement looked current', 'evidence': 'Task T-4 in donor',
                   'limits': 'Untested outside donor', 'rights': 'owner-authored', 'owner': 'kit maintainer'}
        out = self.temp / 'outbox'
        ku.contribute(donor, [REVIEW], out, details)
        record = json.loads((out / 'contribution.json').read_text())
        self.assertEqual(ku.check_contribution(record), [])
        self.assertEqual(len(record['source_revision']), 40)
        sh('apply', str(out / 'change.patch'), cwd=self.source)
        self.release('0.2.0')
        self.adopt(receiver, '0.2.0')
        self.assertIn(lesson.strip(), (receiver / REVIEW).read_text())
        for field, value in (('rights', 'unknown'), ('evidence', ''), ('status', 'done')):
            with self.subTest(field):
                self.assertEqual({f.rule for f in ku.check_contribution({**record, field: value})}, {'LESSON'})

    # ---------------------------- findings of the fresh review, 2026-10-20

    def grant_github(self, root):
        self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']},
                                     'github': {'grant': ['review-template', 'ci-workflow']}})

    def test_review_a_source_that_looks_like_an_option_is_refused(self):
        root = self.consumer()
        self.adopt(root)
        marker = self.temp / 'PWNED'
        lock = ku.load_lock(root)
        lock['source'] = f'--upload-pack=touch {marker};'
        (root / ku.LOCK).write_text(json.dumps(lock))
        with self.assertRaisesRegex(ku.KitError, 'source'):
            self.run_change(root, '0.1.0')
        self.assertFalse(marker.exists())

    def test_review_a_planted_journal_cannot_reach_outside_the_kit_area(self):
        root = self.consumer()
        self.adopt(root)
        outside = self.temp / 'outside.txt'
        outside.write_text('keep me\n')
        journal = root / ku.JOURNAL
        journal.mkdir()
        (journal / '0.orig').write_text('#!/bin/sh\necho hook\n')
        (journal / 'journal.json').write_text(json.dumps({'kit': 'journal/1', 'steps': [
            {'path': '../outside.txt', 'backup': None, 'before': None, 'after': None},
            {'path': '.git/hooks/pre-commit', 'backup': '0.orig', 'before': None, 'after': None}]}))
        with self.assertRaisesRegex(ku.KitError, 'journal'):
            ku.recover(root)
        self.assertEqual(outside.read_text(), 'keep me\n')
        self.assertFalse((root / '.git' / 'hooks' / 'pre-commit').exists())

    def test_review_recover_refuses_to_write_through_a_link(self):
        root = self.consumer()
        self.adopt(root)
        outside = self.temp / 'elsewhere'
        outside.mkdir()
        shutil.rmtree(root / '.engineering-kit' / 'kit' / 'procedures')
        (root / '.engineering-kit' / 'kit' / 'procedures').symlink_to(outside)
        journal = root / ku.JOURNAL
        journal.mkdir()
        (journal / '0.orig').write_text('planted\n')
        (journal / 'journal.json').write_text(json.dumps({'kit': 'journal/1', 'steps': [
            {'path': REVIEW, 'backup': '0.orig', 'before': None, 'after': None}]}))
        with self.assertRaisesRegex(ku.KitError, 'symbolic link'):
            ku.recover(root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_review_recover_never_reverts_work_done_after_the_interruption(self):
        root = self.consumer()
        self.adopt(root)
        self.grant_github(root)
        self.second_release()  # its plan updates review.md and adds the template
        with self.assertRaises(ku.KitError):
            self.run_change(root, '0.2.0', apply_now=True, fail_after=0)
        with open(root / REVIEW, 'a') as handle:
            handle.write('\nWritten after the interruption.\n')
        template = root / '.github' / 'pull_request_template.md'
        template.parent.mkdir(parents=True)
        template.write_text('Our own template\n')
        with self.assertRaisesRegex(ku.KitError, 'changed since'):
            ku.recover(root)
        self.assertIn('after the interruption', (root / REVIEW).read_text())
        self.assertEqual(template.read_text(), 'Our own template\n')
        ku.recover(root, abandon=True)
        self.assertFalse((root / ku.JOURNAL).exists())
        self.assertEqual(template.read_text(), 'Our own template\n')

    def test_review_an_identical_project_file_is_kept_on_removal(self):
        kit_template = (self.source / 'integrations' / 'github' / 'pull_request_template.md').read_text()
        root = self.consumer(files={'.github/pull_request_template.md': kit_template})
        self.adopt(root)
        self.grant_github(root)
        status, report = self.run_change(root, '0.1.0')
        self.assertIn('adopt', report)
        self.adopt(root)
        self.adopt(root, None)
        self.assertEqual((root / '.github' / 'pull_request_template.md').read_text(), kit_template)
        self.assertFalse((root / '.github' / 'workflows' / 'engineering-kit.yml').exists())

    def test_review_a_block_kept_as_the_projects_own_stays_untouched(self):
        root = self.consumer(files={'AGENTS.md': '# Shop\n'})
        self.adopt(root)
        (root / 'AGENTS.md').write_text('# Shop\n\nOur own pointer to the contract.\n')
        self.second_release()
        status, report = self.run_change(root, '0.2.0', apply_now=True)
        self.assertEqual(status, 1, report)
        self.adopt(root, '0.2.0', resolutions={'AGENTS.md': 'local'})
        self.release('0.3.0', lambda source: edit(source / 'templates' / 'entry-block.md',
                                                  'read its handoff first', 'read its handoff before anything'))
        self.adopt(root, '0.3.0')
        self.assertEqual((root / 'AGENTS.md').read_text(), '# Shop\n\nOur own pointer to the contract.\n')
        self.assertIn("kept as the project's own: entry block in AGENTS.md", '\n'.join(ku.status(root)[1]))

    def test_review_rollback_refuses_a_moved_tag(self):
        root = self.consumer()
        self.adopt(root)
        self.second_release()
        self.adopt(root, '0.2.0')
        sh('checkout', '-q', 'v0.1.0', cwd=self.source)
        edit(self.source / 'CONTRACT.md', 'Contract version: 1', 'Contract version: 1 (quietly changed)')
        sh('tag', '-d', 'v0.1.0', cwd=self.source)
        self.release('0.1.0')
        with self.assertRaisesRegex(ku.KitError, 'not what was installed'):
            self.run_change(root, ku.previous_version(root), apply_now=True)

    def test_review_each_integration_file_needs_a_declared_and_granted_permission(self):
        root = self.consumer()
        self.adopt(root)
        for label, entry in (('no permission', {}), ('undeclared permission', {'permission': 'ci-workflow'})):
            with self.subTest(label):
                def sneak(source, entry=entry):
                    manifest = source / 'integrations' / 'agents-md' / 'integration.json'
                    data = json.loads(manifest.read_text())
                    (source / 'integrations' / 'agents-md' / 'agents.yml').write_text('on: push\n')
                    data['files'] = [{'source': 'agents.yml', 'target': '.github/workflows/agents.yml', **entry}]
                    manifest.write_text(json.dumps(data, indent=2))
                version = f'0.{len(list(self.source.glob(".git/refs/tags/*"))) + 1}.0'
                self.release(version, sneak)
                with self.assertRaisesRegex(ku.KitError, 'permission'):
                    self.run_change(root, version, apply_now=True)
                self.assertFalse((root / '.github').exists())

    def test_review_something_other_than_a_file_in_the_way_stops_before_writing(self):
        root = self.consumer()
        self.adopt(root)
        (root / '.github' / 'workflows' / 'engineering-kit.yml').mkdir(parents=True)
        self.grant_github(root)
        status, report = self.run_change(root, '0.1.0', apply_now=True)
        self.assertEqual(status, 1, report)
        self.assertIn('not a file', report)
        self.assertFalse((root / '.github' / 'pull_request_template.md').exists())
        self.assertFalse((root / ku.JOURNAL).exists())

    def test_review_a_newer_tool_still_removes_what_an_older_release_installed(self):
        root = self.consumer()
        self.adopt(root)
        self.grant_github(root)
        self.adopt(root)
        with mock.patch.object(kit, 'CONTRACT_VERSION', 2):
            self.adopt(root, None)
        self.assertFalse((root / '.github' / 'workflows' / 'engineering-kit.yml').exists())
        self.assertFalse((root / 'AGENTS.md').exists())

    def test_review_rollback_accepts_a_contract_acknowledgement(self):
        root = self.consumer()
        self.adopt(root)
        result = subprocess.run([sys.executable, str(root / '.engineering-kit' / 'kit' / 'tools' / 'kit.py'),
                                 'rollback', '--accept-contract', '1', '--root', str(root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('no earlier installed release', result.stdout)

    def test_review_small_cases(self):
        root = self.consumer(files={'AGENTS.md': ''})
        self.adopt(root)
        for target in ('.', '.GIT/hooks/pre-commit', 'sub/.git/config'):
            with self.subTest(target):
                def odd(source, target=target):
                    manifest = source / 'integrations' / 'github' / 'integration.json'
                    data = json.loads(manifest.read_text())
                    data['files'][0]['target'] = target
                    manifest.write_text(json.dumps(data, indent=2))
                version = f'0.{len(list(self.source.glob(".git/refs/tags/*"))) + 1}.0'
                self.release(version, odd)
                self.grant_github(root)
                with self.assertRaisesRegex(ku.KitError, 'outside the area|unsafe'):
                    self.run_change(root, version)
        self.set_integrations(root, {'agents-md': {'grant': ['writes-instructions']}})
        subprocess.run([sys.executable, str(root / '.engineering-kit' / 'kit' / 'tools' / 'kit.py'),
                        'status', '--root', str(root)], check=True, capture_output=True)
        self.assertEqual(list(root.rglob('__pycache__')), [])
        self.adopt(root, None)
        self.assertEqual((root / 'AGENTS.md').read_text(), '')

    def test_review_a_deleted_instruction_file_is_a_conflict_not_a_silent_re_add(self):
        root = self.consumer()
        self.adopt(root)
        (root / 'AGENTS.md').unlink()
        self.second_release()
        status, report = self.run_change(root, '0.2.0', apply_now=True)
        self.assertEqual(status, 1, report)
        self.assertIn('deleted locally', report)
        self.assertFalse((root / 'AGENTS.md').exists())

    def test_command_line_preview_and_apply(self):
        root = self.consumer()
        tool = [sys.executable, str(self.source / 'tools' / 'kit.py')]
        preview = subprocess.run([*tool, 'adopt', str(self.source), '0.1.0', '--root', str(root)],
                                 capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        self.assertIn('Preview only', preview.stdout)
        applied = subprocess.run([*tool, 'adopt', str(self.source), '0.1.0', '--root', str(root), '--apply'],
                                 capture_output=True, text=True)
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        installed = [sys.executable, str(root / '.engineering-kit' / 'kit' / 'tools' / 'kit.py')]
        result = subprocess.run([*installed, 'status', '--root', str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Kit 0.1.0', result.stdout)
        refused = subprocess.run([*installed, 'update', '9.9.9', '--root', str(root)], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)


if __name__ == '__main__':
    unittest.main()
