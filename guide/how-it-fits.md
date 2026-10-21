# How it fits together

[Guide](README.md) · This page explains the parts of the kit and who owns
each file it touches.

## The parts

- **The contract** ([`CONTRACT.md`](../CONTRACT.md)) holds the rules, once.
  Each rule has an ID such as `CHECKS`, says whether a command enforces it,
  and says whether a project may make an exception. Fixed rules, such as
  "checks name the exact revision they examined", accept none.
- **The procedures** ([`procedures/`](../procedures/understand.md)) give the
  steps for each stage and point back at the rules they apply. Agents follow
  them; people read them when they want the detail.
- **The project configuration** (`.engineering-kit/project.json`) is yours.
  It names your checks and commands, the delivery profiles that say which
  checks a kind of work needs, the boundaries where acceptance is judged,
  who may authorize what, your own rules and any exceptions.
- **The records** are one JSON file per task and one Markdown handoff for
  each task that stopped early, in the folders `project.json` names.
  [`RECORDS.md`](../RECORDS.md) defines every field.
- **The checker** (`tools/kit.py`) reads the configuration and records and
  refuses what breaks a rule. It needs only Python and, for some commands,
  Git.
- **Integrations** (`.engineering-kit/kit/integrations/`) are optional
  adapters: the entry block in your agents' instruction files, skills, the
  short `kit` command, review templates and continuous integration for your
  Git host. Each declares the permissions it needs, and is installed only
  when `project.json` grants them all. A grant is a declaration shown in
  the preview, not a sandbox: read an integration's files before you grant
  it.
- **Releases** are version tags in the kit's repository. Each holds a
  manifest of every file with its digest, so an install is checked against
  exactly what was published. A published release never changes.

## Who owns which file

![Three groups of files: the kit's own files, which releases update; the
project's files, which the kit never changes; and the lock and journal,
which the tool keeps](images/file-ownership.svg)

In words: the **kit owns** everything under `.engineering-kit/kit/`, the
marked block between `<!-- engineering-kit:begin -->` and
`<!-- engineering-kit:end -->` in each instruction file, and the files its
granted integrations install, such as `kit` or the skills. Updates replace
these, merging any change you made. The **project owns**
`.engineering-kit/project.json`, the task and handoff folders, and all text
outside the marked block; the kit never changes them. The **tool keeps**
`.engineering-kit/lock.json`, which records the installed release and the
digest of every file it wrote, and, only while an apply runs, a journal in
`.engineering-kit/journal/` that lets `recover` undo an interrupted write.
Commit `lock.json` with the kit files; never commit a journal, and do not
edit either by hand.

Keep project notes in `project.json` rules or in your instruction files
outside the block. A changed kit file still works, but it must be merged at
every update and counts as a change when a merge is compared with its
reviewed candidate.

## What the checks prove, and what they cannot

The checker proves that the records are complete and consistent: every
required check has a passing result **for the exact candidate revision**,
the approving reviewer is not the author, every effect outside the repository
is authorized by a role your policy allows, a task is verified only by
evidence from its acceptance boundary or a stronger one, and an unknown
outcome is never counted as success.

It cannot prove that what a record says happened did happen, or who wrote
it. A record can claim a test passed. The kit makes such a claim specific and
reviewable; protected branches, signed continuous integration results and
review on your Git host make it trustworthy. `check` never runs your
project's commands, and a rule labelled `guidance` is applied only by the
people and agents who read it.

## Versions and support

A release is `MAJOR.MINOR.PATCH`. PATCH releases fix defects and wording.
MINOR releases add procedures, integrations or checks; a new check may refuse
a record an older release accepted, and the release notes list it. MAJOR
releases change the contract and ask you to accept the new version. The
newest release and the one before it are supported.
