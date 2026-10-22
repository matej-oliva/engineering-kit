# What the kit is, and what you gain

[Guide](README.md) · Start here if you have never heard of the kit. No
prior knowledge is needed.

## The problem it solves

More and more software is written with AI agents: programs that read a
request, change code and run commands. They are fast, and they can claim
more than they did: "the tests pass" when they ran against an older version,
"it works" when nobody tried it where it matters, "reviewed" when the author
reviewed their own work. People do the same under pressure. When something
breaks a week later, nobody can say what was asked, what was checked, or who
agreed.

## The idea

The kit is a small set of files you add to a project. It does three things:

1. **It tells agents and people how work moves** from a request to a
   verified result, in six stages, and what each stage must leave behind.
2. **It keeps a short written record of every task**: what was asked, how
   success is recognised, which exact version was tested and reviewed,
   where the result was confirmed, and who approved anything risky.
3. **It checks those records.** A small program refuses any record that
   claims more than its evidence shows, for example a test result that
   belongs to a different version of the code.

Think of it as a pilot's checklist and logbook for software work. It does
not fly the plane, and it does not replace skill. It makes the important
steps hard to skip, and leaves a trail anyone can follow.

![A request enters the kit's six stages, which produce a verified change and
a task record; the checker reads the record and refuses claims without
evidence](images/overview.svg)

In words: a request goes through six stages: understand, design, implement,
review, release and maintain. The result is a change that was verified
where it matters, plus a task record that says how. The checker reads the
record and refuses any claim that lacks evidence. Agents learn the stages
from the instructions the kit installs; people can read this guide.

## What you gain

| Without the kit | With the kit |
| --- | --- |
| "Tests pass", but nobody knows on which version | Every check names the exact version it ran on; a result for another version does not count |
| The author reviews their own change | A different person or agent must approve the exact version |
| "Done" means "it worked on my machine" | "Done" means it was observed where it matters: merged, published or in production, as your project defines |
| A risky step, such as a deployment, happens on a guess | It is prepared first: what changes, who approved it, how to undo it |
| A half-finished task is lost when a session ends | A handoff says where things stand and the one next step |
| Each project invents its own process | The same small process works for any language, framework, agent or host |
| Lessons stay in one project | A lesson can be sent back to the kit and reach every project |

## Who it is for

- **People who lead projects** and want to trust what agents report.
- **Developers** who work with agents and want them to follow the same
  steps every time.
- **Agents** themselves: the kit gives them clear instructions, in files
  they already read.

It suits work that several people or agents touch over time. For a
throwaway script it adds more care than the script needs.

## What it is not

- **Not a framework or a library.** Your code does not import it. It is a
  folder of text files and one small Python program.
- **Not a build or deployment tool.** It never runs your tests or deploys
  anything. It reads the records your work leaves.
- **Not tied to one tool.** It works with any programming language, any Git
  host and any agent that reads instruction files.
- **Not a guarantee.** It makes claims specific and checkable. Whether a
  claim is true still depends on the people and tools that made it; see
  [what the checks can and cannot prove](how-it-fits.md#what-the-checks-prove-and-what-they-cannot).

## What is inside

| Part | What it is | Read more |
| --- | --- | --- |
| Contract | 18 short rules, each saying what enforces it | [What agents are told](agents.md) |
| Procedures | 12 step-by-step guides, one per kind of work | [What agents are told](agents.md) |
| Skills | The same 12 procedures, packaged so agents load the right one by themselves | [Skills](skills.md) |
| Records | One JSON file per task, one Markdown handoff per stopped task | [How it fits together](how-it-fits.md) |
| Checker and updater | `kit.py`, one small Python program with no dependencies | [Technical reference](reference.md) |
| Integrations | Optional connections to agents, Git hosts and a short `kit` command | [Customize](customize.md) |
| This guide | What you are reading, installed in every project | [Guide](README.md) |

## How to start

1. [Quick start](quick-start.md): install it in a project in a few minutes.
2. [Everyday use](everyday.md): the handful of commands you will use.
3. [Facts and figures](figures.md): how it is tested, in numbers.
