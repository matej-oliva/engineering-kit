"""Record which Perl switch words really enable in-place editing, by asking Perl.

    python3 tests/perl_switch_table.py write    # run the sweep and write tests/perl_switches.json
    python3 tests/perl_switch_table.py show     # print the counts of the committed table

The suite does not run Perl. test_work_cycle.py reads the committed table and holds the edit guard
to it. A word is listed under "refuse" when real Perl either parsed it as -i (it sets $^I in a BEGIN
block) or rewrote a real file when given it with -p, and under "allow" when it did neither. The
sweep covers every word of up to three characters that contains i, over every Perl switch character
plus a few others, so the guard is checked against Perl and not against its own reading of Perl.
"""
from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_release import remove_tree  # noqa: E402

TABLE = Path(__file__).resolve().parent / 'perl_switches.json'
SWITCHES = '0aCcdDeEfFghiIlmMnpsSTtuUvVwWxX'  # perldoc perlrun
OTHERS = '179.=:oz'
ALPHABET = SWITCHES + OTHERS
BEGIN = 'BEGIN { print defined $^I ? "KIT:Y\\n" : "KIT:N\\n"; exit }'


def words() -> list[str]:
    found = []
    for length in (1, 2, 3):
        found += [''.join(letters) for letters in itertools.product(ALPHABET, repeat=length) if 'i' in letters]
    return found


def quiet() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))  # -u asks Perl to dump core


def run(arguments: list[str], cwd: Path, environment: dict) -> str:
    try:
        done = subprocess.run(['perl', *arguments], cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, errors='replace', timeout=20, preexec_fn=quiet)
        return done.stdout
    except subprocess.TimeoutExpired:
        return ''


def sweep() -> dict:
    version = subprocess.run(['perl', '-e', 'print $^V'], capture_output=True, text=True, check=True).stdout
    refuse, allow = [], []
    with tempfile.TemporaryDirectory(prefix='kit-perl-sweep-') as directory:
        scratch = Path(directory)
        environment = {'PATH': os.environ['PATH'], 'HOME': str(scratch), 'LC_ALL': 'C', 'PERLDB_OPTS': 'NonStop'}
        target = scratch / 'x'
        for word in words():
            parsed = 'KIT:Y' in run([f'-{word}', '-e', BEGIN], scratch, environment)
            target.write_text('a\n', encoding='utf-8')
            run(['-p', f'-{word}', '-e', 's/a/b/', 'x'], scratch, environment)
            rewrote = target.read_text(encoding='utf-8') != 'a\n'
            if rewrote and not parsed:
                raise SystemExit(f'-{word} rewrote a file without setting $^I; read it by hand')
            (refuse if parsed or rewrote else allow).append(word)
            for stray in scratch.iterdir():  # backups and anything a switch left behind
                if stray != target:
                    remove_tree(stray) if stray.is_dir() else stray.unlink()
    return {'perl': version, 'alphabet': ALPHABET, 'refuse': ' '.join(refuse), 'allow': ' '.join(allow)}


def main(argv: list[str]) -> int:
    if argv == ['write']:
        TABLE.write_text(json.dumps(sweep(), indent=1) + '\n', encoding='utf-8')
    elif argv != ['show']:
        raise SystemExit(__doc__)
    table = json.loads(TABLE.read_text(encoding='utf-8'))
    print(f'Perl {table["perl"]}: {len(table["refuse"].split())} words enable -i, '
          f'{len(table["allow"].split())} do not')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
