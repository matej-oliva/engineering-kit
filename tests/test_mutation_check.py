"""Exercise the release runner on a small independent kit snapshot."""
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
