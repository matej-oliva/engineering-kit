# Design and plan

Use after a task is accepted and before implementation.

1. **Choose the delivery profile** from `project.json` that fits the work's
   risk: a wording fix needs less evidence than a data migration. Done when
   `profile` is set and you know its required checks, and whether review
   and release apply (rule `PROFILE`).
2. **Compare alternatives when the choice is costly to reverse.** Note two
   or three options, their trade-offs and the reason for your choice. A
   decision that is hard to reverse, surprising without its context and the
   result of a real trade-off also gets a short decision record in the
   project's documentation.
3. **Name dependencies, risks and recovery**: how the change is undone and
   what cannot be undone. Done when `plan.risks` and `plan.recovery` say so.
4. **Plan the evidence**: which check proves each acceptance example, and at
   which boundary. For an interface, cover its interaction states (empty,
   loading, error and success), keyboard and screen reader use, and the
   screen sizes the project supports. The project's own design system, not
   the kit, decides how it looks.
5. **Split the work into increments** that each leave the system working and
   can be reviewed alone. Done when `plan.increments` lists them.
6. **Prepare effects** outside the repository, such as deployments, data
   migrations, external services, permission changes or deletion, with
   `procedures/change-preflight.md` before any of them is applied.
