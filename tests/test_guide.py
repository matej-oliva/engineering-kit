"""The guide installs with every release and works offline: links resolve, pictures explain themselves."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

KIT = Path(__file__).resolve().parents[1]
GUIDE = KIT / 'guide'
sys.path.insert(0, str(KIT / 'tools'))
import kit_update as ku  # noqa: E402

LINK = re.compile(r'(!?)\[([^\]]*)\]\(([^)\s]+)\)')
SVG = '{http://www.w3.org/2000/svg}'


def pages():
    return sorted(GUIDE.glob('*.md'))


def links(page: Path):
    for image, text, target in LINK.findall(page.read_text(encoding='utf-8')):
        yield bool(image), text, target


class Guide(unittest.TestCase):
    def test_every_relative_link_and_picture_reaches_an_installed_file(self):
        for page in pages():
            for _, text, target in links(page):
                if re.match(r'[a-z]+:', target):
                    self.fail(f'{page.name} links outside the installed kit: {target}')
                path = target.split('#', 1)[0]
                if not path:
                    continue
                with self.subTest(page=page.name, target=target):
                    resolved = (page.parent / path).resolve()
                    self.assertTrue(resolved.is_file(), f'{page.name}: {target} does not exist')
                    relative = PurePosixPath(resolved.relative_to(KIT).as_posix())
                    self.assertTrue(ku.payload(str(relative)), f'{page.name}: {target} is not installed')

    def test_every_anchor_names_a_heading_in_its_page(self):
        def slug(heading):  # how Markdown viewers name a heading's anchor
            return re.sub(r'[^\w\- ]', '', heading.strip().lower()).replace(' ', '-')
        for page in pages():
            for _, _, target in links(page):
                path, _, anchor = target.partition('#')
                if not anchor:
                    continue
                document = (page.parent / path).resolve() if path else page
                headings = re.findall(r'^#+ (.+)$', document.read_text(encoding='utf-8'), re.M)
                with self.subTest(page=page.name, target=target):
                    self.assertIn(anchor, {slug(h) for h in headings})

    def test_every_page_is_reachable_from_the_index_and_links_back(self):
        index = {target for _, _, target in links(GUIDE / 'README.md')}
        for page in pages():
            if page.name != 'README.md':
                with self.subTest(page.name):
                    self.assertIn(page.name, index)
                    self.assertIn('[Guide](README.md)', page.read_text(encoding='utf-8'))

    def test_every_picture_has_alt_text_and_is_explained_in_words(self):
        shown = set()
        for page in pages():
            text = page.read_text(encoding='utf-8')
            for image, alt, target in links(page):
                if image:
                    shown.add((page.parent / target).resolve())
                    with self.subTest(page=page.name, image=target):
                        self.assertGreater(len(alt.split()), 5, 'alt text describes the picture')
                        after = text.split(f']({target})', 1)[1].lstrip()
                        self.assertTrue(after.startswith('In words:'), 'a prose explanation follows')
        self.assertEqual(shown, {svg.resolve() for svg in (GUIDE / 'images').glob('*.svg')})

    def test_every_command_the_guide_shows_exists_with_its_options(self):
        shown = {}
        for page in pages():
            for line in page.read_text(encoding='utf-8').replace('\\\n', ' ').splitlines():
                for match in re.finditer(r'(?:python3|py) (?:kit|\S*kit\.py) ([a-z-]+)((?: +[^ `|#]+)*)', line):
                    options = set(re.findall(r'(?<!\S)(--[a-z-]+)', match.group(2)))
                    shown.setdefault(match.group(1), set()).update(options)
        self.assertGreater(len(shown), 8)
        for command, options in sorted(shown.items()):
            with self.subTest(command):
                result = subprocess.run([sys.executable, str(KIT / 'tools' / 'kit.py'), command, '--help'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, f'{command} is not a command: {result.stderr}')
                for option in options:
                    self.assertIn(option, result.stdout, f'{command} has no option {option}')

    def test_rights_shown_in_the_guide_are_accepted(self):
        text = (GUIDE / 'maintenance.md').read_text(encoding='utf-8')
        for value in re.findall(r'--rights (\S+)', text) + re.findall(r'`(licensed:\w+)`', text):
            with self.subTest(value):
                self.assertIsNotNone(ku.RIGHTS.fullmatch(value), 'contribute would refuse it')

    def test_charts_and_tables_are_drawn_from_the_figures_data(self):
        done = subprocess.run([sys.executable, str(KIT / 'tests' / 'guide_figures.py'), 'check'],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_diagrams_are_accessible_and_self_contained(self):
        for svg in sorted((GUIDE / 'images').glob('*.svg')):
            with self.subTest(svg.name):
                text = svg.read_text(encoding='utf-8')
                root = ET.fromstring(text)
                self.assertEqual(root.get('role'), 'img')
                self.assertEqual(root.get('aria-labelledby'), 'title desc')
                self.assertTrue((root.findtext(f'{SVG}title') or '').strip())
                self.assertGreater(len((root.findtext(f'{SVG}desc') or '').split()), 20)
                self.assertNotIn('<script', text)
                self.assertNotRegex(text, r'(href|src)="(?!#)')  # no external file, font or page


if __name__ == '__main__':
    unittest.main()
