# Review and validate

Use when a candidate is ready. The reviewer is not the author.

Use the readiness steps first when preparing that candidate. The stage
guidance below is a proposal from one project;
the checker enforces final acceptance, not review scheduling or report quality.

## Before formal acceptance review

1. **Name the review's purpose.** An optional source-readiness review checks
   the worker's scoped change and focused evidence so an integrator can
   prepare a combined candidate in an isolated checkout. It is not a kit approval:
   keep its report outside the task's `reviews` array and leave the task
   `in_progress` or `candidate`. Record known defects and the downstream
   checks, their owners and their prerequisites. Pending downstream evidence
   does not fail source readiness. A demonstrated source defect still can.
   Preparing that checkout does not authorize a protected-branch merge,
   release or deployment. Projects without delegated work can skip this review.
2. **Complete the evidence packet before requesting acceptance.** Follow the
   evidence owners and stages in the plan. If a prerequisite check or required
   acceptance observation is missing, the candidate is not ready for formal review:
   give the evidence producer one finite checklist and next action. This
   readiness check does not consume a correction round. Do not ask another
   reviewer to reject the same incomplete packet. A `candidate` record still
   needs a result for each required check; use `unknown` with the reason and
   owner for an unrun check, never `pass`. This does not make it `reviewed`.
   Observations assigned to release verification remain there; they are not
   prerequisites for source review or permission to prepare a release.
3. **Make another review useful.** Keep a ledger of finding IDs, severity,
   disposition and supporting evidence. A repeat review needs changed code,
   new evidence or a specific unresolved dispute to decide. Give the reviewer
   the earlier findings and the delta, and ask which findings remain open.
   Resolve a missing tool or observation method before resubmitting. Projects
   choose their correction budget and escalation owner; exhausting a budget
   is not approval. An out-of-scope refinement becomes a proposed task rather
   than expanding this candidate. Do not defer a blocking finding to obtain
   acceptance: it must be resolved, with evidence, before `reviewed`.

For example, a worker changes an asset and passes its focused checks. The
integrator owns a required combined-system check. Source readiness lets the
integrator assemble the candidate and run that check; its result is not a
prerequisite for assembling the candidate that produces it:

```text
worker proof -> source readiness -> integrated candidate -> required checks -> acceptance review
```

If integration changes source, bind checks and formal review to the resulting
revision. A source-ready report never satisfies the `REVIEW` rule. A later
merge or rebase still follows step 5 below. The example is synthetic;
`tests/test_review_stages.py` in the kit's source repository verifies that pending or stale evidence cannot
pass final acceptance. It does not test an agent's adherence to this guidance.

## Formal acceptance review

1. **Choose a fresh reviewer**: another person, or an agent session that did
   not write the change and starts from the task record rather than the
   author's conversation. Give them the requirement, the acceptance
   examples, the candidate revision and the evidence, and nothing that
   argues for a verdict. A handoff is for resuming work: a reviewer who
   reads it checks each claim and does not treat it as evidence. Anyone who
   changed the candidate or recorded its evidence for the author is listed
   in `contributors` and does not review it.
2. **Review against the requirement.** For each acceptance example, does the
   candidate meet it, and is there evidence? Are the required checks
   meaningful, recorded for this revision and passing? Look for changes
   outside the task, unrelated edits, credentials or restricted material,
   and documentation that no longer matches.
3. **Record findings** with `blocking` set when an acceptance example is not
   met, a check is wrong or missing, a risk is unhandled or a contract rule
   is broken. Other findings are not blocking; the reviewer proposes each
   as a new task in state `proposed` for the decision owner.
4. **Return or approve.** With blocking findings open, the verdict is
   `changes` and the task returns to the author. The author fixes them in a
   new candidate; checks and review then apply to that revision. A reviewer
   may re-review only a small, bounded change, but records a new review for
   the new revision.
5. **Validate the integrated candidate**: when the candidate will be merged
   with other work, run the required checks on the merged result, because a
   change in the base can break a change that passed alone. If the merged
   result differs from the candidate outside the process files that
   `RECORDS.md` lists under `candidate`, it is a new candidate. Otherwise
   record it in `candidate.integrated` with the output of
   `tools/kit.py integrated CANDIDATE REVISION` as its evidence, run from
   the candidate's checkout or a clone of the kit, never from the revision
   under judgement. When it reports `UNKNOWN`, such as a kit adopted or
   moved to another source after the candidate, review that kit change
   before you rely on the result.
6. **Mark the task reviewed** once a review of this revision approves it and
   its required checks pass. Put what you examined and reran in the review's
   `evidence`, not in `checks`: recording the author's checks would make you
   a contributor. Done when `tools/kit.py check-task FILE` passes in state
   `reviewed` (rules `REVIEW` and `CHECKS`).
