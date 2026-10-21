# Troubleshooting and recovery

[Guide](README.md) · Every refusal says what stopped and, where it can, the
command to type next. Nothing below needs anything beyond the installed kit.

## How an update decides

![A preview leads either to a stop that writes nothing, when changes overlap
or a file is in the way, or to an apply that writes through a journal; an
interrupted apply is undone with recover](images/update-flow.svg)

In words: `update`, `rollback`, `adopt` and `remove` first build a plan and
show it. If your change and the release's change overlap in a file, or a
file the release adds already exists and is not the kit's, the plan
**stops and writes nothing**. Settle each listed file and preview again.
Otherwise `--apply` writes the plan. Before each write it saves the earlier
file in a journal, so if the apply is interrupted, `recover` puts every file
back. A finished apply removes the journal and records the release in
`lock.json`.

## An update stops on an overlap

The preview lists the file with `local and kit changes overlap` and ends
`Stopped: ... Nothing was written.` Choose for each file:

- **Merge by hand.** Edit your copy so it includes the release's change, as
  shown by `update --diff`, then preview again.
- **Take the kit's version**, dropping your change:
  `python3 kit update --apply --resolve .engineering-kit/kit/procedures/review.md=kit`
- **Keep yours**, skipping the release's change to that file:
  `--resolve PATH=local`.

A file you deleted that the release still provides, and a file you changed
that the release drops, stop the same way and are settled the same way.
Keeping your side of a deleted or unmanaged file with `PATH=local` takes
that path out of the kit's care for good: later updates leave it alone, and
the lock lists it under `excluded`.

## An unmanaged file is in the way

A release or integration adds a file, such as `kit` at the root, that your
project already has with different content. Rename or merge your file, or
leave the integration out of `project.json`, then preview again. If your
file is identical to the kit's, the kit adopts it and leaves it in place if
the kit is ever removed.

## A release lacks an integration you granted

`integration launcher is not in release 1.1.0; to use that release, remove
"launcher" from integrations in .engineering-kit/project.json` appears when
you roll back or move to a release older than an integration. Remove the
named entry, then preview again. If the removed integration is `launcher`,
the `kit` command goes with it; use
`python3 .engineering-kit/kit/tools/kit.py` instead.

## The plan changed since the preview

`the plan is ..., not the previewed ...; preview again` means something
changed between your preview and `--apply --plan DIGEST`: a file, or a newer
release appeared. Preview again and apply the new plan.

## An apply was interrupted

A crash, a full disk or a closed terminal can stop an apply halfway. Every
later `adopt`, `update`, `rollback` or `remove` then refuses with
`an earlier apply was interrupted`; `check` and the other read-only commands
still run. Run:

```sh
python3 kit recover
```

`recover` restores each file the apply had written. If you edited one of
those files after the interruption, it refuses and names them, so nothing of
yours is overwritten: copy your edits elsewhere and run it again, or keep
the files as they are with `python3 kit recover --abandon`.

## Other refusals

| Message | What to do |
| --- | --- |
| `this project has not adopted the kit; use adopt` | Run `adopt` from a kit clone, as in [Quick start](quick-start.md). |
| `the contract changes from 1 to 2; read the release notes, then rerun with --accept-contract 2` | Read what changed in the contract, then rerun with that option. |
| `... is a symbolic link` | The kit never writes through a link. Replace the link with a real folder or file. |
| `release ... manifest does not match its files` | The release does not match what was published. Use another release and tell the kit's maintainer. |
| `git ls-remote failed: ...` or `git fetch failed: ...` | The machine cannot read the kit's source: a Git address it is not signed in to, or a folder that moved or is missing. Sign in, or give the new address or folder once with `--source`, for example `python3 kit update --source NEW_ADDRESS`; `rollback` and `remove` take it too. The new source must hold exactly the release you have installed. |
| `Run it from the project root: cd ...` | The short `kit` command works only from the folder that holds it. Change to that folder and run it again. |
| `FORMAT` from `check` | A file cannot be read as a record, or still holds a `kit-placeholder:` value. Fix the field the line names. |
| A rule ID from `check`, such as `CHECKS` | The record lacks evidence the rule needs. [`RECORDS.md`](../RECORDS.md) names the field. |

## Start again

If the kit files are in a state you no longer trust, remove the kit and
adopt it again from a clone of a release tag. Your `project.json`, tasks and
handoffs are kept. A kit file you changed stops the removal; settle it with
`--resolve PATH=kit` first.

```sh
python3 kit remove --apply
python3 ~/engineering-kit/tools/kit.py adopt --apply
```

Undoing an effect your project applied, such as a deployment, is not the
kit's job: follow the rollback recorded in that task's `effects`.
