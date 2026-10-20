# Engineering kit

A small, versioned engineering foundation that projects adopt, update from
and contribute lessons back to. It defines how work moves from an idea to
verified delivery and maintenance, and what evidence each step leaves. Each
project keeps its own language, framework, design system, agent client, Git
host, deployment platform and permissions.

Status: version 0.1.0, the pilot release, contract version 1. See
`CHANGELOG.md`. MIT licence; see `LICENSE`.

## Contents

| Path | What it is |
| --- | --- |
| `CONTRACT.md` | The rules, each with how it is enforced. Start here. |
| `RECORDS.md` | The project configuration, task record and handoff formats. |
| `procedures/` | The steps for each stage, each ending in a checkable result. |
| `templates/` | A starting project configuration, task, handoff and the entry block for instruction files. |
| `tools/kit.py` | The reference checker. |
| `integrations/` | Optional adapters that connect the contract to a particular tool. |

The kit's own repository also holds what an installed copy leaves out:
`conformance/`, planted failures and known-good records that any checker
must agree with; `examples/walkthrough/`, a defect in a small library from
its brief to a closed task with a handoff; and `tests/`.

## Check a project

The reference checker needs Python 3.11 or later and nothing else;
`scan-secrets` and `integrated` also use the Git command line. It reads records and never
runs a command that a project supplies.

```sh
python3 .engineering-kit/kit/tools/kit.py check
python3 .engineering-kit/kit/tools/kit.py check-task .engineering-kit/tasks/T-1.json
python3 .engineering-kit/kit/tools/kit.py scan-secrets
python3 .engineering-kit/kit/tools/kit.py integrated CANDIDATE MERGED
```

`check` exits 1 and names the contract rule for each refusal. A project that
does not use Python follows the same procedures and checks its records by
hand against `RECORDS.md` and the rule table in `CONTRACT.md`.

## Adopt, update and contribute

A release is a Git tag `vX.Y.Z` in the kit's repository, served by any Git
host or a plain path. To start a new project or bring an existing one in,
clone the release anywhere outside the project, then run its tool from the
project's root. It installs the release it was cloned at, from the address
it was cloned from:

```sh
git clone --depth 1 --branch v0.1.0 KIT_ADDRESS ~/engineering-kit-0.1.0
python3 ~/engineering-kit-0.1.0/tools/kit.py adopt --with copilot           # preview
python3 ~/engineering-kit-0.1.0/tools/kit.py adopt --with copilot --apply   # write
```

`--with` names the instruction files your agents read, beyond `AGENTS.md`:
`claude-code`, `copilot` or `gemini`; see `integrations/`. Later, from the
project:

```sh
python3 .engineering-kit/kit/tools/kit.py update 0.2.0 --diff
python3 .engineering-kit/kit/tools/kit.py rollback --apply
```

On Windows, run `py` instead of `python3`. A private kit repository needs
the machine to be signed in to an account that can read it.

Updates merge the project's own changes to kit files with the release's and
stop without writing when they overlap. `procedures/adopt-and-update.md` and
`procedures/contribute.md` give the steps; `RECORDS.md` describes the lock,
release and contribution files. The kit is never installed by running code
from a release, and it writes only under `.engineering-kit/kit/`, the files
its granted integrations name, and the marked entry block.

## Context cost

Only the entry block is loaded into every agent session: about 0.4 kB. The
contract is read when work is planned, reviewed or released: about 6.8 kB.
A procedure is about 1.8 kB and is read only for its stage.

## Test the kit

```sh
python3 -m unittest discover -s tests
```

The suite needs no network, no credentials, no Git hosting service and no
running application. Before a release, `python3 tests/mutation_check.py`
breaks each guard on purpose and confirms a test notices; add a mutant when
you add a guard.
