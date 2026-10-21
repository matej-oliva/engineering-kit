# Quick start

[Guide](README.md) · You need Git and Python 3.11 or newer. A private kit
repository also needs this machine to be signed in to an account that can
read it. The kit's tests run on Linux, on Windows Server and on macOS; the
[supported environments](../README.md#supported-environments) list exactly
which versions. Desktop Windows has not been tested.

## 1. Install the kit

Clone the newest release once, anywhere outside your project, then run its
tool from your project's root folder. The project may be new or existing.

```sh
git clone --depth 1 --branch vX.Y.Z KIT_ADDRESS ~/engineering-kit
cd PATH/TO/YOUR/PROJECT
python3 ~/engineering-kit/tools/kit.py adopt --with launcher --with agent-skills
python3 ~/engineering-kit/tools/kit.py adopt --with launcher --with agent-skills --apply
```

On Windows, in PowerShell, use `py` and backslashes:

```powershell
git clone --depth 1 --branch vX.Y.Z KIT_ADDRESS $HOME\engineering-kit
cd PATH\TO\YOUR\PROJECT
py $HOME\engineering-kit\tools\kit.py adopt --with launcher --with agent-skills
py $HOME\engineering-kit\tools\kit.py adopt --with launcher --with agent-skills --apply
```

`KIT_ADDRESS` is where your kit repository lives, and `vX.Y.Z` is the newest
release tag listed there. To install the newest release without looking up
its number, give the address to `adopt`: `adopt KIT_ADDRESS --apply`.

The first `adopt` only previews. Read the list: it adds the
`.engineering-kit/` folder, a short marked block in `AGENTS.md`, the `kit`
launcher at the root and one skill per procedure. Your own text in
`AGENTS.md` stays byte for byte. Add `--with claude-code`, `--with copilot`
or `--with gemini` for the instruction files those agents read.

## 2. Describe your project

Open `.engineering-kit/project.json`. Replace every value that starts with
`kit-placeholder:` with your project's facts: its name and scope, the command
that runs its tests, what `merged` means here and who decides. An agent can
fill it in for you from the repository; review the result.
[Customize your project](customize.md) explains each field.

```sh
python3 kit check
```

`check` lists what is still missing. Each line names a rule from
[`CONTRACT.md`](../CONTRACT.md), or `FORMAT` when a file cannot be read as a
record yet, for example because a placeholder remains. When it says the
project passes, commit the new files like any other change. The kit never
commits for you.

## 3. Run your first task through it

Ask your agent for a change as usual. Because `AGENTS.md` now points at the
contract, it writes a task record in `.engineering-kit/tasks/`, for example
`T-1.json`, and moves it through the stages. Check it at any point:

```sh
python3 kit check-task .engineering-kit/tasks/T-1.json
```

A refusal names the rule it enforces, such as `CHECKS` when a required check
has not passed on the exact revision under review. Fix the record or the
work, not the checker. The kit's own repository, not your installed copy,
holds a complete worked example in `examples/walkthrough/`: a defect taken
from its report to a closed task.

## Next

- [Everyday use](everyday.md) for updates, rollback and removal.
- [How it fits together](how-it-fits.md) for what each file is for.
