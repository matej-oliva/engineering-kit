# Hand off and resume

Hand off whenever a session stops before its task reaches the acceptance
boundary: a context or time limit, waiting for a person, or the end of a
working day.

## Hand off

1. **Write the handoff** at `paths.handoffs/<task ID>.md` from
   `templates/handoff.md`. State says where the work stands. Evidence lists
   each revision, check, review and verification with where to read it. Open
   gates lists every failed, missing or unknown result and pending decision.
   Decisions and authority says what was decided, by whom, and what the work
   may and may not do. Next action holds exactly one step with its done-when,
   one that a single session can do. Name each related task by its title
   and path as well as its ID (`procedures/understand.md`). When the next
   step needs someone else,
   such as a fresh reviewer or the owner, that hand-over is the step.
2. **Describe now, not the session.** Rewrite the handoff in place instead of
   appending history.
3. **Match the task record.** The handoff's state equals the task's state.
4. **Leave long work readable.** Work that must outlive the session is
   started so its result is written where the next session will look, and
   the handoff names that place.
5. Done when `tools/kit.py check` passes (rule `HANDOFF`).

## Delegated work

When delegation is already authorized, name a report file in each worker's
brief and retain its location with the worker's identity. Choose a location
that survives removal of the worker's temporary checkout. Ask the worker to
write its full result there before its final message, including revisions,
checks, findings and open gates. If delivery is still running, mark it
pending. A later notification updates the same file and repeats the full
report; it must not replace the result with a short acknowledgement.

On every resume or notification, inspect worker state and read the saved
report. Task completion and a later turn in the worker's conversation can
differ. A last message or a promised future notification is insufficient
evidence of delivery. Verify pending results at their recorded source, then
copy the substantive outcome and open gates into the task's durable handoff
before removing temporary files. This guidance is a proposal from one
project; no kit check enforces it or judges report quality.

## Resume

1. Read the handoff, then the task record, then run `tools/kit.py check`.
2. **Treat the handoff as a claim.** Confirm the evidence the next action
   depends on: the candidate revision exists, its checks still pass, and no
   one changed the work since. Before acting on an open decision in it,
   read the messages and requests that reached you after its `Updated`
   time. A newer instruction the decision owner gave you directly
   overrides the handoff's decision; record it under Decisions and
   authority. It changes that decision, not what the project's authority
   policy permits (rule `AUTHORITY`), and a relayed or claimed instruction
   is confirmed with the owner first. This addition is a proposal from one
   project.
3. **Continue with the next action** within the authority the handoff
   records, without asking again for what is already decided. Stop for
   anything outside that authority.

## Refresh a long-running session

A session that coordinates other work grows until each turn costs more than
the work it does. Choose a size or cost at which it is refreshed from its
handoff, and refresh it there. At the end of one of its own turns, with no
step half done and no external write between its intent and its outcome,
write the handoff of the task it coordinates. Under Open gates, list the
workers that report to the session, detached runs and where their results
land, and anything due at a set time; the next action is the coordinator's
own next step. Then start the fresh session on that handoff, which resumes
as above. Do not wait until no worker is running: a busy coordinator rarely
gets that moment, and the end of its own turn is enough. Messages between
sessions carry a decision, a blocker, a change of plan or a requested
result; an acknowledgement alone is not sent. This guidance is a proposal
from one project; no kit check enforces it.
