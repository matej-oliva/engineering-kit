# Diagnose a defect

Use when software behaves incorrectly. Diagnosis alone authorizes no fix and
no retry of an effect. Adapted from ideas in `mattpocock/skills` and
`backnotprop/pstack`, both MIT licensed; see `THIRD_PARTY_NOTICES.md`.

1. **Capture the symptom before a theory**: expected and actual behaviour,
   revision, input and environment. Keep the original evidence.
2. **Make one reproducer anyone can run.** Start from the failing command or
   interaction and remove input until the smallest example still fails for
   the reported reason. A missing tool, credential or access path is a setup
   failure, not a reproduction. If the real symptom cannot be reproduced
   safely, record that gap instead of experimenting on production.
3. **Rank falsifiable causes** for a defect that is not obvious: three to
   five, each with the observation that would rule it out. Change one
   variable at a time. After two fixes built on the same premise fail, test
   the premise itself. When a check passes or fails unexpectedly, test the
   way you observe before the system.
4. **Write the regression check first**, at the smallest public boundary that
   shows the failure: a command with its arguments, a request, or a sequence
   of user actions. Test what a caller observes. Derive the expected result
   independently. Replace only external boundaries such as the network, the
   clock or privileged execution. Done when the check fails on the base
   revision for the reported reason.
5. **Make the smallest fix** that turns it green, and add one nearby case
   that distinguishes the cause from the symptom.
6. **Clean up and record.** Remove temporary diagnostics and experiments.
   Record `reproduction` with the check, the base revision, its failing
   result and the candidate's pass (rule `REPRODUCE`).
