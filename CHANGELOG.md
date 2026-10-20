# Changelog

Each release lists what changed, anything a project must do when updating,
and whether the contract changed. Newest first.

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
