# Records

Contract version: 1

The kit's records are JSON files, except handoffs, which are Markdown with
fixed headings. `tools/kit.py check` is the reference reader; this page is
the specification a person or another tool can follow without it. Records
may carry other fields, which the checker ignores; put evidence the contract
asks for in the fields named here, or it does not count. Templates mark the
values a project must supply with `kit-placeholder:`; a record or handoff
that still contains that marker is refused. Templates are in `templates/`.
Times are ISO 8601 with a time zone. Revisions are
whatever identifies an exact source state in the project's version control,
such as a commit ID.

## Project configuration: `.engineering-kit/project.json`

Owned by the project. Kit updates never change it.

| Field | Meaning |
| --- | --- |
| `kit` | Always `"project/1"`. |
| `name`, `scope` | What the project is and what it covers. |
| `commands` | Named local commands, for example `{"test": "npm test"}`. Informational. |
| `checks` | Map of check ID to `{"description", "command"}`. A check with no command is performed by hand. |
| `profiles` | Map of profile name to `{"required_checks": [...], "review": "required" or "none", "release": true or false, "reproduction": true or false}`. `"review": "none"` needs an exception to `REVIEW`. |
| `boundaries` | Ordered list of acceptance boundaries, weakest first, for example `["local", "ci", "staging", "production"]`. |
| `boundary_meaning` | Optional: what each boundary means here and who reaches it, for example `{"merged": "merged into main by the owner"}`. |
| `authority.roles` | Map of role name to who holds it. |
| `authority.effects` | Map of effect kind to the roles that may authorize it. An effect kind not listed is refused. |
| `instructions.clients` | Map of agent client to the instruction files it loads, in load order. |
| `instructions.precedence` | Always `"stricter"`: the stricter of project and kit rules applies. |
| `rules` | The project's own rules: `{"id", "text", "enforced", "by"}`. `enforced` is `guidance`, `partial`, `checked` or `integration`; `by` names the check or integration unless it is guidance. |
| `exceptions` | `{"rule", "scope", "reason", "approved_by", "date"}`. `rule` is a contract rule that is not fixed; `approved_by` is a role. |
| `integrations` | Map of integration name to `{"grant": [permissions]}`. An integration whose permissions are not all granted is not installed. |
| `paths.tasks`, `paths.handoffs` | Where task records and handoffs live, relative to the project root. Neither covers `.engineering-kit/kit` nor the lock; they may be the same folder. |
| `design` | Optional: `{"system", "references"}`. The project's own design system, if any. |
| `data` | Optional: `{"sensitivity", "restricted"}`. What must never leave the project. |

## Task record: one file per task in `paths.tasks`

Name each file after its task, `<id>.json`, and give a new task the next
unused ID. Task IDs are unique within the project, and no record, task or
handoff, is named like an instruction file (`AGENTS`, `CLAUDE`, `GEMINI`,
`copilot-instructions`, `README`, or any file in `instructions.clients`),
compared without case: agents read such files as rules.

| Field | Meaning | Required from state |
| --- | --- | --- |
| `kit` | Always `"task/1"`. | always |
| `id`, `title`, `state` | Stable ID, title and current state. | always |
| `author` | Who implements the task. A proposed task may not have one yet. | `accepted` |
| `contributors` | Optional: everyone else who changed the candidate or recorded its evidence, such as a session that committed the author's work. None of them may approve it. | |
| `profile` | A profile name from `project.json`. | `accepted` |
| `requirement` | `{"revision", "problem", "decision_owner", "excluded": [...], "acceptance": [{"id", "example"}], "acceptance_boundary"}`. Optional `assumptions`: choices made without the decision owner, such as examples added beyond the request. | `accepted` |
| `questions` | Optional: `[{"id", "question", "recommended", "answer"}]` for the decision owner. | |
| `plan` | Optional: `{"risks", "recovery", "increments", "evidence"}`; `evidence` maps acceptance examples to the checks and boundaries that will show them. | |
| `candidate` | `{"revision", "base"}`: the exact state under review and the revision its work started from. Optional `integrated`: `[{"revision", "evidence"}]` for revisions, such as the merge that landed it, that equal the candidate except in process files: task records and handoffs, recognised by their content and named after their task, directly in the folders the candidate's own `project.json` names; `.engineering-kit/project.json` and the lock; and what the lock's release installs or removes: kit files, integration files and one entry block per instruction file. A lock that changed is checked against the published release at the source the candidate's lock names; a changed source, a kit adopted or removed after the candidate, or a release that cannot be fetched leaves the result `UNKNOWN`. `tools/kit.py integrated` produces that evidence. | `candidate` |
| `checks` | `[{"id", "revision", "result", "evidence"}]`. `result` is `pass`, `fail`, `skipped` or `unknown`. Each required check has a result for the candidate by `candidate` and passes by `reviewed`. | `candidate` |
| `not_applicable` | `[{"check", "reason"}]` for required checks that do not apply. | |
| `reproduction` | `{"check", "base", "base_result": "fail", "candidate_result": "pass", "evidence"}` when the profile requires it. `check` is the test or command that shows the defect; `base` equals `candidate.base`, run with the new test added and the code unchanged. | `reviewed` |
| `reviews` | `[{"reviewer", "revision", "verdict", "evidence", "findings": [{"id", "blocking", "status", "summary"}]}]`. `verdict` is `approve` or `changes`; the optional `evidence` says what the reviewer examined and reran; `status` is `open` or `resolved`. | `reviewed` |
| `effects` | `[{"kind", "target", "authorized_by", "authorization", "door", "rollback", "irreversible", "status"}]`. `door` is `two-way` or `one-way`; a one-way effect states in `irreversible` what cannot be undone. `status` is `planned`, `done`, `failed`, `uncertain` or `rolled_back`. | whenever present |
| `release` | `{"source", "artifact", "checks": [...], "rollback"}`. `source` is the candidate or one of its integrated revisions. | `released` |
| `verification` | `[{"boundary", "revision", "result", "evidence"}]`, on the candidate or an integrated revision. | `verified` |
| `documentation` | `{"updated": [paths]}` or `{"none": "reason"}`. | `closed` |
| `exception` | Optional rule IDs this task relies on, each recorded in `project.json`. | |

