# Maintain and learn

Use when closing a task, after an incident, and when a dependency or tool
needs a decision.

1. **Make the documentation current.** Pages that describe the system say
   what is true now; dated history belongs in a changelog or change record.
   Record `documentation.updated`, or `documentation.none` with the reason
   (rule `DOCS`).
2. **Close only at the acceptance boundary.** A task is closed after it is
   verified, or as `cancelled` or `failed` with the reason in its record.
3. **Give every finding an owner and a decision.** Incidents, dependency
   advisories and review findings that were not blocking become tasks. A
   dependency finding is fixed, removed, or accepted with a reason and the
   date it is reviewed again.
4. **Turn repeated mistakes into checks.** When a mistake could have been
   caught mechanically, add a check, and show it fails on the real past
   mistake before relying on it; its message says what to do instead. Prose
   rules are for judgment. Delete a rule that changed nothing. When existing
   work already breaks the new check, record today's count for each file as
   a baseline that may fall and never rise, with a new file starting at
   zero, instead of exempting old work or postponing the check; lower the
   baseline whenever a count falls. The baseline is a proposal from one
   project.
   At the retrospective, group recurring review comments by cause. For a
   recurring mechanical mistake, assign an owner to turn one real example
   into a failing lint or test case and verify a valid example passes.
   Retire the duplicate review reminder once the check covers it.
   Keep a small fixture with a planted violation for each lint rule the
   project relies on. Run the configured linter with the project's actual
   settings and assert the expected rule ID and location. Fail the canary
   if that diagnostic disappears, even if another rule still reports.
5. **Measure before you keep or remove** a tool, rule or integration: how
   often it is used, what it caught and what it costs. A claim that has not
   been measured stays labelled as unproved.
6. **Give postponed ideas a trigger**: a check that fails or a procedure step
   that runs when "later" arrives. Otherwise decide now.
7. **Offer reusable lessons to the kit** with their provenance and rights
   (rule `LESSON`). Keep project secrets, private data and restricted
   material out of anything you offer.
8. **Check module depth at a regular team retrospective.** Pick one module
   with repeated fixes or changes that ripple into callers. Trace a recent
   change through its public interface. Which decisions must callers repeat,
   and could the module hide them behind one operation? Record a caller and
   test for a proposed improvement, or the reason to keep the boundary.
   Revisit the example at the next retrospective.
