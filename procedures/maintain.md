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
   rules are for judgment. Delete a rule that changed nothing.
5. **Measure before you keep or remove** a tool, rule or integration: how
   often it is used, what it caught and what it costs. A claim that has not
   been measured stays labelled as unproved.
6. **Give postponed ideas a trigger**: a check that fails or a procedure step
   that runs when "later" arrives. Otherwise decide now.
7. **Offer reusable lessons to the kit** with their provenance and rights
   (rule `LESSON`). Keep project secrets, private data and restricted
   material out of anything you offer.
