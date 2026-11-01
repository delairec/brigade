Answers what a tick does with the facts it reads, from launching the tasks of a wave to verifying, repairing and rebasing their pull requests, starting waves and pausing them on the quota, and how `brigade scheduler` fires the tick every five minutes.

## What a tick does

A tick builds a snapshot of the facts, plans the actions they call for and applies them, round after round until the
plan is empty or ten rounds have passed. Among those actions, it runs the due studies, as [Studies](Studies.md) says, and launches
each startable task of an open wave as a detached build run, in the worktree it cuts for the task, of `build-task`,
the procedure brigade ships, or of the one the key `build` of the table `[procedures]` of `config.toml` names in its
place, resolved as the argument of `brigade run` is, with the wave and the task as `--wave` and `--task`. It follows the pull request of each task past its launch,
read as the login of the key `cli` of `[forge_accounts]`: the task is recorded `pr_open` when its pull request opens,
`merged` when it merges, `parked` with the reason `pull request closed` when it closes unmerged, and the task's
worktree is removed once its pull request is merged or closed, never while a run holds it. A task is recorded `running`
before its run is spawned, and its launch reuses the branch `task/<slug>/<task>` and its worktree when they exist. On
a project of `FORGE github` the launch fetches the wave branch and cuts the task branch from `origin/<branch>`, its
setup checking that `origin/<branch>` is an ancestor of `HEAD`; a project of `FORGE none` keeps its local wave branch.
An existing task branch that does not descend from that wave branch is rebased onto it before the setup; a rebase
stopped on a conflict is aborted and the tick starts a detached run of the slot `rebase` in the worktree of the task,
with the arguments `task` and `base` and no `pr`, the task staying `running`: once that run ends done, the next tick
launches the build run, and a run that ends blocked parks the task on its question. A
task whose setup fails is recorded `parked` with the reason `setup failed`, its worktree and branch left in place. A
`running` task with no pull request that no live run names in its wave and task, its run rate-limited or a rebase
run ended done aside, is parked, `task.parked` with the reason `run dead: <run>`, the last run naming the task, or `run not started` when no run
names it. An
action that fails is recorded as `tick.action_failed`, with the action, its project, wave and task where it names
them, and the error; the tick applies the actions that follow it, never applies it again in the same tick and undoes
nothing, the next tick planning again from the facts. On the pull request a task
in `pr_open` opened, once every check run completed, at least one unless the project declares `CHECK_RUNS none`, and
for each head once, it runs `brigade verify preflight`,
records its findings in `task.preflighted` and moves the task to `verifying` when no check fails. On a task in
`verifying` whose pull request is open, it starts a fresh detached run of the slot `review` in the task's worktree, of
`verify-pr`, the procedure brigade ships, or of the one the key `review` of `[procedures]` names, with `pr` and `task`
as its arguments, unless a run holds the worktree or a review run of the task already ended at that head other than on
a rate limit; once a `task.verdict` is recorded at the head of the pull request, it moves the task to `verified` on
`pass` and to `changes_requested` on `changes`. A task in `verifying` whose pull request head is no longer the head of
its last `task.preflighted` moves back to `pr_open`, where the preflight of the new head opens the next verification.
A task in `pr_open` whose preflight failed on a finding other than `ancestry` and `checks` moves to
`changes_requested`, those findings as its reason. On an open pull request whose head the last preflight judged, and
when no run holds the task's worktree, a task in `changes_requested` starts a detached run of the slot `remediate`, of
`remediate-pr`, the procedure brigade ships, or of the one the key `remediate` of `[procedures]` names, which answers
through `brigade review context|reply`; a task whose preflight found a failing check starts a detached run of the slot
`build` whose brief carries the build brief of the task and the last 200 lines of the log of each failing check. Each
launch records the task `fixing` and counts one round; a run that ends without a push leaves the task `fixing`, and the
next tick launches it again. A push moves the task back to `pr_open`. Past the `VERIFY_ROUNDS` of the project's
`POLICY`, 2 by default, the task is parked, `task.parked` naming the rounds. A run of the slot `remediate`, `build` or
`rebase` that cannot go on without a ruling pushes nothing and ends on `brigade-end: blocked`, its question on the lines
above: the next tick parks its task, whatever its rounds, `task.parked` naming the run and that question.
A task whose open pull request is behind the branch of its wave, from `pr_open` to `fixing`, is rebased by git when no
run holds its worktree, and waits for the next tick otherwise: under the lock of the project's worktrees, the tick
fetches the wave branch, rebases the worktree onto it and pushes with `--force-with-lease` on the head it read, as the
login of the key `cli` of `[forge_accounts]`, then records `task.rebased`, the head before and after and that login,
and moves the task back to `pr_open`. On a conflict it aborts the rebase and starts a detached run of the slot
`rebase`, of `rebase-on-base`, the procedure brigade ships, or of the one the key `rebase` of `[procedures]` names,
which works through `brigade rebase context|done`; the launch records the task `fixing` and counts no round, and past
the rounds the repair runs spent the task is parked instead.
The waves are the
open waves of the ledger, each with the tasks its `wave.started` names, in that order, read from the project corpus
at the wave's branch; a wave whose pull requests the forge fails to read is skipped, named on stderr, and the tick
serves the others.

