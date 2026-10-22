"""Measure the kit's releases and draw the guide's charts from those numbers alone.

    python3 tests/guide_figures.py measure X.Y.Z   # write guide/data/figures.json; X.Y.Z labels HEAD
    python3 tests/guide_figures.py render          # write guide/images/chart-*.svg from that file
    python3 tests/guide_figures.py check           # refuse charts that differ from their data

`measure` reads every release tag and HEAD with Git, so it runs in the kit's repository. The
`observed` entries in the data file, such as timings from a hosted run, are kept as written, each
with its source. `render` and `check` need only the data file, so they also run in a copy.
"""
from __future__ import annotations

import ast
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

KIT = Path(__file__).resolve().parents[1]
DATA = KIT / 'guide' / 'data' / 'figures.json'
IMAGES = KIT / 'guide' / 'images'
FONT = 'Helvetica, Arial, sans-serif'
INK, MUTED, BLUE, GREEN, AMBER = '#111827', '#4b5563', '#1d4ed8', '#15803d', '#b45309'


def git(*args) -> bytes:
    return subprocess.run(['git', *args], cwd=KIT, capture_output=True, check=True).stdout


def tests_in(revision: str) -> int:
    """Test cases the suite at REVISION defines, without running them."""
    with tempfile.TemporaryDirectory(prefix='kit-figures-') as directory:
        with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', revision))) as bundle:
            bundle.extractall(directory, filter='data')
        code = ('import sys, unittest; sys.path.insert(0, "tests"); '
                'print(unittest.defaultTestLoader.discover("tests", top_level_dir="tests").countTestCases())')
        done = subprocess.run([sys.executable, '-B', '-c', code], cwd=directory, capture_output=True, text=True,
                              check=True)
        return int(done.stdout.split()[-1])


def mutants_in(revision: str) -> int:
    try:
        source = git('show', f'{revision}:tests/mutation_check.py').decode()
    except subprocess.CalledProcessError:
        return 0
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'MUTANTS' for t in node.targets):
            return len(node.value.elts)
    return 0


def installed_files(revision: str) -> int:
    try:
        return len(json.loads(git('show', f'{revision}:RELEASE.json'))['files'])
    except subprocess.CalledProcessError:  # HEAD before its release commit: count what release would list
        sys.path.insert(0, str(KIT / 'tools'))
        import kit_update
        names = git('ls-tree', '-r', '--name-only', revision).decode().split('\n')
        return sum(1 for name in names if name and kit_update.payload(name))


def size(revision: str, path: str) -> int:
    return len(git('show', f'{revision}:{path}'))


def measure(label: str) -> dict:
    tags = sorted((t for t in git('tag', '--list', 'v*').decode().split() if re.fullmatch(r'v\d+\.\d+\.\d+', t)),
                  key=lambda t: tuple(map(int, t[1:].split('.'))))
    releases = []
    for name, revision in [*((t[1:], t) for t in tags if t[1:] != label), (label, 'HEAD')]:
        releases.append({'version': name, 'date': git('log', '-1', '--format=%cs', revision).decode().strip(),
                         'tests': tests_in(revision), 'mutants': mutants_in(revision),
                         'installed_files': installed_files(revision)})
    procedures = [p for p in git('ls-tree', '--name-only', 'HEAD', 'procedures/').decode().split() if p]
    skills = KIT / 'integrations' / 'agent-skills' / 'skills'
    context = {
        'entry block, read in every session': size('HEAD', 'templates/entry-block.md'),
        'contract, read to plan, review or release': size('HEAD', 'CONTRACT.md'),
        'one procedure, on average, read for its stage': round(sum(size('HEAD', p) for p in procedures)
                                                                / len(procedures)),
        'all skill names and descriptions, read in every session': sum(
            len(path.read_text(encoding='utf-8').split('---')[1].encode()) for path in skills.glob('*/SKILL.md')),
    }
    observed = json.loads(DATA.read_text(encoding='utf-8')).get('observed', []) if DATA.exists() else []
    return {'releases': releases, 'context_bytes': context, 'observed': observed}


# ------------------------------------------------------------------ drawing

def svg(title: str, desc: str, width: int, height: int, body: list[str]) -> str:
    return '\n'.join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-labelledby="title desc" font-family="{FONT}">',
        f'  <title id="title">{title}</title>', f'  <desc id="desc">{desc}</desc>',
        f'  <rect width="{width}" height="{height}" fill="#ffffff"/>', *('  ' + line for line in body),
        '</svg>', ''])


def text(x, y, value, size=13, anchor='middle', fill=INK, weight='normal'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}">{value}</text>')


def bars(series: list[tuple[str, str, list[int]]], labels: list[str], title: str, desc: str,
         unit: str) -> str:
    """Grouped vertical bars: SERIES is (name, colour, values) per group of LABELS."""
    width, height, left, bottom, top = 900, 380, 70, 320, 60
    top_value = max(max(values) for _, _, values in series)
    scale = (bottom - top) / (top_value * 1.1)
    group = (width - left - 30) / len(labels)
    bar = min(36, (group - 20) / len(series))
    body = [text(left, 30, title, 17, 'start', weight='bold'),
            f'<line x1="{left}" y1="{bottom}" x2="{width - 20}" y2="{bottom}" stroke="{MUTED}"/>']
    for step in range(0, int(top_value * 1.1) + 1, max(1, int(round(top_value / 4, -1)))):
        y = bottom - step * scale
        body += [f'<line x1="{left}" y1="{y:.1f}" x2="{width - 20}" y2="{y:.1f}" stroke="#e5e7eb"/>',
                 text(left - 8, y + 4, step, 12, 'end', MUTED)]
    for index, label in enumerate(labels):
        start = left + index * group + (group - bar * len(series)) / 2
        for number, (_, colour, values) in enumerate(series):
            x, value = start + number * bar, values[index]
            y = bottom - value * scale
            body += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar - 4:.1f}" height="{bottom - y:.1f}" '
                     f'fill="{colour}"/>', text(x + (bar - 4) / 2, y - 6, value, 12)]
        body.append(text(left + index * group + group / 2, bottom + 20, label, 13))
    x = left
    for name, colour, _ in series:
        body += [f'<rect x="{x}" y="42" width="12" height="12" fill="{colour}"/>',
                 text(x + 18, 53, name, 13, 'start')]
        x += 30 + 8 * len(name)
    body.append(text(width - 20, bottom + 44, unit, 12, 'end', MUTED))
    return svg(title, desc, width, height, body)


