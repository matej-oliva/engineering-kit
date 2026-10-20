# Changelog

Each release lists what changed, anything a project must do when updating,
and whether the contract changed. Newest first.

## 0.1.1, 2026-10-20, pilot release

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
- `kit.py integrated` now accepts, besides the task and handoff folders,
  changes to `project.json`, the lock, the secret allowlist, and kit files
  and entry blocks that match exactly the release the lock records. A kit
  update or a configuration fix no longer makes a new candidate; a
  hand-edited kit file or lock still does. The task and handoff folders are
  read from the candidate's own configuration and matched literally.
- Tasks may list `contributors`, each a name, who may not approve the
  candidate.
- Every review names its revision, and may record its `evidence`.
- Templates mark values to fill in with `kit-placeholder:` at the start of a
  value. `kit.py check` refuses that marker in `project.json`, a task or a
  handoff, and `adopt` names that step. Projects adopted at 0.1.0 marked
  them "replace with"; search `project.json` for that once, by hand.
- `paths.tasks` and `paths.handoffs` must name a folder that covers neither
  the kit's files nor the lock.
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
