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
   one that a single session can do. When the next step needs someone else,
   such as a fresh reviewer or the owner, that hand-over is the step.
2. **Describe now, not the session.** Rewrite the handoff in place instead of
   appending history.
3. **Match the task record.** The handoff's state equals the task's state.
4. **Leave long work readable.** Work that must outlive the session is
   started so its result is written where the next session will look, and
   the handoff names that place.
5. Done when `tools/kit.py check` passes (rule `HANDOFF`).

## Resume

1. Read the handoff, then the task record, then run `tools/kit.py check`.
2. **Treat the handoff as a claim.** Confirm the evidence the next action
   depends on: the candidate revision exists, its checks still pass, and no
   one changed the work since.
3. **Continue with the next action** within the authority the handoff
   records, without asking again for what is already decided. Stop for
   anything outside that authority.
