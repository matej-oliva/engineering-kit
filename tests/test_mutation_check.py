"""Exercise the release runner on a small independent kit snapshot."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mutation_check


class MutationCheck(unittest.TestCase):
    def test_survival_requires_the_whole_suite_to_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            (root / 'tests').mkdir()
            (root / 'tools/kit.py').write_text('value = 1\n', encoding='utf-8')
            (root / 'tests/test_tool.py').write_text('', encoding='utf-8')
            (root / 'tests/test_other.py').write_text(
                'import unittest\nfrom tools.kit import value\n'
                'class Other(unittest.TestCase):\n'
                '    def test_value(self):\n        self.assertEqual(value, 1)\n',
                encoding='utf-8')
            mutants = [('caught elsewhere', 'kit.py', '1', '2'), ('equivalent', 'kit.py', '1', '1 + 0')]
            with patch.object(mutation_check, 'KIT', root), patch.object(mutation_check, 'MUTANTS', mutants):
                self.assertEqual(mutation_check.main(['caught elsewhere']), 0)
                self.assertEqual(mutation_check.main(['equivalent']), 1)

    def kit(self, root: Path):
        (root / 'tools').mkdir()
        (root / 'tests').mkdir()
        (root / 'tools/kit.py').write_text('value = 1\n', encoding='utf-8')
        (root / 'tests/test_tool.py').write_text(
            'import unittest\n'
            'class Tool(unittest.TestCase):\n'
            '    def test_passes(self):\n        pass\n', encoding='utf-8')
        (root / 'tests/test_other.py').write_text(
            'import unittest\nfrom tools.kit import value\n'
            'class Other(unittest.TestCase):\n'
            '    def test_value(self):\n        self.assertEqual(value, 1)\n', encoding='utf-8')

    def test_a_stale_or_missing_cache_entry_falls_back_to_the_full_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.kit(root)
            mutants = [('caught elsewhere', 'kit.py', '1', '2'), ('equivalent', 'kit.py', '1', '1 + 0'),
                       ('not cached', 'kit.py', 'value = 1', 'value = 3')]
            (root / mutation_check.CACHE).write_text(json.dumps({
                'caught elsewhere': 'test_gone.Gone.test_renamed',  # a test that no longer exists
                'equivalent': 'test_tool.Tool.test_passes',  # passes, so it proves nothing
                'retired mutant': 'test_tool.Tool.test_passes'}), encoding='utf-8')
            with patch.object(mutation_check, 'KIT', root), patch.object(mutation_check, 'MUTANTS', mutants):
                self.assertEqual(mutation_check.main(['caught elsewhere', 'not cached']), 0)
                self.assertEqual(mutation_check.main(['equivalent'], workers=2), 1)
                self.assertEqual(mutation_check.main([], workers=3, update_cache=True), 1)
            cache = json.loads((root / mutation_check.CACHE).read_text(encoding='utf-8'))
            # The cache learns the real catching test and forgets mutants no longer listed;
            # the survivor keeps its old entry, which never decides a verdict.
            self.assertEqual(cache, {'caught elsewhere': 'test_other.Other.test_value',
                                     'not cached': 'test_other.Other.test_value',
                                     'equivalent': 'test_tool.Tool.test_passes'})

    def test_the_cached_test_runs_first_and_alone_decides_a_catch_it_makes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.kit(root)
            calls = []
            real = mutation_check.subprocess.run
            def run(command, **options):
                calls.append(command[command.index('tests') + 1:])
                return real(command, **options)
            with patch.object(mutation_check.subprocess, 'run', side_effect=run):
                alive, test = mutation_check.survives(root, 'kit.py', '1', '2',
                                                      cached='test_other.Other.test_value')
            self.assertEqual((alive, test, calls), (False, 'test_other.Other.test_value',
                                                    [['-p', 'test_other.py', '-k', 'Other.test_value']]))

    def test_the_failing_test_is_named_in_either_unittest_format(self):
        self.assertEqual(mutation_check.failed_test('FAIL: test_x (test_tool.Tool.test_x)\n'),
                         'test_tool.Tool.test_x')
        self.assertEqual(mutation_check.failed_test('x\nERROR: test_x (test_tool.Tool)\n'), 'test_tool.Tool.test_x')
        self.assertIsNone(mutation_check.failed_test('OK\n'))

    def test_the_committed_cache_names_only_listed_mutants(self):
        cache = json.loads((mutation_check.KIT / mutation_check.CACHE).read_text(encoding='utf-8'))
        self.assertLessEqual(set(cache), {m[0] for m in mutation_check.MUTANTS})
