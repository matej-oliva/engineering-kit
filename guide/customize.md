# Customize your project

[Guide](README.md) · The kit fits a project through two places: the
integrations you choose when you adopt it, and the facts in
`.engineering-kit/project.json`. Nothing else needs editing, and the kit's
own files are best left as released.

![A sequence of choices: which agents read instructions, whether to install
skills and the short command, which Git host to connect, then the commands,
profiles, boundaries, authority, rules and folders in project.json](images/customization.svg)

In words: first choose the **integrations**, which decide what the kit
installs: instruction files for your agents, skills, the short `kit`
command, and review templates or continuous integration for your Git host.
Then fill in **`project.json`** from top to bottom: the commands and checks
your project already has, the delivery profiles that say which checks each
kind of work needs, the acceptance boundaries from weakest to strongest, who
decides and who may authorize each kind of effect, your own rules with how
each is enforced, any exceptions, and where tasks and handoffs live.

## What the project is

`name` and `scope` say what the project is, who uses it and what it does
not cover, in a sentence or two; reviewers and agents read them to judge
whether a request belongs here. `data.sensitivity` says what data the
project holds, and `data.restricted` lists what must never enter a record,
a handoff or a contribution. Who decides goes in `authority.roles`, below.

## Integrations

| Integration | Installs | Permission it needs |
| --- | --- | --- |
| `agents-md` | the entry block in `AGENTS.md`, read by many agents | `writes-instructions` |
| `claude-code`, `copilot`, `gemini` | the same block in `CLAUDE.md`, `.github/copilot-instructions.md` or `GEMINI.md` | `writes-instructions` |
| `agent-skills` | one skill per procedure in `.agents/skills/` and `.claude/skills/` | `writes-skills` |
| `launcher` | the short `kit` command at the project root | `writes-launcher` |
| `github` | a pull request template and a workflow that runs `check` | `review-template`, `ci-workflow` |
| `gitlab` | a merge request template, and a pipeline file your own `.gitlab-ci.yml` must include before it runs | `review-template`, `ci-workflow` |

`adopt --with NAME` enables an integration in a new `project.json` and
grants what it declares. In an existing project, add it under
`integrations` with its permissions and run `python3 kit update --apply`:

```json
"integrations": {
  "agents-md": {"grant": ["writes-instructions"]},
  "launcher": {"grant": ["writes-launcher"]}
}
```

A grant is a declaration shown in the preview, not a sandbox: read the
integration's files before you grant it. An integration whose target file
already exists and is not the kit's stops the change before anything is
written; move or merge that file first. Each integration's
`integration.json` has a `tested` field saying what has really used it;
several, including the continuous integration workflows and the launcher,
have so far been exercised only by the kit's tests.

## Agent entry points

`instructions.clients` lists, for each agent client you use, the
instruction files it reads, in the order it reads them. `check` refuses a
listed file that does not exist, so keep this in step with the
integrations you enabled. `instructions.precedence` is always `"stricter"`:
where your instructions and the contract differ, the stricter one applies.

```json
"instructions": {
  "clients": {"any-agent": ["AGENTS.md"], "claude-code": ["CLAUDE.md", "AGENTS.md"]},
  "precedence": "stricter"
}
```

## Commands, checks and profiles

`commands` records the commands people use, for reference. `checks` names
what must pass, with the command if one exists, so a test command often
appears in both. A check without a command is done by hand and recorded the
same way. The kit never runs these commands, and `python3 kit check` does
not show that they work: run each one yourself once. `profiles` groups
checks by kind of work:

```json
"commands": {"test": "make test", "serve": "make serve"},
"checks": {
  "tests": {"description": "Unit tests pass", "command": "make test"},
  "visual": {"description": "Screens match the design at three widths"}
},
"profiles": {
  "change": {"required_checks": ["tests"], "review": "required", "release": false},
  "defect": {"required_checks": ["tests"], "review": "required", "release": false, "reproduction": true},
  "screen": {"required_checks": ["tests", "visual"], "review": "required", "release": true},
  "docs": {"required_checks": [], "review": "none", "release": false}
}
```

`reproduction: true` makes a defect fix start with a check that fails before
the fix. `release: true` adds the release stage, with its effects and
rollback. `"review": "none"` skips review, which the contract allows only
through a recorded exception, shown below. A task names one profile.

## Boundaries and authority

`boundaries` lists where acceptance can be judged, weakest first, and
`boundary_meaning` says what each means here. `authority.roles` names who
holds each role, and `authority.effects` lists, per kind of effect outside
the repository, the roles that may authorize it. A kind of effect that is
not listed is refused:

```json
"boundaries": ["local", "merged", "staging", "production"],
"authority": {
  "roles": {"owner": "Dana Ruiz", "on-call": "the operations rota"},
  "effects": {"deploy": ["owner"], "migration": ["owner"], "rollback": ["owner", "on-call"]}
}
```

## Rules and exceptions

Add your own rules with how each is enforced: `guidance` (people apply it),
`partial`, `checked` or `integration`, and what enforces it unless it is
guidance. A project rule needs its own ID, not one from the contract. To
relax a contract rule that is not fixed, record an exception with its
scope, reason, approving role and date. The scope is `project`,
`profile:NAME` or `task:ID`.

```json
"rules": [{"id": "API-COMPAT", "text": "Public APIs stay backward compatible within a major version",
           "enforced": "checked", "by": "the api-diff check"}],
"exceptions": [{"rule": "REVIEW", "scope": "profile:docs", "reason": "Single maintainer for typo fixes",
                "approved_by": "owner", "date": "2026-10-02"}]
```

## Contrasting projects

The same kit fits very different work. Three sketches:

- **A library** with one maintainer and outside contributors: profiles
  `change` and `defect`, boundaries `local` and `merged`, no release stage
  for ordinary changes, and a `release` profile for publishing a version
  with the package's own publish command as its effect.
- **A web service** deployed by a team: a `screen` profile with a visual
  check by hand, boundaries up to `production`, effects `deploy` and
  `migration` authorized by named roles, and the Git host integration so
  every pull request runs `check`.
- **A data pipeline** that handles restricted data: `data.restricted` lists
  what must never enter a record, a `backfill` effect is marked `one-way`
  with what it cannot undo, and verification happens at a `staging`
  boundary on a copy before `production`. The `data` fields guide people
  and agents; no check reads them.

None of these needs a particular language, framework or design system. If
your project has a design system, name it in the optional `design` field.

## Project documentation

Keep your own documentation where it already lives. A task's
`documentation` field lists the pages it updated when it closes, or says why
none changed, so your documentation stays current with the work.
