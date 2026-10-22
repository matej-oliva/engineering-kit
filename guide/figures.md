# Facts and figures

[Guide](README.md) · Measured numbers only. Each chart is drawn from
[`data/figures.json`](data/figures.json) by the kit's own script, and the
table under it holds the same numbers, so you can read them without the
picture. Release numbers come from each release's tagged files; timings
name the hosted run they come from.

## Checks behind each release

![Grouped bars per release showing the number of automated tests and of
deliberate faults the tests caught, both rising with each
release](images/chart-checks.svg)

In words: the releases carry more and more automated tests, and more
**deliberate faults**: copies of the kit with one safety check broken on
purpose, which the tests must catch. A fault the tests miss would show a
check nobody protects; every release is published only when all of them are
caught. The first release had no deliberate faults yet.

<!-- figures:releases -->
| Release | Date | Tests | Deliberate faults caught | Files installed |
| --- | --- | --- | --- | --- |
| 0.1.0 | 2026-10-20 | 62 | 0 | 35 |
| 0.1.1 | 2026-10-21 | 79 | 63 | 36 |
| 1.0.0 | 2026-10-21 | 79 | 63 | 37 |
| 1.0.1 | 2026-10-21 | 84 | 67 | 37 |
| 1.1.0 | 2026-10-21 | 97 | 76 | 50 |
| 1.2.0 | 2026-10-22 | 117 | 84 | 63 |
| 1.2.1 | 2026-10-22 | 121 | 86 | 80 |
<!-- /figures:releases -->

## What each release installs

![Bars per release showing how many files each release installs into a
project, rising as procedures, skills, the short command and this guide
were added](images/chart-files.svg)

In words: the installed copy grew from the core contract, procedures and
checker to include agent skills in 1.1.0, the short command and the first
guide in 1.2.0, and this complete documentation with its diagrams and
charts in 1.2.1. Everything installed lives under `.engineering-kit/kit/`.

## What an agent reads, and when

![Horizontal bars in bytes for the entry block read in every session, the
contract read to plan, review or release, one procedure on average, and the
skill descriptions read in every session](images/chart-context.svg)

In words: an agent's working memory is limited, so the kit keeps what is
read in every session small. The entry block and, when skills are enabled,
the skill descriptions are read every time. The contract is read only to
plan, review or release, and a procedure only for its stage.

<!-- figures:context -->
| What the agent reads | Bytes |
| --- | --- |
| Entry block, read in every session | 473 |
| Contract, read to plan, review or release | 6840 |
| One procedure, on average, read for its stage | 2080 |
| All skill names and descriptions, read in every session | 2905 |
<!-- /figures:context -->

## The full test suite on hosted Windows

![Horizontal bars in seconds: the suite took 1712 and 1263 seconds at commit
5a7049e, and 633 and 582 seconds at commit 6291ebb](images/chart-windows.svg)

In words: starting a program is slow on Windows, and reading a release used
to start one Git process per file. Between these two hosted runs, three
changes landed: each release is now read through one Git process, Git's
background maintenance is switched off in the tests' scratch repositories,
and two test faults were fixed. Together they cut the full suite on hosted
Windows to between a third and a half of its time; the one-process read is
the change expected to matter most, and it also makes real updates faster
there. The earlier run also had one failing test, so this compares two
nearby commits, not one change in isolation.

<!-- figures:observed -->
| Measurement | Seconds | Source |
| --- | --- | --- |
| One Git process per file, Python 3.11 | 1712 | native run 39682094280, job windows-2025 / Python 3.11, step Suite, 2026-10-22 |
| One Git process per file, Python 3.14 | 1263 | native run 39682094280, job windows-2025 / Python 3.14, step Suite, 2026-10-22 |
| One batch read per release, Python 3.11 | 633 | native run 39690264562, job windows-2025 / Python 3.11, step Suite, 2026-10-22 |
| One batch read per release, Python 3.14 | 582 | native run 39690264562, job windows-2025 / Python 3.14, step Suite, 2026-10-22 |
<!-- /figures:observed -->

## Tested environments

| System | Python | Git | Tested |
| --- | --- | --- | --- |
| Linux on ARM64 | 3.12, 3.14 | 2.53 | The suite, deliberate faults, release rehearsals, pilot projects |
| Windows Server 2025, x64, hosted | 3.11, 3.14 | 2.56 | The suite and the release lifecycle before and after each release |
| macOS 15, Apple silicon, hosted | 3.11, 3.14 | 2.55 | The suite and the release lifecycle before and after each release |

Desktop Windows and other systems have not been tested; see the
[supported environments](../README.md#supported-environments).
