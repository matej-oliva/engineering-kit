# Engineering kit

A small, versioned engineering foundation that projects adopt, update from
and contribute lessons back to. It defines how work moves from an idea to
verified delivery and maintenance, and what evidence each step leaves. Each
project keeps its own language, framework, design system, agent client, Git
host, deployment platform and permissions.

Status: contract version 1, not yet released. Distribution, updates and
contributions arrive with the first release.

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

## Context cost

Only the entry block is loaded into every agent session: about 0.4 kB. The
contract is read when work is planned, reviewed or released: about 6.7 kB.
A procedure is about 1.7 kB and is read only for its stage.

## Test the kit

```sh
python3 -m unittest discover -s tests
```

The suite needs no network, no credentials, no Git hosting service and no
running application.
