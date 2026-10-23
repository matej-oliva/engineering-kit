# Grill me

Use only when the user asks for `kit-grill-me` or `grill-me` by name.
Otherwise return to the current task. Adapted from Matt Pocock's `grill-me`
and `grilling` skills at `5beb35b0`, MIT; see `THIRD_PARTY_NOTICES.md`.

The interview builds a shared understanding of a plan, decision or idea.
It is conversation only: read relevant evidence, but write no files and
make no changes. Implementing or recording the outcome needs a separate
request under the project's normal rules.

1. **Map the decisions.** Identify open decisions and their prerequisites.
   The subject need not be software. Keep within the user's scope and narrow
   the interview when they say it is drifting.
2. **Look up facts before asking.** Use available repository evidence,
   connected sources or the web. Ask for preferences and decisions; ask for
   facts only when available sources cannot establish them. State what is
   unknown. Continue with questions independent of pending lookups.
3. **Ask independent questions in rounds.** Ask all currently answerable
   questions together, numbered. A question depending on another answer in
   this round waits for the next. Give concrete options and a recommended
   answer with a reason grounded in the user's situation. Phrase each so
   "yes" accepts the recommendation:

   ```
   Q1. Short title. The question and options, if there are several.

   Recommended: the answer and why.
   ```

4. **Wait and update.** After the user answers, update the decisions and ask
   the next round. Treat "I don't know" as an answer: name evidence or an
   experiment that would resolve it and keep it explicitly unresolved.
   Proposing an experiment does not authorize running it. Challenge answers
   conflicting with earlier decisions, evidence or project boundaries.
5. **Confirm understanding.** When no answerable questions remain, summarize
   the decisions and unresolved items with what would settle them. Ask the
   user to confirm. Finish when they confirm, or stop when asked;
   confirmation of the summary is not permission to implement it.
