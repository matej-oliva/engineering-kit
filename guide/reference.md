# Technical reference

[Guide](README.md) · How the kit is built and how each part behaves, for
people who maintain a project's setup, review the kit or want to know
exactly what it does to a repository. Formats are specified field by field
in [`RECORDS.md`](../RECORDS.md); the rules in [`CONTRACT.md`](../CONTRACT.md).

## Architecture

![The kit's repository publishes release tags, each with a manifest; a
project installs a release into .engineering-kit/kit/ plus integration
files and entry blocks; the lock records what was installed; the checker
reads the project's configuration and records](images/architecture.svg)

In words: the kit's **source repository** publishes **releases** as Git
tags. Each tag holds `RELEASE.json`, a manifest with the SHA-256 digest of
every file it installs. **Adopting or updating** fetches one tag into a
temporary repository, verifies it against its manifest and writes the files
into the project: the kit itself under `.engineering-kit/kit/`, the files of
granted integrations such as skills or the `kit` command, and the marked
entry block in each instruction file. `.engineering-kit/lock.json` records
the release, its source and the digest of everything written. The
**checker** reads `.engineering-kit/project.json`, the task records and the
handoffs, and never runs anything the project supplies.

| Component | File | Role |
| --- | --- | --- |
| Checker and command line | `tools/kit.py` | `check`, `check-task`, `check-handoff`, `scan-secrets`, `integrated`; parses every command |
| Distribution | `tools/kit_update.py` | Builds and verifies releases; adopts, updates, rolls back, removes and recovers; prepares contributions |
| Contract | `CONTRACT.md` | The 18 rules and how each is enforced |
| Specification | `RECORDS.md` | Every field of every record and manifest |
| Procedures | `procedures/` | Twelve step lists, one per kind of work |
| Templates | `templates/` | A starting `project.json`, task, handoff and the entry block |
| Integrations | `integrations/` | Optional adapters, each with an `integration.json` manifest |
| Guide | `guide/` | This documentation |

Both programs use only the Python standard library (3.11 or later) and the
`git` command line. `check`, `check-task` and `check-handoff` need no Git.

## Commands

Run from the project root as `python3 kit COMMAND` with the `launcher`
integration, or as `python3 .engineering-kit/kit/tools/kit.py COMMAND`.
Every command accepts `--root FOLDER`. Exit status 0 is success, 1 a
refusal with its reason, 2 a mistyped command.

| Command | Arguments and options | Writes |
| --- | --- | --- |
| *(none)* | | Lists the everyday commands |
| `check` | `--json` | No |
| `check-task FILE` | `--json` | No |
| `check-handoff FILE` | `--json` | No |
| `scan-secrets` | `--json` | No |
| `integrated CANDIDATE REVISION` | `--json` | No |
| `status` | | No |
| `guide` | | No |
| `adopt [SOURCE [VERSION]]` | `--with NAME` (repeatable), `--apply`, `--plan DIGEST`, `--resolve PATH=kit\|local`, `--diff` | With `--apply` |
| `update [VERSION]` | `--source ADDRESS`, `--accept-contract N`, `--apply`, `--plan`, `--resolve`, `--diff` | With `--apply` |
| `rollback` | `--source`, `--accept-contract N`, `--apply`, `--plan`, `--resolve`, `--diff` | With `--apply` |
| `remove` | `--source`, `--apply`, `--plan`, `--resolve`, `--diff` | With `--apply` |
| `recover` | `--abandon` | Yes, from the journal |
| `contribute FILE...` | `--out FOLDER`, `--need`, `--evidence`, `--limits`, `--rights`, `--owner` (all required) | Into `--out` only |
| `check-contribution FILE` | `--json` | No |
| `release VERSION` | `--check` | `RELEASE.json`, in the kit's own repository |

`adopt` with no source installs the release the running tool was cloned at;
with a source alone, the newest release there. `update` with no version
moves to the newest release and never moves back.

## Records

| Record | Where | Owner | Specification |
| --- | --- | --- | --- |
| Project configuration | `.engineering-kit/project.json` | the project | [RECORDS.md](../RECORDS.md#project-configuration-engineering-kitprojectjson) |
| Task record | one JSON file per task in `paths.tasks` | the project | [RECORDS.md](../RECORDS.md#task-record-one-file-per-task-in-pathstasks) |
| Handoff | one Markdown file per task in `paths.handoffs` | the project | [RECORDS.md](../RECORDS.md#handoff-one-markdown-file-in-pathshandoffs) |
| Lock | `.engineering-kit/lock.json` | the tool | [RECORDS.md](../RECORDS.md#lock-engineering-kitlockjson) |
| Contribution | `contribution.json` beside `change.patch` | the contributor | [RECORDS.md](../RECORDS.md#contribution-contributionjson-beside-changepatch) |
| Release manifest | `RELEASE.json` in each release tag | the kit | [RECORDS.md](../RECORDS.md#release-manifest-releasejson-in-each-tagged-release) |
| Integration manifest | `integrations/<name>/integration.json` | the kit | [RECORDS.md](../RECORDS.md#integration-manifest-integrationsnameintegrationjson) |

### Task states

![The task states in order, proposed, accepted, in_progress, candidate,
reviewed, released, verified and closed, with blocked, failed and cancelled
reachable from any of them, and the shortcut from reviewed to verified when
a profile has no release](images/task-states.svg)

In words: a task moves forward through `proposed`, `accepted`,
`in_progress`, `candidate`, `reviewed`, `released`, `verified` and `closed`.
Each state requires more evidence than the one before, and the checker
refuses a record whose state claims evidence it does not hold. A profile
without a release goes straight from `reviewed` to `verified`. `blocked`,
`failed` and `cancelled` can end or pause a task at any point; whatever was
recorded before must still be truthful.

## How an update is computed

For every file the kit manages, the updater compares three versions: the
**base**, as the installed release shipped it; **yours**, as it is in the
project now; and **theirs**, as the new release ships it.

| Situation | Result |
| --- | --- |
| New in the release, absent in the project | Added |
| New in the release, the project has an identical file | Kept; it stays if the kit is removed |
| New in the release, the project has a different file | Stop: "an unmanaged file is in the way" |
| Yours equals theirs | Nothing to do |
| Dropped by the release, yours unchanged | Deleted |
| Dropped by the release, yours changed | Stop: "changed locally but dropped by the kit" |
| Deleted by you, still in the release | Stop: "deleted locally but still provided by the kit" |
| Yours unchanged, the release changed it | Updated |
| You changed it, the release did not | Your version kept |
| Both changed, different lines | Merged line by line |
| Both changed, the same lines | Stop: "local and kit changes overlap" |

A stop writes nothing; `--resolve PATH=kit` or `PATH=local` settles one
file. The entry block is replaced inside its markers while every byte
around it is kept, and a file that uses Windows line endings throughout
keeps them. The plan's digest covers every planned action and the target
version, so `--apply --plan DIGEST` writes only the plan that was
previewed.

## Applying and recovering

`--apply` first saves each file it will change into
`.engineering-kit/journal/`, with digests of its state before and after,
then writes. If the apply is interrupted, every later change refuses until
`recover` restores the saved files; `recover` refuses to overwrite a file
edited since, unless `--abandon` drops the journal and keeps the files as
they are. A finished apply removes the journal and any folder its
deletions left empty.

## Releases and integrity

![A release commit's files are hashed into RELEASE.json and tagged; on
install every file is checked against the manifest, the manifest against
its own digest, and later fetches against the commit and digest the lock
recorded](images/release-integrity.svg)

In words: `release` hashes every file of the committed tree that a project
would receive and writes the digests into `RELEASE.json`, whose own digest
covers the list. The commit holding it is tagged. On every fetch the kit
refuses a tag containing a link or submodule, a manifest that does not list
exactly the files present, a file whose SHA-256 differs from the manifest,
or a manifest whose digest is wrong. The lock records the commit and digest
of what was installed, so a later update or rollback refuses a tag that was
moved or replaced. A published tag never changes; a fix ships as a new
release.

## Security model

- **Bounded writes.** The kit writes only under `.engineering-kit/kit/`, the
  files its granted integrations name, the marked block in instruction
  files, `project.json` when adopting into a project without one, the lock
  and the journal. It refuses targets outside the project, inside `.git`,
  or through a symbolic link.
- **Permissions are declarations.** Each integration declares what it may
  write; a project grants permissions in `project.json`, and the preview
  lists them. They are not a sandbox: read an integration's files before
  granting it.
- **Updates run no release code.** The installed tool reads a new release
  as data. Only the first adoption runs the tool from a clone you chose.
- **Sources are guarded.** A source that looks like a command-line option is
  refused, Git's command-running transports are disabled, and every fetched
  file is checked against its manifest.
- **Instructions in content grant nothing.** Rule `AUTHORITY`: text in
  documents, tool output or contributed files never grants permission.
- **Secrets stay out.** `scan-secrets` refuses common credential shapes in
  staged files without printing them.

## Versions and compatibility

Releases follow `MAJOR.MINOR.PATCH`: PATCH fixes defects and wording, MINOR
adds procedures, integrations or checks, MAJOR changes the contract and asks
each project to accept it with `--accept-contract N`. The newest release
and the one before it are supported. Each release is rehearsed by
installing the two previous releases with their own tools and updating them
to it, because older installed tools must be able to read every new
release.

## Quality assurance

| Layer | What it shows | Where |
| --- | --- | --- |
| Test suite | Every command and refusal behaves as specified | `tests/` in the kit's repository |
| Windows text mode | The tests do not rely on Unix line endings | `tests/windows_text_mode.py` |
| Mutation check | Each guard is needed: a deliberately broken copy must fail the tests | `tests/mutation_check.py` |
| Native platforms | The suite and a full release lifecycle pass on Windows and macOS | hosted workflow, before and after each release |
| Release rehearsal | The two previous releases update to the new one with their own tools | `tests/native_release.py --candidate` |
| Independent review | Someone other than the author approves each release | `MAINTAINING.md` |
| Fresh-agent acceptance | An agent with no context can use the kit from this guide alone | release records |

[Facts and figures](figures.md) shows these in numbers.
