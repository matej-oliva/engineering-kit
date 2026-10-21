# Engineering kit

A small, versioned engineering foundation that projects adopt, update from
and contribute lessons back to. It defines how work moves from an idea to
verified delivery and maintenance, and what evidence each step leaves. Each
project keeps its own language, framework, design system, agent client, Git
host, deployment platform and permissions.

Status: version 1.0.1, contract version 1.
See `CHANGELOG.md` and `MAINTAINING.md`. MIT licence; see `LICENSE`.

## Contents

| Path | What it is |
| --- | --- |
| `CONTRACT.md` | The rules, each with how it is enforced. Start here. |
| `RECORDS.md` | The project configuration, task record and handoff formats. |
| `procedures/` | The steps for each stage, each ending in a checkable result. |
| `templates/` | A starting project configuration, task, handoff and the entry block for instruction files. |
| `tools/kit.py` | The reference checker. |
| `integrations/` | Optional adapters that connect the contract to a particular tool. |
| `MAINTAINING.md` | Versions, support, releases, contributions and recovery. |

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
git clone --depth 1 --branch v1.0.1 KIT_ADDRESS ~/engineering-kit-1.0.1
python3 ~/engineering-kit-1.0.1/tools/kit.py adopt --with copilot           # preview
python3 ~/engineering-kit-1.0.1/tools/kit.py adopt --with copilot --apply   # write
```

`--with` names the instruction files your agents read, beyond `AGENTS.md`:
`claude-code`, `copilot` or `gemini`; see `integrations/`. Add
`--with agent-skills` to install one skill per procedure in `.agents/skills/`
and `.claude/skills/`, the folders most agent clients search, so an agent
loads the procedure that fits its work without being told. Each skill only
points at its installed procedure.

To install the newest release without choosing its version, give the
address alone: `kit.py adopt KIT_ADDRESS`. Later, from the project, one
command moves to the newest release; it previews first and never moves back:

```sh
python3 .engineering-kit/kit/tools/kit.py update --diff      # preview the newest release
python3 .engineering-kit/kit/tools/kit.py update --apply     # install it
python3 .engineering-kit/kit/tools/kit.py update 1.0.1 --apply   # or a chosen release
python3 .engineering-kit/kit/tools/kit.py rollback --apply   # back to the previous one
```

On Windows, run `py` instead of `python3`. A private kit repository needs
the machine to be signed in to an account that can read it.

Updates merge the project's own changes to kit files with the release's and
stop without writing when they overlap. `procedures/adopt-and-update.md` and
`procedures/contribute.md` give the steps; `RECORDS.md` describes the lock,
release and contribution files. Initial adoption runs the installer from the
release you cloned and reviewed. Updates use the installed tool to read the
new release as data; they do not execute its hooks or installer. Writes stay
under `.engineering-kit/kit/`, the files its granted integrations name, and
the marked entry block, plus the project configuration and lock described
in `procedures/adopt-and-update.md`.

## Supported environments

| Environment | Status |
| --- | --- |
| Linux on ARM64, Python 3.14, Git 2.53 | Tested: the suite, the mutation check, both pilots and a fresh install |
| Python 3.11 to 3.13 | The declared minimum is 3.11; the suite passes natively on 3.11 (Windows, macOS) and on 3.12 (Linux) |
| Windows Server 2025 x64, Python 3.11 and 3.14, Git 2.56 | Tested on hosted runners: installing 0.1.1, updating to 1.0.0, rolling back, updating again and removing, and the full suite. Making a release or a contribution from a Windows checkout needs 1.0.1 or later |
| macOS 15 on Apple silicon, Python 3.11 and 3.14, Git 2.55 | Tested on hosted runners: the same lifecycle and the full suite |
| Agent clients, Git hosts | Each integration's `tested` field says what has used it in a real project; some have only been installed by the tests |

## Known limits

- `kit.py check` reads records. It never runs a project's checks, so a
  recorded pass is only as true as the session that recorded it; reviews
  rerun what matters.
- `kit.py integrated` needs Git access to the kit's repository when the
  lock changed after the candidate. Without it the result is unknown.
- Permissions are declarations shown in the preview, not a sandbox.
- A private kit repository needs the machine to be signed in to an account
  that can read it.
- Releases are not signed. A project trusts the repository it installs from
  and pins each release by its commit and digest.
- The record folders are the project's reviewed choice. Nothing stops a
  configuration from naming a folder an agent client reads settings from,
  where a record-shaped file could carry live hooks; reviewers read a
  configuration change like code. A client file with a leading dot, such
  as `.cursorrules`, reserves no useful name.

## Context cost

Only the entry block is loaded into every agent session: about 0.4 kB. The
contract is read when work is planned, reviewed or released: about 6.8 kB.
A procedure is about 2.1 kB and is read only for its stage. With the
`agent-skills` integration, clients that support skills also load each
skill's name and description, near 2.9 kB for all twelve, and open a skill,
and so its procedure, only when the work matches it.

## Test the kit

```sh
python3 -m unittest discover -s tests
```

The suite needs no network, no credentials, no Git hosting service and no
running application. Before a release, `python3 tests/mutation_check.py`
breaks each guard on purpose and confirms a test notices; add a mutant when
you add a guard.