States in order: `proposed`, `accepted`, `in_progress`, `candidate`,
`reviewed`, `released`, `verified`, `closed`. `blocked`, `failed` and
`cancelled` end or pause a task at any point and need no further evidence,
but anything already recorded must still be truthful: an unauthorized effect
or a pass claimed for the wrong revision is refused in every state.

## Handoff: one Markdown file in `paths.handoffs`

```markdown
# <title> handoff

Task: <task ID>
Updated: <ISO time with zone>
State: <task state>

## State
## Evidence
## Open gates
## Decisions and authority
## Next action
- <exactly one action, with its done-when>
```

Name the file after its task, `<task ID>.md`; every `.md` file in the
folder is read as a handoff. The five sections appear in this order. `Next action` holds exactly one list item. `Updated` is not in
the future, and `State` equals the task record's state.

## Integration manifest: `integrations/<name>/integration.json`

| Field | Meaning |
| --- | --- |
| `kit`, `name` | `"integration/1"` and the folder's name. |
| `summary`, `capabilities`, `runtime` | What it does, the capabilities it adds and what it needs to run. |
| `contract` | The contract versions it supports. |
| `permissions` | What installing it allows; the project grants each one in `project.json`. |
| `inputs`, `evidence` | What it reads and the evidence it produces. |
| `files` | `[{"source", "target", "permission"}]`: files it installs, with `source` relative to its folder and the declared permission that covers the file. Targets stay outside `.engineering-kit/` and any `.git` folder, compared without case. |
| `blocks` | `[{"target"}]`: instruction files that receive the marked entry block; it needs the `writes-instructions` permission. |
| `manual` | How to meet the same need by hand without it. |

Permissions: `writes-instructions` adds the entry block to an instruction
file; `review-template` adds a template to a hosting service's review form;
`ci-workflow` adds automation that runs on the hosting service when code is
pushed. An integration that declares a permission the project has not
granted is not installed, and a release that adds a permission stops the
update until the project grants it. Permissions are declarations shown in
the preview, not a sandbox: review a release's files before granting.

## Release manifest: `RELEASE.json` in each tagged release

`{"kit": "release/1", "version", "contract", "digest", "files", "integrations", "notes"}`.
`files` maps every installed file to its SHA-256; `digest` is the SHA-256 of
the lines `<sha256>  <path>` sorted by path. `tests/`, `examples/` and
`conformance/` stay in the kit's repository and are not installed. A release
is the Git tag `v<version>` on the commit that holds this file.

## Lock: `.engineering-kit/lock.json`

Written by `tools/kit.py` and never edited by hand.
`{"kit": "lock/1", "source", "version", "commit", "digest", "contract", "integrations", "files", "blocks", "excluded", "adopted", "created", "history"}`.
`files` and `blocks` hold the SHA-256 of what the kit installed, so `status`
can tell local changes apart. `excluded` lists files, and `block:FILE`
entry blocks, that the project kept as its own when the kit offered one
there; later updates leave them alone. `adopted` lists files the project
already had in exactly the kit's form, which stay when the kit is removed.
`created` lists instruction files the kit created for its block, the only
ones removal may delete. `history` lists every release applied, newest last.
A release whose tag no longer points at the commit and digest recorded for
it, installed or earlier, is refused.

## Contribution: `contribution.json` beside `change.patch`

| Field | Meaning |
| --- | --- |
| `kit` | Always `"contribution/1"`. |
| `project`, `source_revision`, `kit_version` | Where the lesson came from. |
| `files` | The kit files the patch changes, relative to the kit's root. |
| `need`, `evidence`, `limits`, `owner` | The failure or need, what shows the change helps, where it is unproven, and who maintains it. |
| `rights` | `owner-authored`, `licensed:<SPDX identifier>` or `cleared:<reference>`. Anything else, such as unknown or employer material without clearance, stays out. |
| `status` | `proposal` until evidence shows the lesson works, then `proven`. |