## Starting and closing waves

The tick starts a wave, as `brigade wave start <project>` does, for each registered project not `paused` whose
`POLICY` sets `WAVE_START` to `auto`, the default when no `POLICY` names the project, when at least one candidate lies
outside every open wave; the wave takes every candidate, `SLOTS` bounding the live build runs alone, and `ask` leaves
the start to the user. A project whose tasks cannot be read is skipped, named on stderr. An open wave whose branch is
missing has it cut again from the main branch, with no second `wave.started`. A queued task of an open wave that a
live blocker cites is recorded `parked` with the reason `blocked by` and the citing entity. Once every task of a wave
is `merged` or `parked`, the tick records `wave.reported`, its `run` null until the wave-report study exists, and once
the integration pull request of a reported wave is merged, `wave.closed` with its number.

## Quota and forge-account pauses

Any run that finished on the `error_class` `rate_limit`, until its `reset` has passed, pauses every running wave of the
machine: `wave.paused` with the reason `quota` and `resume_at` the first instant after the tick's clock at the hour and
in the timezone of the result's `reset`, or that clock plus 30 minutes when `reset` is null, and the task of a build
run moves to `paused:quota`. A wave started during a quota pause is paused until the same `resume_at`. A
`forge_account.unavailable` of the ledger pauses every running wave, those started after it included, with the reason
`forge_account` and no `resume_at`, until `brigade wave resume`. The tick launches no run of a paused wave. The first tick past
`resume_at` records `wave.resumed` for the wave and resumes the run of each `paused:quota` task as its next segment,
through `resume-argv` with the session of its last segment, or as a fresh launch from its progress file when the
client adapter declares no resume, and moves the task back to `running`.

## Commands

```
brigade tick --once       # one tick, under the lock $XDG_STATE_HOME/brigade/locks/tick.lock
brigade tick --dry-run    # the snapshot and the plan, applied to nothing
brigade tick --loop       # a tick at once, then one every five minutes, until SIGTERM or SIGINT
brigade scheduler install
brigade scheduler status
```

## `brigade tick`

`tick --once` takes the lock without waiting: when another tick holds it, it writes one line naming the lock on stderr,
writes nothing and exits 0. Otherwise it writes the heartbeat `$XDG_STATE_HOME/brigade/tick.json` atomically:
`schema_version`, `ts`, `duration_ms`, `actions_applied` and `actions_failed`. `--dry-run` takes no lock and writes neither the heartbeat nor a tick trail, its records going to the trail of a command. `--loop`
reports each tick on stderr; a signal lets the tick under way finish, then the loop exits 0 with the number of ticks
attempted, stand-downs included. Every mode prints text or, with `--json`, a JSON document.

## `brigade scheduler`

`scheduler install` installs what fires `brigade tick --once` every five minutes, chosen by the `scheduler` key of
`config.toml`, else, without the key or without `config.toml`, by a probe: `systemd` where `systemctl --user
is-system-running` answers `running` or `degraded`, `cron` otherwise. `systemd` writes `brigade.service` and
`brigade.timer` in `$XDG_CONFIG_HOME/systemd/user/`, then reloads the user manager and enables the timer now, and warns, in the `warnings` list of its document and one
line of its text, when `loginctl show-user -p Linger` does not answer `Linger=yes`: without `loginctl enable-linger`
the user manager stops with the last session, and the timer with it; the exit code stays 0; `cron`
replaces the crontab line marked `# brigade scheduler install`, keeping every other line, appends the stderr of each
tick to `$XDG_STATE_HOME/brigade/tick.log` and discards its stdout, the heartbeat keeping the last tick; `loop` installs
nothing and names the `brigade tick --loop` command to keep running. The unit and the cron line run the brigade that
installed them with the `PATH`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME` and `XDG_CACHE_HOME` of the install, escaped for
systemd or quoted for the shell and cron. Run again, it leaves one pair of units or one line. `scheduler status` reports
the scheduler installed or `none`, its unit files or cron line, the next activation of the timer, the last tick read
from the heartbeat, the paused waves with their reason and their `resume_at`, and the parked tasks of the open waves
with their wave and their reason; it resumes no wave. It exits 1 when the last tick is older than `tick_stale_after` of
`config.toml`, in minutes, 15 by default, or when no tick ever ran while a scheduler is installed, and 0 otherwise.
