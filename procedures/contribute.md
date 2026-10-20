# Contribute a lesson back

Use when a change you made to a kit file in your project would help other
projects, or when a project lesson should become part of the kit.

1. **Make it generic.** Remove project names, paths, data and anything
   owned by an employer, client or third party. Keep only what another
   project can use.
2. **Check your rights** (rule `LESSON`). Your own work is
   `owner-authored`. Third-party material needs its licence identifier, and
   employer or client material needs a written clearance you can cite.
   Without one, the lesson stays in the project.
3. **Package it**: commit the change in your project, then run
   `tools/kit.py contribute FILES --out DIR --need ... --evidence ...
   --limits ... --rights ... --owner ...`. It writes `change.patch` against
   the installed release and `contribution.json` with its provenance, and
   refuses an incomplete record.
4. **Propose it to the kit.** In the kit's repository, apply the patch with
   `git apply`, add a check or conformance case that fails without it where
   the lesson is mechanical, and treat it as a task with its own review.
   An unproven lesson keeps the status `proposal`.
5. **Release it**: run `tools/kit.py release VERSION` in the kit's
   repository, commit, tag `vVERSION`, and add a line to `CHANGELOG.md`.
6. Done when another project updates to that release and receives the
   change through `procedures/adopt-and-update.md`.
