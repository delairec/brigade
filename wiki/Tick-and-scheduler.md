What a tick does with the facts it reads, from launching the tasks of a wave to verifying, repairing and rebasing their
pull requests, starting waves and pausing them on the quota, and how `brigade scheduler` fires the tick every five
minutes.

## Commands

```
brigade tick --once         # one tick, under the lock $XDG_STATE_HOME/brigade/locks/tick.lock
brigade tick --dry-run      # the snapshot and the plan, applied to nothing
brigade tick --loop         # a tick at once, then one every five minutes, until SIGTERM or SIGINT
brigade scheduler install   # install what fires brigade tick --once every five minutes
brigade scheduler status    # the scheduler, the last tick, the paused waves and the parked tasks
```

Every mode prints text or, with `--json`, a JSON document.

## What a tick does

A tick builds a snapshot of the facts, plans the actions they call for and applies them, round after round until the
plan is empty or ten rounds have passed. Among those actions, it:

- runs the due studies, as [Studies](Studies.md) says;
- starts a wave for each project whose `POLICY` sets `WAVE_START` to `auto`;
- carries each task of an open wave from its launch to its merge, as below;
- pauses every running wave on the quota or on the forge account, and resumes it.

## The course of a task

| Step | What the tick does | Task state |
|---|---|---|
| launch | cuts a worktree for each startable task of an open wave and launches a detached build run of `build-task` | `running` |
| pull request | follows the pull request of the task | `pr_open` when it opens |
| preflight | once every check run completed, runs `brigade verify preflight`; no failing check moves the task on | `verifying` |
| review | starts a detached run of the slot `review`, of `verify-pr`; its `task.verdict` decides | `verified` on `pass`, `changes_requested` on `changes` |
| repair | starts a detached run of the slot `remediate`, of `remediate-pr`, or of the slot `build` for a failing check | `fixing`, back to `pr_open` on a push |
| rebase | rebases a pull request behind its base once its check runs all passed; a conflict starts a run of the slot `rebase` | back to `pr_open`, or `fixing` |
| merge | merges a verified pull request into the branch of its milestone, never into the main branch, then removes the task's worktree once its pull request is merged or closed | `merged` |

The procedure of each run is the one brigade ships, or the one the key of its slot (`build`, `review`, `remediate`,
`rebase`) of the table `[procedures]` of `config.toml` names in its place.

## Why a task is parked

| `task.parked` reason | When |
|---|---|
| `pull request closed` | its pull request closes unmerged |
| `setup failed` | the setup of its worktree fails; the worktree and the branch stay in place |
| `run dead: <run>`, or `run not started` | it is `running`, has no pull request, and no live run names it |
| the rounds | it passes the `VERIFY_ROUNDS` of the project's `POLICY`, 2 by default |
| the run and its question | a run of the slot `remediate`, `build` or `rebase` ended on `brigade-end: blocked` |
| `blocked by` and the citing entity | it is queued in an open wave and a live blocker cites it |

> **Watch out:** the tick never queues a parked task again by itself: `brigade wave requeue`, as [Waves](Waves.md)
> says.

## Quota and forge-account pauses

| Cause | Reason | Resumed |
|---|---|---|
| a run finished on the `error_class` `rate_limit`, until its `reset` has passed | `quota` | by the first tick past `resume_at` |
| a `forge_account.unavailable` in the ledger | `forge_account` | by `brigade wave resume` alone |

The tick launches no run of a paused wave.

> **Watch out:** a wave paused on the forge account stays paused, waves started after the event included, until you
> run `brigade wave resume`.

## The scheduler

`brigade scheduler install` chooses the scheduler by the `scheduler` key of `config.toml`, else by a probe:

| Scheduler | Chosen by the probe when | Installs |
|---|---|---|
| `systemd` | `systemctl --user is-system-running` answers `running` or `degraded` | `brigade.service` and `brigade.timer` in `$XDG_CONFIG_HOME/systemd/user/`, the timer enabled now |
| `cron` | otherwise | the crontab line marked `# brigade scheduler install`; each tick's stderr goes to `$XDG_STATE_HOME/brigade/tick.log` |
| `loop` | never | nothing: it names the `brigade tick --loop` command to keep running |

`brigade scheduler status` reports the scheduler and the last tick, and exits 1 when the last tick is older than
`tick_stale_after` of `config.toml`, in minutes, 15 by default.

> **Watch out:** under `systemd`, without `loginctl enable-linger` the user manager stops with the last session, and
> the timer with it. `scheduler install` warns when `loginctl show-user -p Linger` does not answer `Linger=yes`.

## Details and edge cases

<details><summary>Launching a task</summary>

- The build run is launched in the worktree the tick cuts for the task, resolved as the argument of `brigade run` is,
  with the wave and the task as `--wave` and `--task`.
