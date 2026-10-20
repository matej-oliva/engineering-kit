# Implement

Use while changing the repository for an accepted task. Set `state` to
`in_progress` when you start.

1. **Stay inside the task.** Change what the acceptance examples need and
   nothing speculative: no option, abstraction or cleanup the task does not
   ask for. Record a problem you find outside the task as a new task instead
   of fixing it silently (rule `PRESERVE`).
2. **Keep work you did not make.** Never discard, overwrite or reformat
   someone else's changes. Work that spans sessions uses its own branch or
   working copy.
3. **Start a defect with its reproduction** (`procedures/diagnose-defect.md`):
   a check that fails for the reported reason before any fix.
4. **Run the focused checks** for what you change while you iterate. Run the
   profile's required checks once the candidate is complete.
5. **Fix the candidate**: record `candidate.revision` and `candidate.base`,
   the revision your work started from, and set `state` to `candidate`. Any
   later edit makes a new candidate, and checks and reviews then apply to the
   new revision (rule `CANDIDATE`). Commits that change only process files,
   the `.engineering-kit/` folder and the task and handoff folders, such as
   the one recording the candidate, do not.
   If your environment cannot create a revision, for example a sandbox that
   keeps Git read-only, set `state` to `blocked` and list each changed file
   with its SHA-256 in the handoff's evidence. The next action, for a session
   that can commit, is to commit those files unchanged and repeat the checks
   on that revision; that session adds itself to `contributors`. This step
   is a proposal from one pilot.
6. **Record each check** with the revision it ran on and its result. A
   skipped, unknown or failed check is recorded as such, never as a pass
   (rule `CHECKS`).
7. **Hand off if you stop** before acceptance (`procedures/handoff.md`).

Done when the task passes `tools/kit.py check-task FILE` in state
`candidate` and its required checks are recorded against that revision.
