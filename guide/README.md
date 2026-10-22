# Engineering kit guide

The complete documentation of the engineering kit: what it is, how to use
it, what it tells agents, and how it works inside. It is plain Markdown
with pictures stored beside it, so it reads the same in any Markdown viewer,
offline, from the copy installed in your project at
`.engineering-kit/kit/guide/`. It always matches the installed release: an
update replaces it with the guide of the new release.

**New here?** Read [What the kit is, and what you gain](what-is-it.md)
first. It needs no prior knowledge.

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

## Using the kit

| If you want to | Read |
| --- | --- |
| understand what the kit is and why to use it | [What the kit is](what-is-it.md) |
| install the kit or check your first task | [Quick start](quick-start.md) |
| run checks, update, roll back or remove | [Everyday use](everyday.md) |
| fit the kit to your project | [Customize your project](customize.md) |
| fix a refusal, a conflict or an interrupted update | [Troubleshooting and recovery](troubleshooting.md) |
| keep the kit current or send a lesson back | [Maintenance and contributions](maintenance.md) |

## For agents, explained for people

| If you want to know | Read |
| --- | --- |
| every instruction agents receive, in plain words | [What agents are told](agents.md) |
| the twelve skills and when agents use them | [Skills](skills.md) |

## How it works

| If you want to know | Read |
| --- | --- |
| the parts and who owns which file | [How it fits together](how-it-fits.md) |
| commands, formats, algorithms, integrity and security | [Technical reference](reference.md) |
| how it is tested, in numbers and charts | [Facts and figures](figures.md) |
| what a word means | [Glossary](glossary.md) |

The commands in this guide use the short form `python3 kit COMMAND`, which
the `launcher` integration installs at your project root. On Windows type
`py kit COMMAND`. Without the launcher, type
`python3 .engineering-kit/kit/tools/kit.py COMMAND` instead; everything
else is the same.
