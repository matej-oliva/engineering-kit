"""The contract, its documents and the reference checker stay consistent and portable."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import unittest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'tools'))
import kit  # noqa: E402

TOOL = (KIT / 'tools' / 'kit.py').read_text(encoding='utf-8')
# Words that tie a file to one person's environment. No kit file may use them.
ENVIRONMENT = re.compile(r'\b(T3|Terrain|Powerstation|Homebase|homelab|home-server|tailnet|workstation|'
                         r'Autopilot|olivam|matej)\b|\bops/', re.I)
# Products the core must not depend on; integrations may name them.
VENDORS = re.compile(r'\b(GitHub|GitLab|Bitbucket|Claude|Codex|OpenAI|Anthropic|Cursor|Gemini|Vercel|'
                     r'Netlify|AWS|Azure)\b')


def contract_table() -> dict[str, tuple[str, bool]]:
    rows = {}
    for line in (KIT / 'CONTRACT.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('| `'):
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            rows[cells[0].strip('`')] = (cells[2], cells[3] == 'fixed')
    return rows


def kit_files(*, core: bool):
    for path in sorted(KIT.rglob('*')):
        relative = path.relative_to(KIT)
        if (not path.is_file() or relative.parts[0] in ('tests', '.git', '.github')
                or '__pycache__' in relative.parts):  # .git exists once the kit is its own repository
            continue
        if core and (relative.parts[0] == 'integrations' or relative.name == 'THIRD_PARTY_NOTICES.md'):
            continue
        yield relative, path.read_text(encoding='utf-8')


class ContractConsistency(unittest.TestCase):
    def test_rule_table_and_checker_agree(self):
        table = contract_table()
        self.assertEqual(set(table), set(kit.RULES))
        for rule, (_, fixed) in table.items():
            self.assertEqual(kit.RULES[rule], fixed, f'{rule}: fixed differs between CONTRACT.md and kit.py')

    def test_refusals_name_contract_rules(self):
        """Every rule ID the tool can emit is a contract rule; test_conformance proves each checked one fires."""
        named = set(re.findall(r"(?:refuse|Finding|stale)\('([A-Z]+)'", TOOL))
        named |= {rule for pair in re.findall(r"'([A-Z]+)' if [^\n]* else '([A-Z]+)'", TOOL) for rule in pair}
        self.assertLessEqual(named, set(kit.RULES) | {kit.FORMAT})
        self.assertGreaterEqual(len(named), 10)

    def test_enforcement_labels_are_known(self):
        for rule, (enforced, _) in contract_table().items():
            self.assertIn(enforced, kit.ENFORCED, rule)

    def test_named_kit_paths_exist(self):
        pattern = re.compile(r'`((?:procedures|templates|tools|integrations|conformance|examples|tests)/[^`\s]*'
                             r'|[A-Z_]+\.md)`')
        for relative, content in kit_files(core=False):
            if relative.suffix != '.md':
                continue
            for name in pattern.findall(content):
                if '<' in name or name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md'):  # placeholders, a project's files
                    continue
                with self.subTest(file=str(relative), path=name):
                    self.assertTrue((KIT / name.rstrip('/')).exists(), f'{relative} names {name}')

    def test_templates_are_refused_only_for_their_placeholders(self):
        def filled(value):
            if isinstance(value, dict):
                return {key: filled(item) for key, item in value.items()}
            if isinstance(value, list):
                return [filled(item) for item in value]
            return 'filled in' if isinstance(value, str) and kit.TEMPLATE_MARKER in value else value

        project = json.loads((KIT / 'templates' / 'project.json').read_text(encoding='utf-8'))
        task = json.loads((KIT / 'templates' / 'task.json').read_text(encoding='utf-8'))
        handoff = (KIT / 'templates' / 'handoff.md').read_text(encoding='utf-8')
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        for found in (kit.check_project(project), kit.check_task(task, project), kit.check_handoff(handoff, now=now)):
            self.assertEqual([(f.rule, f.message.split(' in ')[0].split(' (')[0]) for f in found],
                             [('FORMAT', 'replace the template placeholders')])
        self.assertEqual(kit.check_project(filled(project)), [])
        self.assertEqual(kit.check_task(filled(task), filled(project)), [])
        self.assertEqual(kit.check_handoff(handoff.replace(kit.TEMPLATE_MARKER, 'Filled in:'), now=now), [])
        title_only = handoff.replace('# kit-placeholder: the task title', '# Rounding')
        self.assertEqual([f.rule for f in kit.check_handoff(title_only, now=now)], ['FORMAT'])

    def test_example_carries_the_entry_block_verbatim(self):
        block = (KIT / 'templates' / 'entry-block.md').read_text(encoding='utf-8').strip()
        example = (KIT / 'examples' / 'walkthrough' / 'project' / 'AGENT-INSTRUCTIONS.md').read_text(encoding='utf-8')
        inside = example.split('<!-- engineering-kit:begin -->\n', 1)[1].split('<!-- engineering-kit:end -->', 1)[0]
        self.assertEqual(inside.strip(), block)

    def test_integration_manifests_declare_what_they_need(self):
        for manifest in sorted((KIT / 'integrations').glob('*/integration.json')):
            with self.subTest(manifest.parent.name):
                data = json.loads(manifest.read_text(encoding='utf-8'))
                self.assertEqual(data['kit'], 'integration/1')
                self.assertEqual(data['name'], manifest.parent.name)
                self.assertIn(kit.CONTRACT_VERSION, data['contract'])
                for field in ('summary', 'runtime', 'tested', 'manual'):
                    self.assertTrue(data[field].strip())
                for field in ('capabilities', 'permissions', 'inputs', 'evidence', 'blocks', 'files'):
                    self.assertIsInstance(data[field], list)
                for entry in data['files']:  # sources are relative to the integration's folder
                    self.assertTrue((manifest.parent / entry['source']).is_file(), entry['source'])
                    self.assertIn(entry['permission'], data['permissions'], entry['target'])
                if data['blocks']:
                    self.assertIn('writes-instructions', data['permissions'])
                for entry in data['blocks'] + data['files']:  # blocks always carry the entry block
                    self.assertTrue(kit.relative_path(entry['target']))
                    self.assertNotIn(Path(entry['target']).parts[0], ('.engineering-kit', '.git'))


    def test_each_procedure_has_one_skill_that_points_at_it(self):
        """Skills are pointers: a procedure's steps live only in the procedure."""
        folder = KIT / 'integrations' / 'agent-skills'
        procedures = sorted(p.stem for p in (KIT / 'procedures').glob('*.md'))
        skills = sorted(p.name for p in (folder / 'skills').iterdir())
        self.assertEqual(skills, [f'kit-{stem}' for stem in procedures])
        for stem in procedures:
            name = f'kit-{stem}'
            with self.subTest(name):
                text = (folder / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
                front, body = re.fullmatch(r'---\n(.*?)\n---\n(.*)', text, re.S).groups()
                fields = dict(line.split(': ', 1) for line in front.splitlines())
                expected = {'name', 'description'}
                if stem == 'grill-me':
                    expected.add('disable-model-invocation')
                    self.assertEqual(fields['disable-model-invocation'], 'true')
                self.assertEqual(set(fields), expected)
                self.assertEqual(fields['name'], name)
                self.assertRegex(name, r'^[a-z0-9]+(-[a-z0-9]+)*$')
                self.assertLessEqual(len(name), 64)
                self.assertIn('Use ', fields['description'])  # says when it applies, which is how it is chosen
                self.assertLessEqual(len(fields['description']), 1024)
                self.assertIn(f'`.engineering-kit/kit/procedures/{stem}.md`', body)
                self.assertLess(len(body), 600, 'a skill points at its procedure instead of copying it')
        targets = {entry['target'] for entry in json.loads((folder / 'integration.json').read_text())['files']}
        self.assertEqual(targets, {f'{root}/{skill}/SKILL.md' for skill in skills
                                   for root in ('.agents/skills', '.claude/skills')} |
                         {'.agents/skills/kit-grill-me/agents/openai.yaml'})


class Portability(unittest.TestCase):
    def test_no_file_names_a_personal_environment(self):
        for relative, content in kit_files(core=False):
            if relative.name == 'LICENSE':  # names the copyright holder, as a licence must
                continue
            with self.subTest(str(relative)):
                self.assertIsNone(ENVIRONMENT.search(content), f'{relative} is tied to one environment')

    def test_core_names_no_vendor(self):
        for relative, content in kit_files(core=True):
            with self.subTest(str(relative)):
                match = VENDORS.search(content)
                self.assertIsNone(match, f'{relative} names {match and match.group(0)}; move it to an integration')

    def test_python_files_parse_with_the_declared_minimum_grammar(self):
        """Python 3.11 is the declared minimum. This catches newer syntax, not newer library calls."""
        import ast
        for path in sorted([*KIT.rglob('*.py'), KIT / 'integrations' / 'launcher' / 'kit']):
            if '.git' in path.relative_to(KIT).parts:
                continue
            with self.subTest(str(path.relative_to(KIT))):
                ast.parse(path.read_text(encoding='utf-8'), feature_version=(3, 11))

    def test_readme_context_sizes_are_current(self):
        readme = (KIT / 'README.md').read_text(encoding='utf-8')
        block, contract, procedure = (float(n) for n in re.findall(r'about (\d+\.\d) kB', readme))
        sizes = [len(p.read_bytes()) for p in (KIT / 'procedures').glob('*.md')]
        self.assertEqual(block, round(len((KIT / 'templates' / 'entry-block.md').read_bytes()) / 1000, 1))
        self.assertEqual(contract, round(len((KIT / 'CONTRACT.md').read_bytes()) / 1000, 1))
        self.assertEqual(procedure, round(sum(sizes) / len(sizes) / 1000, 1))


if __name__ == '__main__':
    unittest.main()
