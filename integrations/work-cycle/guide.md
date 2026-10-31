# Work cycle guide: Windows with WSL2 behind a TLS-inspecting proxy

The work-cycle integration brings one development cycle to every repository
on a machine: a backlog of kit task records, a task runner that agents work
through during working hours, delivery through a review request that a
person merges, and guards that keep agents off the protected branches. This
page sets it up on a Windows laptop with WSL2 whose network goes through a
TLS-inspecting proxy such as ZScaler. Everything except the proxy section
applies to macOS and Linux too.

## What it never does

- It never merges a request and never pushes a default or protected branch.
- It never creates an operating-system scheduler entry. The runner is a
  loop you start in a terminal; it stops by itself when the working-hours
  window closes. Enterprise policy that removes Task Scheduler entries
  cannot remove it, and closing the terminal stops it.
- It never stores or prints a credential. `gh`, `glab` and `az` keep their
  own sign-ins, made with the accounts your employer approves.

## 1. Choose one side per repository

Run the runner and the repositories it serves on the same side.

- **Windows:** Python 3.11 or later from python.org (`py -3 --version`), Git
  for Windows, and the review tools in Windows. Keep repositories on a
  Windows drive.
- **WSL2:** Python 3.11 or later and Git inside the distribution, and the
  review tools installed there. Keep repositories in the Linux file system,
  such as `~/src`, not under `/mnt/c`, where Git is slow and file modes and
  line endings mix with Windows tools.

One runner serves every repository registered on its side. Repositories on
the other side need a runner of their own, with its own home folder.

## 2. Trust the proxy's certificate

A TLS-inspecting proxy presents its own certificate authority. Tools that do
not trust it fail with certificate errors. Never turn verification off
(`http.sslVerify false`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `--insecure`);
add the proxy's root certificate instead. Your IT department publishes it,
or export it from the Windows certificate store as a Base-64 `.cer` file.
It is a public certificate, not a secret.

- **Git for Windows:** `git config --global http.sslBackend schannel` uses
  the Windows store, which already holds the proxy's root.
- **WSL2:** copy the certificate to
  `/usr/local/share/ca-certificates/proxy-root.crt` and run
  `sudo update-ca-certificates`. Git, `gh` and `glab` then trust it.
- **`az` (both sides):** it uses its own bundle. Point it at one that holds
  the proxy's root: `REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt`
  in WSL2, or a bundle file you build on Windows.
- **Agent clients built on Node.js:** set `NODE_EXTRA_CA_CERTS` to the
  certificate file.

Check with `git ls-remote` against each host before you continue.

## 3. Sign in the review tools

Install only the tools your hosts need and sign in with your work account:

| Host | Tool | Sign in |
| --- | --- | --- |
| GitHub.com | `gh` | `gh auth login` |
| GitHub Enterprise server | `gh` | `gh auth login --hostname HOST` |
| GitLab, including self-hosted | `glab` | `glab auth login --hostname HOST` |
| Azure DevOps | `az` with the `azure-devops` extension | `az login`, then `az devops configure --defaults organization=URL project=NAME` |

Delivery tells the host from the remote's address. A GitHub Enterprise or
GitLab server whose name does not say so gets `"host"` in the `cycle`
object of `project.json`. A missing tool is not an error: delivery still
pushes the branch and records a compare address you open by hand.

## 4. Adopt the kit with the integration

Clone a release as the kit's README shows and adopt with the integration:

```sh
python3 ~/engineering-kit-1.4.0/tools/kit.py adopt --with launcher --with agent-skills --with work-cycle
python3 ~/engineering-kit-1.4.0/tools/kit.py adopt --with launcher --with agent-skills --with work-cycle --apply
```

A project that already uses the kit adds `"work-cycle": {"grant": [...]}`
under `integrations` in `project.json`, with every permission the
integration declares, and runs `python3 kit update --apply`. Then ask your
agent to follow `.kit-cycle/first-run.md`. It interviews you, writes the
backlog as task records and, in a repository you share with colleagues,
keeps every kit file out of their view through Git's local exclude file.

## 5. Configure and start the runner

`python3 .kit-cycle/cycle.py register` adds the repository to the runner's
settings in `~/.kit-cycle/runner.json` (on Windows `%USERPROFILE%\.kit-cycle`).
Set `KIT_CYCLE_HOME` or `--home` to keep it elsewhere. Edit that file once:

