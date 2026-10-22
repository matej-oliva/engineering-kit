# Glossary

[Guide](README.md) · The words this guide and the kit use, in plain terms.

| Term | Meaning |
| --- | --- |
| Acceptance boundary | Where success must be observed for a task to count as done, such as `merged` or `production`. Each project lists its own, weakest first. |
| Acceptance example | A concrete, observable example of success, written before any work, such as "`tool --quiet sync` prints nothing and exits 0". |
| Adopt | Install the kit into a project. |
| Agent | A program, usually built on an AI model, that reads instructions and changes code or runs commands on someone's behalf. |
| Base | The version of the code that work started from; a bug's failing test is run on it to show the bug exists. |
| Blast radius | Who and what would be affected if a risky step goes wrong. |
| Candidate | The one exact version of the code, such as a commit, that checks and reviews examine. Any later edit makes a new candidate. |
| Check | Something that must pass, such as the test suite, recorded with the version it ran on and its result. |
| Commit | One saved, named version of a project's files in Git, identified by a code such as `9f1c2ab`. |
| Contract | The kit's 18 rules, in `CONTRACT.md`. |
| Contributor | Anyone besides the author who changed the candidate or recorded its evidence; none of them may approve it. |
| Decision owner | The person who decides what a task must achieve and answers the questions that are theirs. |
| Deliberate fault | A copy of the kit with one safety check broken on purpose. The kit's tests must catch every one before a release. |
| Digest | A short fingerprint of a file's exact contents, computed with SHA-256; changing one byte changes it. |
| Door | Whether a risky step can be undone: two-way means the rollback restores the exact earlier state, one-way means something cannot be put back. |
| Effect | A change outside the code itself, such as a deployment, a data migration or a permission change. |
| Entry block | The short marked text the kit adds to each agent instruction file, pointing at the contract. |
| Exception | A recorded, approved decision that a project relaxes one rule that is not fixed, with its scope, reason, approver and date. |
| Falsifiable cause | A possible cause of a bug stated so that one observation could rule it out. |
| Fixed rule | A rule no exception can relax, such as `CHECKS`. |
| Guide | This documentation, installed at `.engineering-kit/kit/guide/`. |
| Handoff | A short Markdown note left when work stops early: where things stand, what is proven, what is open, and one next action. |
| Instruction file | A file an agent reads when it starts, such as `AGENTS.md`. |
| Integration | An optional adapter that installs extra files, such as skills, the `kit` command or a review template. |
| Journal | Saved copies of files while an apply runs, so `recover` can undo an interrupted write. |
| Launcher | The `kit` file at the project root that makes every command `python3 kit COMMAND`. |
| Lock | `.engineering-kit/lock.json`: which release is installed, from where, and the digest of every file written. |
| Manifest | `RELEASE.json`, the list of every file a release installs with its SHA-256 digest. |
| Merge | Bringing a reviewed change into the project's main line of work. |
| Permission | What an integration declares it may write. A project grants it in `project.json`. |
| Plan digest | A short code that identifies a previewed change; `--plan` applies only that exact change. |
| Procedure | One of twelve step lists, such as "Diagnose a defect", each ending in a result someone can check. |
| Process files | Task records, handoffs, `project.json` and the lock: files that describe the work, not the product. A merge may change them without changing what was reviewed. |
| Profile | A kind of work defined by the project, such as `change` or `defect`, that sets the required checks and whether review and release apply. |
| Project configuration | `.engineering-kit/project.json`: the project's own facts, checks, profiles, boundaries, authority and rules. |
| Release | A published version of the kit, a Git tag such as `v1.2.0`, which never changes once published. |
| Review | An approval of the exact candidate by someone other than its author. |
| Revision | A version: of the code, usually a commit, or of a task's requirement, each time it changes. |
| Rollback | Returning to the state before a change, by a way recorded in advance. |
| Skill | A small file an agent loads by itself when a request matches its description; the kit offers one per procedure. |
| SPDX identifier | The standard short name of a licence, such as `MIT`, used in `licensed:MIT`. |
| Staging | A copy of the live system used to try a change before production. |
| Stricter applies | Where the project's own instructions and the kit's contract disagree, the one that demands more wins. If it is unclear which demands more, ask the decision owner. |
| Task record | One JSON file per task holding its requirement, plan, candidate, checks, reviews, effects, release and verification. |
| Verification | Evidence that the result works at the acceptance boundary, recorded with the version it observed. |