- A task is recorded `running` before its run is spawned. Its launch reuses the branch `<prefix>/<id>-<slug>` and its
  worktree when they exist, whatever the wave, a cancelled or a closed one included.
- On a project of `FORGE github`, the launch fetches the base of the task, the branch of its milestone or the main
  branch for a task naming none, and cuts the task branch from `origin/<base>`, its setup checking that
  `origin/<base>` is an ancestor of `HEAD`. A project of `FORGE none` keeps its local base.
- An existing task branch that does not descend from that base is rebased onto it before the setup only when its pull
  request is open and its check runs all passed. A rebase stopped on a conflict is aborted, and the tick starts a
  detached run of the slot `rebase` in the worktree of the task, with the arguments `task` and `base` and no `pr`, the
  task staying `running`. Once that run ends done, the next tick launches the build run; a run that ends blocked parks
  the task on its question.
- Any other such branch is built as it stands: the tick rebases nothing, its setup checks no ancestry, and the brief
  tells the build not to rebase it. The build opens its pull request behind its base, and the tick rebases it once its
  check runs pass.
- The tick follows the pull request of each task past its launch, read as the login of the key `cli` of
  `[forge_accounts]`. The worktree of a task is never removed while a run holds it.

</details>

<details><summary>When a dead run parks a task</summary>

A `running` task with no pull request that no live run names in its wave and task is parked, `task.parked` with the
reason `run dead: <run>`, the last run naming the task, or `run not started` when no run names it. A run rate-limited
and not resumed since, or a rebase run ended done, does not park the task; a run resumed after the quota reset that
dies before it records a `run.finished` does.

</details>

<details><summary>Preflight and review</summary>

- The preflight runs on the pull request a task in `pr_open` opened, once every check run completed (at least one,
  unless the project declares `CHECK_RUNS none`), and for each head once. It records its findings in
  `task.preflighted`.
- On a task in `verifying` whose pull request is open, the tick starts a fresh review run in the task's worktree, with
  `pr` and `task` as its arguments, unless a run holds the worktree or a review run of the task already ended at that
  head other than on a rate limit.
- The verdict counts once a `task.verdict` is recorded at the head of the pull request.
- A task in `verifying` whose pull request head is no longer the head of its last `task.preflighted` moves back to
  `pr_open`, where the preflight of the new head opens the next verification.
- A task in `pr_open` whose preflight failed on a finding other than `ancestry` and `checks` moves to
  `changes_requested`, those findings as its reason.

</details>

<details><summary>Repair rounds</summary>

- A repair run starts on an open pull request whose head the last preflight judged, and when no run holds the task's
  worktree.
- A task in `changes_requested` starts a run of the slot `remediate`, which answers through
  `brigade review context|reply`.
- A task whose preflight found a failing check starts a run of the slot `build` whose brief carries the build brief of
  the task and the last 200 lines of the log of each failing check.
- Each launch records the task `fixing` and counts one round. A run that ends without a push leaves the task `fixing`,
  and the next tick launches it again. A push moves the task back to `pr_open`.
- A run of the slot `remediate`, `build` or `rebase` that cannot go on without a ruling pushes nothing and ends on
  `brigade-end: blocked`, its question on the lines above: the next tick parks its task whatever its rounds,
  `task.parked` naming the run and that question.

</details>

<details><summary>Rebasing a pull request behind its base</summary>

- A task whose open pull request is behind its base, from `pr_open` to `fixing`, is rebased by git when
  no run holds its worktree, and waits for the next tick otherwise.
- Under the lock of the project's worktrees, the tick fetches the base, rebases the worktree onto it and pushes
  with `--force-with-lease` on the head it read, as the login of the key `cli` of `[forge_accounts]`. It then records
  `task.rebased`, the head before and after and that login, and moves the task back to `pr_open`.
- On a conflict it aborts the rebase and starts a detached run of the slot `rebase`, of `rebase-on-base`, which works
  through `brigade rebase context|done`. The launch records the task `fixing` and counts no round; past the rounds the
  repair runs spent, the task is parked instead.

</details>

<details><summary>Rebasing the branch of a milestone</summary>

- The tick rebases the branch of a milestone onto the main branch once the main branch has outrun it.
- A conflict is aborted and handed to a detached run of the slot `rebase`.
- A milestone branch git rebased cleanly is checked before it is pushed: in its worktree the tick runs the `SETUP`
  lines of the project, then its `ACCEPTANCE` lines and `awawa fmt --check .` and `awawa lint --strict .`, as
  `brigade task check` does. A failing one pushes nothing: the rebased head stays in the worktree and a detached run of
  the slot `rebase` repairs it there, then pushes it once its tests pass.
- No rebase is planned for a wave that is paused, or whose rebase run lives or ended blocked; a blocked rebase run
  pauses its wave on its question.
