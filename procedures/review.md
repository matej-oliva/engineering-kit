# Review and validate

Use when a candidate is ready. The reviewer is not the author.

1. **Choose a fresh reviewer**: another person, or an agent session that did
   not write the change and starts from the task record rather than the
   author's conversation. Give them the requirement, the acceptance
   examples, the candidate revision and the evidence, and nothing that
   argues for a verdict.
2. **Review against the requirement.** For each acceptance example, does the
   candidate meet it, and is there evidence? Are the required checks
   meaningful, recorded for this revision and passing? Look for changes
   outside the task, unrelated edits, credentials or restricted material,
   and documentation that no longer matches.
3. **Record findings** with `blocking` set when an acceptance example is not
   met, a check is wrong or missing, a risk is unhandled or a contract rule
   is broken. Other findings are not blocking and become tasks.
4. **Return or approve.** With blocking findings open, the verdict is
   `changes` and the task returns to the author. The author fixes them in a
   new candidate; checks and review then apply to that revision. A reviewer
   may re-review only a small, bounded change, but records a new review for
   the new revision.
5. **Validate the integrated candidate**: when the candidate will be merged
   with other work, run the required checks on the merged result, because a
   change in the base can break a change that passed alone. If the merged
   result differs from the candidate in more than the task and handoff
   folders, it is a new candidate. Otherwise record it in
   `candidate.integrated` with the output of
   `tools/kit.py integrated CANDIDATE REVISION` as its evidence.
6. **Mark the task reviewed** once a review of this revision approves it and
   its required checks pass. Done when `tools/kit.py check-task FILE` passes
   in state `reviewed` (rules `REVIEW` and `CHECKS`).
