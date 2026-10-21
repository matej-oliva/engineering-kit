# Engineering kit guide

This guide is for the people who work in a project that uses the kit. It
explains what the kit does, how to run it day to day, how to fit it to your
project and what to do when something goes wrong. Agents read the contract
and the procedures instead; this guide links to them where they hold the
exact steps.

Everything here is plain Markdown with pictures stored beside it, so it reads
the same in any Markdown viewer, offline, from the copy installed in your
project at `.engineering-kit/kit/guide/`. It always matches the installed
release: an update replaces it with the guide of the new release.

## What the kit is

The kit is a small, shared way of taking work from an idea to verified
delivery. It gives your project:

- a **contract** of 18 rules, each saying what enforces it
  ([`CONTRACT.md`](../CONTRACT.md));
- **procedures** for each stage of the work
  ([`procedures/`](../procedures/understand.md));
- **records**: one JSON file per task and one Markdown handoff per stopped
  task, in folders your project chooses ([`RECORDS.md`](../RECORDS.md));
- a **checker** that refuses a record claiming more than its evidence shows;
- optional **integrations** that connect all this to your agents, your Git
  host and your command line.

Your project keeps its own language, framework, design system, agents, Git
host and deployment. The kit never runs your project's commands; it reads
the records your work leaves.

## When it is useful

Use it when more than one person or agent works on a project over time, and
you want each change to show what was asked, what was checked, who reviewed
it and where it was verified. It is less useful for a one-off script nobody
will maintain: the records cost a few minutes per task.

## How work moves

![Six stages from Understand to Maintain, each leading to the next, with a
handoff whenever work stops early](images/lifecycle.svg)

In words: every task passes six stages in order. **Understand** records the
problem and at least one acceptance example. **Design** chooses a delivery
profile, the risks and how to recover. **Implement** produces one exact
candidate revision and runs its checks. **Review** has someone other than
the author approve that revision. **Release** applies it with authority and
observes it where acceptance is judged. **Maintain** closes the task with its
documentation and lessons. A defect starts with a reproduction, and work that
stops early leaves a handoff the next person resumes from. The task record's
`state` field follows the same order: `proposed`, `accepted`, `in_progress`,
`candidate`, `reviewed`, `released`, `verified`, `closed`.

## Read next

| If you want to | Read |
| --- | --- |
| install the kit or check your first task | [Quick start](quick-start.md) |
| run checks, update, roll back or remove | [Everyday use](everyday.md) |
| understand the contract, records, integrations and releases | [How it fits together](how-it-fits.md) |
| fit the kit to your project | [Customize your project](customize.md) |
| fix a refusal, a conflict or an interrupted update | [Troubleshooting and recovery](troubleshooting.md) |
| keep the kit current or send a lesson back | [Maintenance and contributions](maintenance.md) |

The commands in this guide use the short form `python3 kit COMMAND`, which
the `launcher` integration installs at your project root. On Windows type
`py kit COMMAND`. Without the launcher, type
`python3 .engineering-kit/kit/tools/kit.py COMMAND` instead; everything
else is the same.