def hbars(rows: list[tuple[str, int]], title: str, desc: str, unit: str, colour: str = BLUE) -> str:
    width, row, left, top = 900, 46, 360, 60
    height = top + row * len(rows) + 30
    longest = max(value for _, value in rows)
    scale = (width - left - 120) / longest
    body = [text(20, 30, title, 17, 'start', weight='bold')]
    for index, (label, value) in enumerate(rows):
        y = top + index * row
        body += [text(left - 12, y + 20, label, 13, 'end'),
                 f'<rect x="{left}" y="{y + 4}" width="{max(value * scale, 2):.1f}" height="24" fill="{colour}"/>',
                 text(left + value * scale + 8, y + 21, f'{value:,} {unit}'.replace(',', ' '), 13, 'start')]
    return svg(title, desc, width, height, body)


def charts(data: dict) -> dict[str, str]:
    releases = data['releases']
    labels = [r['version'] for r in releases]
    tests, mutants = [r['tests'] for r in releases], [r['mutants'] for r in releases]
    files = [r['installed_files'] for r in releases]
    out = {
        'chart-checks.svg': bars(
            [('tests', BLUE, tests), ('deliberate faults caught', GREEN, mutants)], labels,
            'Automated checks behind each release',
            'Grouped bars per release, ' + '; '.join(f'{v}: {t} tests and {m} deliberate faults caught'
                                                       for v, t, m in zip(labels, tests, mutants)) + '.',
            'count per release'),
        'chart-files.svg': bars(
            [('files installed in a project', AMBER, files)], labels, 'What each release installs',
            'Bars per release, ' + '; '.join(f'{v}: {f} files' for v, f in zip(labels, files)) + '.',
            'files under .engineering-kit/kit/'),
        'chart-context.svg': hbars(
            list(data['context_bytes'].items()), 'What an agent reads, and when',
            'Horizontal bars in bytes: ' + '; '.join(f'{k}: {v} bytes' for k, v in data['context_bytes'].items())
            + '.', 'bytes'),
    }
    timing = [o for o in data['observed'] if o.get('chart') == 'chart-windows.svg']
    if timing:
        out['chart-windows.svg'] = hbars(
            [(o['label'], o['value']) for o in timing], 'Full test suite on hosted Windows',
            'Horizontal bars in seconds: ' + '; '.join(f'{o["label"]}: {o["value"]} seconds' for o in timing)
            + '.', 'seconds', GREEN)
    return out


PAGE = KIT / 'guide' / 'figures.md'


def tables(data: dict) -> dict[str, str]:
    """The figures page's tables, so its text holds the same numbers as its charts."""
    releases = ['| Release | Date | Tests | Deliberate faults caught | Files installed |',
                '| --- | --- | --- | --- | --- |']
    releases += [f'| {r["version"]} | {r["date"]} | {r["tests"]} | {r["mutants"]} | {r["installed_files"]} |'
                 for r in data['releases']]
    context = ['| What the agent reads | Bytes |', '| --- | --- |']
    context += [f'| {label[0].upper() + label[1:]} | {value} |' for label, value in data['context_bytes'].items()]
    observed = ['| Measurement | Seconds | Source |', '| --- | --- | --- |']
    observed += [f'| {o["label"][0].upper() + o["label"][1:]} | {o["value"]} | {o["source"]} |'
                 for o in data['observed']]
    return {'releases': '\n'.join(releases), 'context': '\n'.join(context), 'observed': '\n'.join(observed)}


def page_with_tables(page: str, data: dict) -> str:
    for name, table in tables(data).items():
        page = re.sub(rf'<!-- figures:{name} -->\n.*?<!-- /figures:{name} -->',
                      lambda _: f'<!-- figures:{name} -->\n{table}\n<!-- /figures:{name} -->', page, flags=re.S)
    return page


def main(argv: list[str]) -> int:
    if argv[:1] == ['measure'] and len(argv) == 2:
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(json.dumps(measure(argv[1]), indent=2) + '\n', encoding='utf-8', newline='\n')
        return 0
    data = json.loads(DATA.read_text(encoding='utf-8'))
    page = PAGE.read_text(encoding='utf-8')
    if argv == ['render']:
        for name, content in charts(data).items():
            (IMAGES / name).write_text(content, encoding='utf-8', newline='\n')
        PAGE.write_text(page_with_tables(page, data), encoding='utf-8', newline='\n')
        return 0
    if argv == ['check']:
        stale = [name for name, content in charts(data).items()
                 if not (IMAGES / name).is_file() or (IMAGES / name).read_text(encoding='utf-8') != content]
        stale += ['figures.md'] if page_with_tables(page, data) != page else []
        print('Charts and tables match their data.' if not stale
              else 'These differ from their data: ' + ', '.join(stale))
        return 1 if stale else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