- `brigade wave resume` answers every rebase run of the wave that ended blocked before it, one that ended while the
  wave was paused on another question included: only a rebase run that ends blocked after the resume pauses the wave
  again. The resume the tick records after a quota reset answers none.

</details>

<details><summary>A failed action, and the waves a tick reads</summary>

- An action that fails is recorded as `tick.action_failed`, with the action, its project, wave and task where it names
  them, and the error. The tick applies the actions that follow it, never applies it again in the same tick and undoes
  nothing, the next tick planning again from the facts.
- The waves are the open waves of the ledger, each with the tasks its `wave.started` names, in that order, read from
  the project corpus at the branch of the open milestone holding every task of the wave, or at the main branch. A wave whose pull requests the forge fails to read is skipped, named on
  stderr, and the tick serves the others.

</details>

<details><summary>Starting and closing waves</summary>

- The tick starts a wave, as `brigade wave start <project>` does, for each registered project not `paused` whose
  `POLICY` sets `WAVE_START` to `auto`, when at least one candidate lies outside every open wave. `auto` is the default
  when no `POLICY` names the project; `ask` leaves the start to the user.
- The wave takes every candidate, the `SLOTS` of the project bounding the live build runs alone.
- A project whose tasks cannot be read is skipped, named on stderr.
- The tick cuts no branch for a wave, opens no pull request for it and merges none. Once every task of a wave is
  `merged` or `parked`, it records `wave.closed`, with no pull request.
- Once every task of a milestone at its branch is `merged` or `parked` and no wave of it is open, the tick runs the
  study `milestone-report` and records `milestone.reported`; that run commits the report on the branch of the
  milestone and opens its pull request into the main branch, the report as its body.
- For a task naming no milestone, once its pull request is ready to merge or the task is parked, the tick runs the
  study `task-report` and records `task.reported`; that run commits the report on the branch of the task and
  replaces the body of its pull request with it. The user merges that pull request into the main branch.
- The patterns of a request go delivered at `milestone.closed` of the milestone it was planned into.

</details>

<details><summary>Quota pauses in detail</summary>

- A quota pause records `wave.paused` with the reason `quota` and `resume_at`: the first instant after the tick's clock
  at the hour and in the timezone of the result's `reset`, or that clock plus 30 minutes when `reset` is null. The task
  of a build run moves to `paused:quota`.
- A wave started during a quota pause is paused until the same `resume_at`.
- The forge-account pause carries no `resume_at`.
- The first tick past `resume_at` records `wave.resumed` for the wave and resumes the run of each `paused:quota` task as
  its next segment, through `resume-argv` with the session of its last segment, or as a fresh launch from its progress
  file when the client adapter declares no resume. Only a segment that wrote its `result.json` counts: a segment
  directory left without one, by a segment that failed before or while it ran, is run again under its number. It moves the task back to `running` with the reason `resumed after
  the quota reset`: that resume ends the stop, and only a later `run.finished` on `rate_limit` pauses the task again.

</details>

<details><summary>The modes of <code>brigade tick</code></summary>

- `tick --once` takes the lock without waiting: when another tick holds it, it writes one line naming the lock on
  stderr, writes nothing and exits 0. Otherwise it writes the heartbeat `$XDG_STATE_HOME/brigade/tick.json`
  atomically: `schema_version`, `ts`, `duration_ms`, `actions_applied` and `actions_failed`.
- `--dry-run` takes no lock and writes neither the heartbeat nor a tick trail, its records going to the trail of a
  command.
- `--loop` reports each tick on stderr; a signal lets the tick under way finish, then the loop exits 0 with the number
  of ticks attempted, stand-downs included.

</details>

<details><summary><code>brigade scheduler install</code> in detail</summary>

- The probe runs without the `scheduler` key or without `config.toml`.
- `systemd` reloads the user manager after writing the units, then enables the timer now. Its linger warning goes in
  the `warnings` list of its document and one line of its text; the exit code stays 0.
- `cron` replaces its marked line, keeping every other line, and discards the stdout of each tick, the heartbeat
  keeping the last tick.
- The unit and the cron line run the brigade that installed them with the `PATH`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`
  and `XDG_CACHE_HOME` of the install, escaped for systemd or quoted for the shell and cron.
- Run again, it leaves one pair of units or one line.

</details>

<details><summary><code>brigade scheduler status</code> in detail</summary>

It reports the scheduler installed or `none`, its unit files or cron line, the next activation of the timer, the last
tick read from the heartbeat, the paused waves with their reason and their `resume_at`, and the parked tasks of the
open waves with their wave and their reason; it resumes no wave. It exits 1 when the last tick is older than
`tick_stale_after`, or when no tick ever ran while a scheduler is installed, and 0 otherwise.

</details>