```json
{
  "kit": "cycle-runner/1",
  "repositories": [{"name": "billing", "path": "C:/src/billing"}],
  "window": {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "17:00"},
  "agent": {"command": ["claude", "-p", "Follow the instructions in {prompt_file}"], "timeout_minutes": 120},
  "minimum_minutes": 20,
  "poll_minutes": 10
}
```

For the Codex command line use `["codex", "exec", "Follow the instructions
in {prompt_file}"]`. Pass the prompt as a file: Windows command shims
mangle multi-line arguments. Other placeholders are `{task}`, `{repository}`,
`{worktree}`, `{task_file}`, `{handoff}`, `{branch}` and `{base}`; the same
values reach the command as `KIT_CYCLE_*` environment variables. The agent
client's own permission settings decide what it may do without asking; set
them before the first unattended run.

Start it at the beginning of the working day and leave the terminal open:

```sh
py .kit-cycle\cycle.py run        # Windows
python3 .kit-cycle/cycle.py run   # WSL2
```

The runner takes the oldest ready task across every registered repository:
a task record in `accepted` or `in_progress` with `"next_actor": "agent"`.
It claims it, makes a fresh worktree on a new branch `kit/ID-TIME` from the
default branch, and runs the agent command there with a time limit that
ends before the window does. When the agent stops without a handoff, the
runner writes one that says the outcome is unknown. It records each run in
`runs/` in its home folder and stops when the window closes, or after one
task with `--once`. Each task runs at most once per runner session: a task
the agent leaves ready, or a run that failed or timed out, waits for the
next start, so a failing agent command cannot repeat all day. While the
laptop sleeps the runner pauses with it.

- `cycle.py queue` shows the queue and claims.
- `cycle.py claim ID` keeps the runner off a task you work on yourself for
  eight hours; `cycle.py release ID` gives it back.
- Worktrees stay in `worktrees/` until you remove them with
  `git worktree remove`, so unfinished work is never lost.

## 6. Deliver

The agent, or you, delivers from the task branch:

```sh
python3 .kit-cycle/cycle.py deliver --task ID
```

It runs the task profile's checks that have commands, refuses a protected
branch, pushes the branch and opens a pull or merge request whose title
starts with its class: `[routine]`, `[sensitive]` or `[owner-only]`, from
the `paths` patterns. It also adds the class as a label when the label
can be set: GitHub and GitLab after opening the request, Azure DevOps as it
opens it, opening it without the label when that fails. Each delivery is recorded under the
repository's Git folder in `kit-cycle/deliveries/`, never in a commit.

## 7. Guards

`python3 .kit-cycle/cycle.py guards install` writes a pre-push hook into
the repository's Git folder that refuses any push to a protected branch,
including from every worktree. It refuses when `core.hooksPath` points
elsewhere and prints the line to add to that hook instead.

The edit guard runs before each shell command an agent client starts. It
refuses in-place stream edits (`sed -i`, `perl -i`), commands that bypass
Git hooks, force pushes and pushes to a protected branch. For Claude Code,
add it to `.claude/settings.local.json`, which stays on your machine. The
example is for Windows; in WSL2, macOS and Linux write `python3` instead
of `py`:

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
  {"type": "command", "command": "py .kit-cycle/cycle.py guard-edit"}]}]}}
```

Any client that sends the same JSON payload (`tool_input.command`) and reads
exit status 2 as a refusal can use the same command. It allows what it
cannot read; the pre-push guard still refuses protected pushes.

In a repository you share, the runner's worktrees hold only committed
files, so neither `.kit-cycle/` nor `.claude/settings.local.json` is there.
Register the edit guard in the client's user settings instead
(`~/.claude/settings.json` for Claude Code), with the absolute path of the
registered checkout's script, such as
`py C:/src/billing/.kit-cycle/cycle.py guard-edit`. The prompt the runner
writes names the kit files and procedures in the registered checkout. The
pre-push guard needs nothing: every worktree shares the checkout's hooks.

## Removing it

Stop the runner, run `cycle.py guards remove`, remove the integration from
`project.json` and run `python3 kit update --apply`. Delete the runner's
home folder when no repository uses it.
