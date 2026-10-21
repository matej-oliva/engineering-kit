# Understand

Use at the start of every task, before choosing tools or writing code.

1. **State the problem** in the words of whoever has it: who is affected,
   what happens now and what should happen. Done when someone outside the
   work could tell whether a result solves it.
2. **Name the decision owner**, the role that accepts the result and settles
   scope questions. Done when `requirement.decision_owner` names a role from
   `project.json`.
3. **Inspect the existing system** before proposing anything: the code,
   records and documentation the problem touches, and the checks that cover
   them. Done when every assumption is either verified or listed as an
   unknown in the task.
4. **Write acceptance examples**: observable situations with an expected
   result, such as "given one line of 2.675, the total is 2.68". Include the
   case that matters most and one that must not change. Examples you add
   beyond the request are assumptions: list them in
   `requirement.assumptions`. Done when someone who did not write an example
   could check it.
5. **Record what is excluded and the acceptance boundary**, the place where
   the result must be observed: a merged revision, a published package, a
   staging site or production. Done when `requirement.acceptance_boundary`
   is one of the project's boundaries.
6. **Ask only what is the decision owner's** (rule `DECIDE`): one batch of
   questions in the task's `questions`, each with a recommended answer.
   Choose routine engineering details yourself and write the assumption down.
7. **Accept the task**: when the request fixes the outcome, name its
   `author` and the delivery `profile` that fits its risk
   (`procedures/design.md` step 1), then set `state` to `accepted`
   yourself; the decision owner can still correct an assumption.
   When the outcome itself is the owner's open question, wait for the
   answer. Run `tools/kit.py check-task FILE`. Done when it passes (rule
   `ACCEPT`).

A new task gets the next unused ID and a file named after it. A problem found
during other work becomes a `proposed` task, which needs no author yet.

A changed requirement gets a new `requirement.revision` and returns the task
to `accepted`. Reviews made against the earlier requirement are repeated.
