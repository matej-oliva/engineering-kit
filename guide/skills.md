# Skills

[Guide](README.md) · A **skill** is a small file that an agent loads by
itself when your request matches its description. The kit offers twelve, one
for each procedure. They are optional: enable them with the `agent-skills`
integration.

## Why skills help

Without skills, an agent must notice the entry block, open the contract and
choose the right procedure itself. With skills, the agent sees a one-line
description of each of the twelve at the start of a session, near 2.9 kB in
total, and opens the one that fits as soon as you ask for something. Ask
"the checkout shows the wrong total" and it opens `kit-diagnose-defect`;
ask "deploy this" and it opens `kit-change-preflight`, then `kit-release`.

Each skill only points at its procedure, so the steps live in one place.
When the kit updates a procedure, every skill follows automatically.

## Where each skill fits

![The six lifecycle stages from Understand to Maintain, each with its skill
below, plus four skills used at any time: diagnose a defect, preflight an
effect, hand off and resume, and write instructions; two more manage the kit
itself](images/skills-map.svg)

In words: six skills follow the stages of a task, from `kit-understand` to
`kit-maintain`. Four are used whenever the situation arises:
`kit-diagnose-defect` for a bug, `kit-change-preflight` before a risky
step, `kit-handoff` when stopping or resuming, and `kit-write-instructions`
when editing rules for agents. Two concern the kit itself:
`kit-adopt-and-update` and `kit-contribute`.

## All twelve skills

| Skill | In plain words | The agent uses it when |
| --- | --- | --- |
| `kit-understand` | Pins down what is really asked before anything is built | A new task, feature request or bug report arrives; for a bug, `kit-diagnose-defect` follows |
| `kit-design` | Plans the work: how much evidence it needs, its risks, how to recover, small steps | A task is accepted and before any code, or when asked to plan |
| `kit-implement` | Changes the code within the task, with checks recorded against one exact version | Writing or changing code, tests or configuration |
| `kit-review` | Has someone else check that exact version against what was asked | A change is ready for review, before merging, or to review someone's work |
| `kit-release` | Ships the reviewed version and confirms it where success is judged, with a way back | Deploying, publishing or shipping, or before calling a task verified |
| `kit-maintain` | Closes the task cleanly and turns lessons into improvements | Finishing a task, after an incident, or deciding an upgrade |
| `kit-diagnose-defect` | Reproduces a bug, finds its cause and fixes it with a test that failed first | Something behaves wrongly or a test fails unexpectedly, once the bug is recorded as a task |
| `kit-change-preflight` | Prepares a risky change outside the code: target, backup, rollback, approval | Before a deployment, data migration, permission change or deletion |
| `kit-handoff` | Leaves, or picks up, a note so the next session continues correctly | Stopping before a task is done, near a time or context limit, or resuming |
| `kit-write-instructions` | Writes rules for agents that are short, clear and checkable | Editing `AGENTS.md`, `CLAUDE.md`, a skill or a procedure |
| `kit-adopt-and-update` | Installs, updates, rolls back or removes the kit, previewing first | Installing the kit, moving to a newer release, or giving it up |
| `kit-contribute` | Sends a useful lesson back to the kit with its evidence and rights | Something learned here would help other projects |

## Where the files are

The integration installs each skill twice, because agent programs look in
different folders: `.agents/skills/kit-NAME/SKILL.md` and
`.claude/skills/kit-NAME/SKILL.md`. Each file holds a name, a description and
one paragraph pointing at `.engineering-kit/kit/procedures/NAME.md`. Updates
replace them with the next release's versions, and removing the kit removes
them.

To enable them in an existing project, add
`"agent-skills": {"grant": ["writes-skills"]}` under `integrations` in
`project.json` and run `python3 kit update VERSION --apply` with your
installed release. The `tested` field in
`integrations/agent-skills/integration.json` says which agents have been
seen using them.
