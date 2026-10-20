# Changelog

Each release lists what changed, anything a project must do when updating,
and whether the contract changed. Newest first.

## 0.1.1, 2026-10-20, pilot release

Lessons from the first pilots. Contract version 1, unchanged; nothing to do
when updating except filling any placeholder `check` now reports.

- `procedures/implement.md` says what to do when the environment cannot
  create a revision, such as a sandbox that keeps Git read-only.
  Contributed from the `eqradio` pilot; a proposal until more agents use it.
- A candidate is now judged outside all process files: changes to
  `.engineering-kit/`, such as a configuration fix or a kit update, no
  longer make a new candidate.
- Tasks may list `contributors`, who may not approve the candidate.
- Every review names its revision, and may record its `evidence`.
- `kit.py check` refuses template placeholders ("replace with") left in
  `project.json` or a task, and `adopt` names that step.
- A failed Git command names the command, not its options.
- `RECORDS.md` says that extra fields are ignored, so evidence goes in the
  named fields; the contract says `scan-secrets` reads tracked and staged
  files.
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
