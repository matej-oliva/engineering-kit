# Everyday use

[Guide](README.md) · Run every command from the project's root folder.
`python3 kit` alone lists them, and `python3 kit COMMAND --help` shows a
command's options with an example.

| Command | What it does | Changes files |
| --- | --- | --- |
| `check` | Checks `project.json`, every task and every handoff against the contract | never |
| `check-task FILE` | Checks one task record | never |
| `check-handoff FILE` | Checks one handoff | never |
| `status` | Shows the installed release and any kit file you changed | never |
| `scan-secrets` | Looks for credentials in the staged copy of each file | never |
| `integrated CANDIDATE REVISION` | Shows whether a merge changed anything beyond the reviewed candidate | never |
| `update` | Moves to the newest release, or the one you name | only with `--apply` |
| `rollback` | Returns to the release installed before | only with `--apply` |
| `recover` | Undoes the writes of an interrupted apply | yes, from its journal |
| `remove` | Takes the kit out, keeping `project.json`, tasks and handoffs | only with `--apply` |
| `guide` | Shows where this guide is | never |

Every command that changes files first prints the plan, ending in a line
such as `plan 3f2a9c1e5d7b8a40`, and writes only when you add `--apply`.
Nothing is committed: review the change with `git diff` and commit it
yourself. Exit status 0 means success, 1 means a refusal with its reason.

## Before you ask for review

```sh
git add -A
python3 kit scan-secrets
python3 kit check
```

`scan-secrets` reads the staged copy of each file, so stage first. It never
prints a secret it finds, only where it is. A test fixture that must look
like a token is accepted by listing its digest in
`.engineering-kit/secret-allowlist.json` with a reason.

## Update to a new release

Read the release notes first. Then:

```sh
python3 kit status            # what is installed, and what you changed
python3 kit update --diff     # preview the newest release, with each change as a diff
python3 kit update --apply    # install it
python3 kit check
```

The update keeps your changes to kit files and merges them with the
release's changes. When both changed the same lines it stops before
writing anything; [Troubleshooting](troubleshooting.md#an-update-stops-on-an-overlap)
shows how to settle it. Without a version, `update` never moves the project
back to an older release. To install one release in particular, name it:
`python3 kit update 1.2.0 --apply`.

A release that changes the contract version asks you to confirm with
`--accept-contract N` after reading what changed. A release that adds a
permission to an integration you use waits until you grant it in
`project.json`.

## Roll back

```sh
python3 kit rollback          # preview the release installed before
python3 kit rollback --apply
```

Rollback returns the kit files to the earlier release and keeps your own
changes, like an update in the other direction.

## Remove the kit

```sh
python3 kit remove
python3 kit remove --apply
```

Removal deletes the kit files, the integration files and the marked block in
each instruction file, and restores those files' other text byte for byte.
`project.json`, tasks and handoffs stay, so you can adopt again later.

## Check a merge

After a reviewed candidate is merged, show that the merge added nothing
beyond process files such as task records:

```sh
python3 kit integrated abc1234 main
```

`abc1234` is the candidate the review approved. Record the result in the
task's `candidate.integrated`, as the message says.

## Worked example: a small change

A teammate asks for a `--quiet` option. The agent records task `T-12` with
the problem, the owner, an acceptance example ("`tool --quiet sync` prints
nothing and exits 0") and the boundary `merged`. It chooses the profile
`change`, whose required check is `tests`. It implements, commits candidate
`9f1c2ab`, runs the tests and records `{"id": "tests", "revision":
"9f1c2ab", "result": "pass"}`. A different reviewer approves `9f1c2ab`.
After the merge, `python3 kit integrated 9f1c2ab main` passes, and the
record moves to `verified` with that evidence, then to `closed` with the
documentation it updated. If the reviewer had approved an older revision,
`check-task` would refuse the record with rule `CANDIDATE`.
