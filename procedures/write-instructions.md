# Write instructions for people and agents

Use when you write or change a project rule, an agent instruction file or a
procedure. Adapted from the `writing-for-agents` skill in `mattpocock/skills`,
MIT licensed; see `THIRD_PARTY_NOTICES.md`.

1. **Pay for context only where it changes behaviour.** Anything always
   loaded, such as an instruction file or a tool description, costs attention
   in every session. Put material that only some tasks need behind a
   pointer: one always-loaded line that names the material and when to read
   it.
2. **Order by when the reader needs it**: the steps first, each ending in a
   done-when the reader can check; then reference grouped by concept; then
   material for rare cases in a separate file named by the step that needs
   it.
3. **Keep one source of truth.** A rule lives in one place and others point
   to it. A configuration file, a script's help or a test already states its
   facts; write down only what reading them cannot reveal, such as the
   reason or the trap.
4. **Prefer a check to a rule.** A mechanical rule, such as a path, a format
   or a forbidden pattern, belongs in a check. Label every rule with how it
   is enforced (rule `ENFORCEMENT`).
5. **Say what to do.** State the behaviour you want. Keep a prohibition for a
   hard safety boundary, and pair it with what to do instead.
6. **Delete what changes nothing.** A sentence the reader already follows
   without it is noise; so is a rule whose incident a check now catches.
   Remove whole sentences rather than trimming words.
