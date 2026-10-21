# Everyday use

[Guide](README.md) · Run every command from the project's root folder.
`python3 kit` alone lists them, and `python3 kit COMMAND --help` shows a
command's options with an example. Without the `launcher` integration,
type `python3 .engineering-kit/kit/tools/kit.py` where this page says
`python3 kit`.

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
| `remove` | Takes the kit out, keeping `project.json`, tasks and handoffs | only with `--apply` |
| `recover` | Undoes the writes of an interrupted apply | yes, at once |
| `guide` | Shows where this guide is | never |

`update`, `rollback`, `remove` and `adopt` first print the plan, ending in a
line such as `plan 3f2a9c1e5d7b8a40`, and write only when you add
`--apply`. Add `--plan 3f2a9c1e5d7b8a40` to apply only that exact plan, so
nothing that changed since the preview slips in. `recover` writes at once:
it only puts back files from an interrupted apply. Nothing is committed:
review the change with `git diff` and commit it yourself. Exit status 0
means success, 1 a refusal with its reason, and 2 a mistyped command.

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
changes, like an update in the other direction. An earlier release may
lack an integration you granted later, such as `launcher` before 1.2.0:
the preview then refuses and names it. Remove that entry from
`integrations` in `project.json` first. Rolling back past the `launcher`
also removes the `kit` command, so use the long form afterwards.

## Remove the kit

```sh
python3 kit remove
python3 kit remove --apply
```

Removal deletes the kit files, the integration files, `lock.json`, the
folders that leaves empty, and the marked block in each instruction file,
restoring those files' other text byte for byte. `project.json`, tasks and
handoffs stay, so you can adopt again later. A kit file you changed stops
the removal until you settle it: `--resolve PATH=local` keeps it as your own
file, `--resolve PATH=kit` deletes it.

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
nothing and exits 0") and the boundary `merged`, names itself as author and
chooses the profile `change`, whose required check is `tests`. It
implements, commits candidate `9f1c2ab`, runs the tests and records
`{"id": "tests", "revision": "9f1c2ab", "result": "pass", "evidence": "make
test: 214 passed"}`. A different reviewer approves `9f1c2ab`. After the
merge into `main` as `4d7e0b3`, `python3 kit integrated 9f1c2ab 4d7e0b3`
passes; the agent records `4d7e0b3` in `candidate.integrated` with that
output as evidence, and adds `{"boundary": "merged", "revision": "4d7e0b3",
"result": "pass", "evidence": "..."}` to `verification`. The record moves to
`verified`, then to `closed` with the documentation it updated. If the
reviewer had approved an older revision, `check-task` would refuse the
record with rule `CANDIDATE`.
