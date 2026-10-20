# Records

Contract version: 1

The kit's records are JSON files, except handoffs, which are Markdown with
fixed headings. `tools/kit.py check` is the reference reader; this page is
the specification a person or another tool can follow without it. Templates
are in `templates/`. Times are ISO 8601 with a time zone. Revisions are
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
| `paths.tasks`, `paths.handoffs` | Where task records and handoffs live, relative to the project root. |
| `design` | Optional: `{"system", "references"}`. The project's own design system, if any. |
| `data` | Optional: `{"sensitivity", "restricted"}`. What must never leave the project. |

## Task record: one file per task in `paths.tasks`

Name each file after its task, `<id>.json`, and give a new task the next
unused ID. Task IDs are unique within the project.

| Field | Meaning | Required from state |
| --- | --- | --- |
| `kit` | Always `"task/1"`. | always |
| `id`, `title`, `state` | Stable ID, title and current state. | always |
| `author` | Who implements the task. A proposed task may not have one yet. | `accepted` |
| `profile` | A profile name from `project.json`. | `accepted` |
| `requirement` | `{"revision", "problem", "decision_owner", "excluded": [...], "acceptance": [{"id", "example"}], "acceptance_boundary"}`. Optional `assumptions`: choices made without the decision owner, such as examples added beyond the request. | `accepted` |
| `questions` | Optional: `[{"id", "question", "recommended", "answer"}]` for the decision owner. | |
| `plan` | Optional: `{"risks", "recovery", "increments", "evidence"}`; `evidence` maps acceptance examples to the checks and boundaries that will show them. | |
| `candidate` | `{"revision", "base"}`: the exact state under review and the revision its work started from. Optional `integrated`: `[{"revision", "evidence"}]` for revisions, such as the merge that landed it, that equal the candidate outside the task and handoff folders; `tools/kit.py integrated` produces that evidence. | `candidate` |
| `checks` | `[{"id", "revision", "result", "evidence"}]`. `result` is `pass`, `fail`, `skipped` or `unknown`. Each required check has a result for the candidate by `candidate` and passes by `reviewed`. | `candidate` |
| `not_applicable` | `[{"check", "reason"}]` for required checks that do not apply. | |
| `reproduction` | `{"check", "base", "base_result": "fail", "candidate_result": "pass", "evidence"}` when the profile requires it. `check` is the test or command that shows the defect; `base` equals `candidate.base`, run with the new test added and the code unchanged. | `reviewed` |
| `reviews` | `[{"reviewer", "revision", "verdict", "findings": [{"id", "blocking", "status", "summary"}]}]`. `verdict` is `approve` or `changes`; `status` is `open` or `resolved`. | `reviewed` |
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

Name the file after its task, `<task ID>.md`. The five sections appear in
this order. `Next action` holds exactly one list item. `Updated` is not in
the future, and `State` equals the task record's state.
