"""The release commit leaves repository-host files out of the tag and keeps them on the branch."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'tests'))
from native_release import QUIET_GIT, remove_tree  # noqa: E402  Git object files are read-only on Windows


class ReleaseCommit(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='kit-release-commit-'))
        self.addCleanup(remove_tree, self.temp)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(QUIET_GIT, HOME=str(self.temp), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                        GIT_AUTHOR_NAME='Kit Test', GIT_AUTHOR_EMAIL='kit@example.invalid',
                        GIT_COMMITTER_NAME='Kit Test', GIT_COMMITTER_EMAIL='kit@example.invalid')
        self.root = self.temp / 'kit'
        shutil.copytree(KIT, self.root, ignore=shutil.ignore_patterns('__pycache__', '.git'))
        workflow = self.root / '.github' / 'workflows' / 'native.yml'
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_bytes(b'name: Native\n')
        self.git('init', '-q', '-b', 'main')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'Candidate')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, env=self.env, capture_output=True, text=True,
                              check=True).stdout

    def make(self, version):
        return subprocess.run([sys.executable, str(self.root / 'tests' / 'release_commit.py'), version],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def test_the_tag_holds_no_host_files_and_the_branch_keeps_them(self):
        done = self.make('2.0.0')
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        tagged = self.git('ls-tree', '-r', '--name-only', 'v2.0.0').split()
        self.assertIn('RELEASE.json', tagged)
        self.assertIn('integrations/github/workflow.yml', tagged)
        self.assertFalse([path for path in tagged if path.startswith('.github/')], tagged)
        self.assertEqual(self.git('cat-file', '-t', 'v2.0.0').strip(), 'tag')
        self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD').strip(), 'main')
        self.assertTrue((self.root / '.github' / 'workflows' / 'native.yml').is_file())
        self.assertIn('git push origin v2.0.0', done.stdout)

    def test_a_failed_release_leaves_no_branch_and_returns_to_the_start(self):
        (self.root / 'procedures' / 'link.md').symlink_to(self.root / 'README.md')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'A link the release refuses')
        done = self.make('2.0.0')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('link or submodule', done.stderr)
        self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD').strip(), 'main')
        self.assertEqual(self.git('branch', '--list', 'release/*').strip(), '')
        self.assertEqual(self.git('tag', '--list').strip(), '')

    def test_a_refused_commit_leaves_the_checkout_exactly_as_it_was(self):
        hook = self.root / '.git' / 'hooks' / 'pre-commit'
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_bytes(b'#!/bin/sh\necho "hook says no"\nexit 1\n')
        hook.chmod(0o755)
        done = self.make('2.0.0')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('hook says no', done.stderr, 'the reason a commit failed is shown')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        self.assertTrue((self.root / '.github' / 'workflows' / 'native.yml').is_file())
        self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD').strip(), 'main')
        self.assertEqual(self.git('branch', '--list', 'release/*').strip(), '')

    def test_a_failed_manifest_check_leaves_no_new_file(self):
        tool = self.root / 'tools' / 'kit_update.py'
        text = tool.read_text(encoding='utf-8')
        self.assertEqual(text.count('code = 0 if current == manifest else 1'), 1)
        tool.write_text(text.replace('code = 0 if current == manifest else 1', 'code = 1'), encoding='utf-8')
        self.git('commit', '-q', '-am', 'A manifest check that always fails')
        done = self.make('2.0.0')
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD').strip(), 'main')

    def test_a_detached_head_or_an_existing_tag_is_refused(self):
        self.git('tag', '-a', 'v2.0.0', '-m', 'already published')
        done = self.make('2.0.0')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('tag v2.0.0 already exists', done.stderr)
        self.git('switch', '-q', '--detach', 'HEAD')
        done = self.make('2.0.1')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('detached', done.stderr)

    def test_a_dirty_checkout_is_refused_without_a_tag(self):
        (self.root / 'procedures' / 'review.md').write_bytes(b'changed\n')
        done = self.make('2.0.0')
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('uncommitted changes', done.stderr)
        self.assertEqual(self.git('tag', '--list').strip(), '')


if __name__ == '__main__':
    unittest.main()
