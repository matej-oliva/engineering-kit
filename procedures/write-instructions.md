# Write instructions for people and agents

Use when you write or change a project rule, an agent instruction file or a
procedure. Adapted from the `writing-for-agents` skill in `mattpocock/skills`,
MIT licensed; see `THIRD_PARTY_NOTICES.md`.

1. **Pay for context only where it changes behaviour.** Anything always
   loaded, such as an instruction file or a tool description, costs attention
   in every session. Put material that only some tasks need behind a
   pointer: one always-loaded line that names the material and when to read
   it.
   Give the local path and a specific trigger, such as “When changing a
   file format, read docs/compatibility.md.” Retrieve that section when the
   trigger matches. When it changes a decision, quote the governing sentence
   and cite its location so a reviewer can check the interpretation.
2. **Order by when the reader needs it**: the steps first, each ending in a
   done-when the reader can check; then reference grouped by concept; then
   material for rare cases in a separate file named by the step that needs
   it.
3. **Keep one source of truth.** A rule lives in one place and others point
   to it. A configuration file, a script's help or a test already states its
   facts; write down only what reading them cannot reveal, such as the
   reason or the trap. A lesson every contributor needs goes into the
   repository, where its procedure lives: a check, the tool's own message
   or that procedure's page. One agent client's private memory or settings
   reach no other client or person, and nobody reviews them, so they go
   stale unseen; keep there only what is personal to that client. The
   memory part is a proposal from one project.
4. **Prefer a check to a rule.** A mechanical rule, such as a path, a format
   or a forbidden pattern, belongs in a check. Label every rule with how it
   is enforced (rule `ENFORCEMENT`).
   Turn a repeatable multi-step workflow into a deterministic callable
   command. Validate the records it writes and compare the input revision
   before replacing an existing record.
5. **Say what to do.** State the behaviour you want. Keep a prohibition for a
   hard safety boundary, and pair it with what to do instead.
6. **Delete what changes nothing.** A sentence the reader already follows
   without it is noise; so is a rule whose incident a check now catches.
   Remove whole sentences rather than trimming words.
