# Adopt, update and remove the kit

Use when a project takes up the kit, moves to another release, or gives it
up. The commands write files and never commit; review their result like any
other change. Every command previews by default and writes only with
`--apply`.

## Adopt

1. **Get the tool**: clone the kit's repository anywhere, outside the
   project, at the release you want.
2. **Preview**: from the project's root run
   `python3 PATH/TO/KIT/tools/kit.py adopt SOURCE VERSION --diff`, where
   SOURCE is the kit repository's address or path. It lists every file it
   would add and the entry block it would add to `AGENTS.md`. Existing
   instructions are kept; the block is appended between markers.
3. **Reconcile instructions.** Read the project's own instruction files
   against `CONTRACT.md`. Where a project rule is stricter, keep it. Where it
   is weaker, either change it or record an exception in `project.json` with
   its scope, reason, approver and date; fixed rules accept none.
4. **Apply** with `--apply --plan DIGEST`, using the digest the preview
   printed, so what is written is what you reviewed.
5. **Fill in `project.json`**: scope, checks, profiles, boundaries and their
   meaning, authority and integrations. Grant an integration's permissions
   only after reading its manifest; discovering an integration grants
   nothing. Run `update VERSION --apply` to install newly enabled ones.
6. Done when `tools/kit.py check` passes and the change is reviewed and
   committed.

## Update or roll back

1. Run `tools/kit.py status` to see the installed release and any local
   changes to kit files. Keep project notes in `project.json` `rules` or in
   your instruction files outside the entry block, not inside kit files: a
   changed kit file conflicts with updates, and `kit.py integrated` counts
   it as a change, so merging it makes a new candidate.
2. Preview with `tools/kit.py update --diff`, after reading the release
   notes. Without a version it previews the newest release at the source and
   never moves the project back; give `VERSION` to choose one. If a newer
   release appears between the preview and the apply, `--plan` refuses the
   apply. Local changes are merged with the release's changes. An
   overlap stops the update without writing anything: edit the local file to
   include the kit's change, or rerun with `--resolve PATH=kit` or
   `--resolve PATH=local`. A release that changes the contract needs
   `--accept-contract N`; one that adds an integration permission needs the
   grant first.
3. Apply with `--apply --plan DIGEST`, run the project's checks, review and
   commit.
4. `tools/kit.py rollback` returns to the previously installed release the
   same way, keeping local changes.

## Recover and remove

- If an apply is interrupted, every later command refuses until
  `tools/kit.py recover` restores the files it had changed. It stops if
  any of them changed since; save that work elsewhere and run it again, or
  keep the files as they are with `recover --abandon` and preview the update
  again.
- `tools/kit.py remove --apply` deletes unchanged kit files and the entry
  block. It keeps `project.json`, tasks, handoffs and any kit file you
  changed, after you resolve each one.
