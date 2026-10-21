# Changelog

Each release lists what changed, anything a project must do when updating,
and whether the contract changed. Newest first.

## Unreleased

Contract version 1, unchanged. Nothing to do after updating; to add the
skills, grant `writes-skills` to `agent-skills` in `project.json` and
update again.

- `kit.py update` without a version moves to the newest release at the
  source, compared as numbers, previews first and never moves a project
  back. `kit.py adopt SOURCE` without a version installs the newest release.
- The optional `agent-skills` integration installs one skill per procedure
  in `.agents/skills/` and `.claude/skills/`. Each skill names when it
  applies and points at the installed procedure, so the steps stay in one
  place.
- `implement.md` asks for checks on every claimed platform and the oldest
  supported runtime, for exit statuses that a pipeline cannot hide, and for
  safe work in a shared environment. `change-preflight.md` asks for a
  committed, self-recording script, not pasted commands, when a person must
  apply an effect. Lessons from the kit's first native platform tests and
  the owner's own operations repository.
- `release` also refuses a link or submodule outside the installed files,
  as every install already did.

## 1.0.1, 2026-10-21

Contract version 1, unchanged. Nothing to do after updating.

- Tested on Windows Server 2025 and macOS 15, each with Python 3.11 and
  3.14, as well as Linux. The manually started native-platform workflow runs
  the suite and an offline adoption, update, rollback and removal exercise
  between the two newest published releases. Repository workflows stay out
  of installed release payloads.
- `release` builds the manifest from the files committed at `HEAD`, the
  tree a tag will hold, so a release made from a working copy whose editor
  saved CRLF no longer fails verification on install. It refuses kit files
  that are staged, edited, untracked or in conflict, and links or
  submodules, which every install would refuse. `contribute` writes `change.patch` byte for byte, so on Windows
  it still applies with `git apply`. Neither changes the contract.
- The test suite runs on Windows and macOS: fixtures write exact bytes,
  compare POSIX paths, clean up read-only Git objects and no longer depend
  on `/etc/hostname`. `tests/windows_text_mode.py` runs the suite with
  Windows text-mode newlines on any host, and each release tag also gets a
  release page on the kit's Git host.

## 1.0.0, 2026-10-21, first supported release

The first release with a support promise; see `MAINTAINING.md`. Contract
version 1, unchanged, and no tool behaviour changed since 0.1.1. Nothing
to do after updating.

- `MAINTAINING.md`: version policy, the two supported releases, how a
  release is made and reviewed, contributions and recovery.
- `README.md` lists the environments the kit has run on and its known
  limits. Each integration gains a `tested` field saying what has used it
  in a real project.
- The review procedure says a handoff is not evidence, where a reviewer's
  own reruns go, and that the reviewer proposes a task for each
  non-blocking finding. The update procedure says to keep project notes
  out of kit files, because a changed kit file makes every merge a new
  candidate.

## 0.1.1, 2026-10-21, pilot release

Lessons from the first pilots. Contract version 1, unchanged. After
updating, run `kit.py check`: it now refuses a few malformed records that
0.1.0 accepted, listed below.

- Windows checkouts: line endings that Git converts on checkout no longer
  count as local changes, kit files keep the style a file uses throughout,
  every byte of an instruction file outside the entry block stays as it was,
  and the kit's own files stay on Unix line endings through
  `.gitattributes`. Tested by simulation on Linux, not yet on Windows.
- `procedures/implement.md` says what to do when the environment cannot
  create a revision, such as a sandbox that keeps Git read-only.
  Contributed from the `eqradio` pilot; a proposal until more agents use it.
- `kit.py integrated` now accepts, besides task records and handoffs,
  changes to `project.json`, the lock, and kit files and one entry block per
  instruction file that match exactly the release the lock records. A
  changed lock is checked against the published release at the source the
  candidate's lock names, so `integrated` then needs Git access to the kit;
  without it, after a change of source, or when the kit was adopted after
  the candidate, the result is unknown. A kit update or a configuration fix
  no longer makes a new candidate; a hand-edited kit file or lock still
  does. Task records and handoffs are recognised by their content and
  their name, directly in the folders the candidate's own configuration
  names, matched literally; instruction files the kit created or removed,
  and integration files a release removed, are accepted when they match
  what the release does, and a kit removed after the candidate is unknown.
- No task record or handoff may be named like an instruction file, such
  as `CLAUDE.md`, `CLAUDE.local.md` or `README.json`, compared by the part
  before the first dot and without case; `check` refuses
  it and `integrated` treats it as an ordinary file.
- Tasks may list `contributors`, each a name, who may not approve the
  candidate.
- Every review names its revision, and may record its `evidence`.
- Templates mark values to fill in with `kit-placeholder:` at the start of a
  value. `kit.py check` refuses that marker in `project.json`, a task or a
  handoff, and `adopt` names that step. The 0.1.0 templates marked them
  "replace with"; search `project.json`, tasks and handoffs for that once,
  by hand.
- `paths.tasks` and `paths.handoffs` must name a folder that covers neither
  the kit's files nor the lock.
- `tests/mutation_check.py` breaks each guard on purpose before a release
  and confirms a test notices.
- A failed Git command names the command, not its options.
- `RECORDS.md` says that extra fields are ignored, so evidence goes in the
  named fields. `scan-secrets` reads the staged copy of each file: stage
  every change before scanning.
- The handoff procedure says the next action is one step a single session
  can do.

## 0.1.0, 2026-10-20, pilot release

First version, for the pilots; the first supported release follows them.
Contract version 1.

- The contract: 18 rules, each labelled with how it is enforced, the
  lifecycle and precedence. The record formats for project configuration,
  tasks, handoffs, integrations, releases, the lock and contributions.
- Twelve procedures, from understanding a request to contributing a lesson
  back.
- `tools/kit.py`: the reference checker, secret scan, integrated-revision
  check, and adoption, updates, rollback, removal, recovery, releases and
  contributions.
- Integrations: `agents-md`, `claude-code`, `copilot`, `gemini`, `github`
  and `gitlab`. `adopt --with NAME` enables one when a project starts, and
  `adopt` without arguments installs the release the tool was cloned at.
- MIT licence.
