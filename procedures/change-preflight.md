# Preflight an effect

Use before any effect outside the repository: a deployment, a data
migration, a call that changes an external service, a permission change or a
deletion. The preflight prepares the effect; it does not apply it. The
evidence ladder in step 6 is adapted from `backnotprop/pstack`, MIT licensed;
see `THIRD_PARTY_NOTICES.md`.

1. **Restate the exact target** and confirm the authorization covers it under
   `authority.effects` in `project.json`. Approval for one target is not
   approval for the targets next to it.
2. **Capture the current state** of the target: versions, configuration
   digests and data counts, without copying credentials or private data.
3. **Confirm recovery.** Check that the latest backup covers the target and
   that a restore has been shown to work, or record the gap.
4. **Define the rollback** and the checks that show the change worked at the
   acceptance boundary, and that a rollback worked.
5. **Label the door and the blast radius.** Two-way means the rollback
   restores the exact earlier state; one-way means something cannot be put
   back, which you name. The blast radius is who and what is affected if it
   goes wrong.
6. **Name the one fact the change is safe because of**, and how far it is
   proven: stated, cited at a file and line, shown on a copy, or observed on
   the target. Say "unproven" rather than presenting it as settled.
7. **Prepare what a person runs.** When someone else must apply the effect,
   for example with privileges you lack, give them one reviewed, committed
   script per action with its exact command, where to run it and the
   expected result, never commands to paste or code to run as an
   administrator. The script records its outcome where you can read it, so
   you verify from that record instead of asking for pasted output; when it
   fails, fix the script rather than sending variants. Ask every decision
   that is theirs in one batch, each with a recommended answer.
8. **Record the effect** in the task as `planned` with its kind, target,
   authorizing role, authorization, door, and rollback or what is
   irreversible. Done when `tools/kit.py check-task FILE` passes.
