# First run: create the repository's backlog

Use this once in each repository that adopts the work-cycle integration,
before any other task, and again when its owner asks to rebuild the backlog.
It interviews the owner and writes the backlog as kit task records. It
implements nothing: every task it writes waits for its own session.

The work cycle reads the backlog from these records alone. An external
tracker, where the project has one, is a reference inside a task record and
never a second source of state.

## Steps

1. **Check the kit.** Run `python3 kit check` (or `py kit check` on Windows,
   or `python3 .engineering-kit/kit/tools/kit.py check` without the
   launcher). Fix what it refuses before you continue.
2. **Ask whether the repository is shared.** One question: do colleagues
   commit to this repository? If yes, run
   `python3 .kit-cycle/cycle.py exclude` now, before writing any record. It
   lists the kit's files, the task and handoff folders and `.kit-cycle/` in
   Git's local exclude file, which is never committed, so colleagues see
   none of them. Read what it reports: a file Git already tracks stays
   visible, and so does an entry block in a tracked instruction file. In a
   shared repository choose instruction integrations whose files are local
   to you, and tell the owner about every tracked file it names.
3. **Interview the owner, one question at a time.** Give each question your
   recommended answer, so a short yes accepts it, and look facts up in the
   repository yourself instead of asking for them. Cover, in this order:
   - what the project is for and what it does not cover;
   - the open work the owner knows of, one item per answer, with what done
     looks like for each;
   - which commands check a change (tests, lint, build), so each becomes a
     check with a command in `project.json`;
   - which branches are protected besides the default branch;
   - which paths need more attention in review: `owner-only` paths such as
     release, deployment or access settings, and `sensitive` paths such as
     data migrations or public interfaces;
   - where the repository is hosted, if `git remote get-url origin` does not
     say (GitHub, a GitHub Enterprise server, GitLab or Azure DevOps);
   - whether an external tracker such as Jira holds any of the items, and
     its reference for each.
   Stop the interview when the owner says so; unanswered items stay open
   questions in their task records.
4. **Write the configuration.** Add the answers to `.engineering-kit/project.json`:
   the checks and their commands, and a `cycle` object:

   ```json
   "cycle": {
     "remote": "origin",
     "protected": ["release"],
     "paths": {"owner-only": [".gitlab-ci.yml", "deploy/*"], "sensitive": ["migrations/*"]}
   }
   ```

   Add `"host": "github"`, `"gitlab"` or `"azure"` when the remote's address
   does not name its service, and `"default_branch"` when Git cannot tell it.
   Paths are matched with shell-style patterns against each changed path;
   the most demanding class any path falls in labels the review request.
5. **Write one task record per item.** Use `templates/task.json` from the
   installed kit and the next unused ID. A task the owner described but has
   not accepted stays `proposed`. A task with a decision owner, acceptance
   examples and a profile can be `accepted`; add `"next_actor": "agent"`
   only when the owner agrees that the task runner may take it unattended,
   and `"next_actor": "owner"` while it waits for them. Put an external
   tracker reference in the requirement's problem text.
6. **Check again.** Run `python3 kit check` until it passes, then show the
   owner the list of tasks with their states and next actors.
7. **Set up the cycle with the owner.** Install the guards with
   `python3 .kit-cycle/cycle.py guards install`, and register the
   repository with `python3 .kit-cycle/cycle.py register`. The guide in
   `.kit-cycle/guide.md` covers the runner's settings and the edit guard.

## Done when

`kit check` passes, every item the owner named is a task record or an open
question in one, and the owner has seen which tasks the runner may take.
