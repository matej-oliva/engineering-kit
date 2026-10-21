"""The guide installs with every release and works offline: links resolve, pictures explain themselves."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
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
