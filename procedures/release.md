# Release and verify

Use when a reviewed candidate is ready to reach its users. A profile without
a release goes straight to step 5.

1. **Prepare each effect** with `procedures/change-preflight.md` and record
   it in the task as `planned`, with its kind, target, the authorization the
   project's policy accepts, its door and its rollback (rule `EFFECTS`).
2. **Build the release from the candidate revision.** Record its source
   revision, an artifact identity that cannot silently change (a digest, or
   a version bound to a revision), the checks it passed and the rollback
   target (rule `RELEASE`).
3. **Record before you act, then apply.** Update each effect's status after
   applying it. If the outcome is unclear or the work was interrupted, mark
   the effect `uncertain` and inspect the target before trying again
   (rule `UNKNOWN`). Never repeat an effect that cannot be undone on a guess.
4. Set `state` to `released`.
5. **Verify at the acceptance boundary.** Observe the acceptance examples
   where the requirement says, for example by installing the published
   package in a clean environment, using the production site, or, for a
   `merged` boundary, checking the merged revision. `boundary_meaning` in
   `project.json` says who reaches each boundary. Record each verification
   with its boundary, revision and result, naming the candidate or one of
   its integrated revisions. A local or continuous integration pass is
   evidence at that boundary only (rule `BOUNDARY`).
6. **Roll back on failure**: follow the recorded rollback, mark the effect
   `rolled_back`, verify the rollback, and return the task.
7. **Mark the task verified** once a verification at the acceptance boundary
   or a stronger one passes for the candidate and no effect is planned or
   uncertain. Done when `tools/kit.py check-task FILE` passes in state
   `verified`.
