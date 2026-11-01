How work enters brigade and is batched: a request and the plan it receives, then a wave of ratified tasks, how a wave
is started, shown, listed, cancelled and resumed, and how a parked task is queued again.

## Commands

```
brigade request new <project> <text>     # record a request and launch its planner
brigade request show <request>
brigade request list [--project P]
brigade request cancel <request>
brigade plan record <request> --file <plan>
brigade wave start <project> [--task T ...]
brigade wave show <wave>
brigade wave list [--project P]
brigade wave cancel <wave>
brigade wave resume [<wave>]
brigade wave requeue <wave> <task>       # queue a parked task again for the next tick
```

Each prints text or, with `--json`, a JSON document.

## From a request to a plan

A request is a `REQUEST` entity of `requests.awawa` in the operational corpus: what the user wants for one project,
in their words, and the plan it receives.

1. `request new` records the request as `<project>_r<n>` with the status `planning`, launches the planner on it
   detached, and prints the request, the run and `brigade runs show <run> --log`, the command that follows the planner.
2. The planner hands its plan, one `MILESTONE` and its tasks, to `plan record`, which commits it on `plan/<request>`
   and delivers it to the main branch.
3. The request goes `planned` with its `MILESTONE` and, under `github`, its `PR`.

| Forge and `POLICY` | How the plan reaches the main branch |
|---|---|
| `none` | the main branch is fast-forwarded to the plan commit at once |
| `github`, `PLAN_REVIEW auto` (the default) | brigade opens a pull request and merges it itself, squash |
| `github`, `PLAN_REVIEW ask` | brigade opens a pull request; the merge is the user's |

## Starting and following a wave

A wave is a batch of ratified tasks started together, recorded in the ledger alone. `wave start` composes it without
a model and names it `<project>_w<n>` on the branch `integration/<project>_w<n>`. A wave is open until `wave.closed`
or `wave.cancelled`.

A task joins the wave when it:

- is `todo` in the project corpus at the main branch, and holds a number in its name;
- belongs to no open wave and has no live blocker;
- has every task of its `AFTER` implemented or in the wave.

The tasks join in the order of their number; `--task` takes exactly the tasks named instead.

`wave show` prints each task of a wave with its state, its pull request, its last run and, for a parked task, its
reason. `wave list` prints one row per wave, the open waves first.

> **Watch out:** the tick never queues a parked task again by itself: run `brigade wave requeue <wave> <task>`, and
> the next tick launches it again in its existing worktree.

> **Watch out:** `wave cancel` leaves every worktree, branch and pull request of the wave in place, and the tasks of a
> cancelled wave are candidates of the next wave.

## Details and edge cases

<details><summary>Which commands need the operational corpus</summary>

Every command but `wave show`, `wave list`, `wave cancel` and `wave resume`, which read the ledger alone, and
`wave requeue`, which reads the ledger until the task proves parked, exits 1 naming `brigade init` until the corpus
exists.

</details>

<details><summary>Requests in detail</summary>

- `request new` takes `n` one above the highest its project holds, under the lock of the corpus, with the UTC instant
  of its creation. The planner is launched as
  `brigade run wave-plan --slot plan --project <project> --detach request=<name>`. A project that is not registered or
  is paused exits 1.
- `request show` prints a request, its status, its milestone, its pull request and the instant of its creation, `-`
  for a field it does not hold yet. `request list` prints one row per request, those of one project with `--project`.
- `request cancel` moves a `planning` or `planned` request to `cancelled`; a request of another status exits 1 naming
  it.
- Every write to the operational corpus goes through the lock, `awawa fmt`, `awawa lint --strict` and the commit of
  the registry's writes.

</details>

<details><summary><code>plan record</code> in detail</summary>

- It takes the plan of a `planning` request and writes it in a detached worktree of the project's main branch, beside
  the entities of their types, runs `awawa lint --strict` and commits it on `plan/<request>`.
- Under `github` it pushes the branch and opens a pull request to the main branch, titled
  `docs(plan): <milestone title> (@REQUEST.<request>)`, as the login of the key `cli` of `[forge_accounts]`.
- Under `PLAN_REVIEW auto` it merges as the same login, the login of the key `review` approving the pull request first
  when the forge requires an approving review.
- A plan record replayed once `plan/<request>` exists commits nothing again: it takes the pull request of that branch,
  pushes the branch and opens it when the forge finds none, and marks the request planned.

</details>

<details><summary><code>wave start</code> in detail</summary>

- `--task` exits 1 on a task in an open wave, a task with no number in its name, a task the corpus does not define, or
  one whose `AFTER` is neither implemented nor named. An empty wave exits 1 naming the project.
- `n` is one above the highest wave number of the project in the ledger. `wave start` records `wave.started` with the
  wave, the project, the branch and the tasks under the lock of the ledger, then cuts `integration/<project>_w<n>`
  from the main branch and pushes it under the forge `github`.
- The missing branch of an open wave is cut again; a branch of the name that no `wave.started` names, local or remote,
  exits 1.

</details>

<details><summary><code>wave show</code> and <code>wave list</code> in detail</summary>

- `wave show` prints a wave, its branch, the instant it started and its last wave event, then each task with its last
  `task.state`, its pull request, its last run in the wave and, for a parked task, the reason of its `task.parked`,
  `-` when none.
- `wave list` prints one row per wave of the ledger, its project, branch, last wave event and task count, the open
  waves first, those of one project with `--project`.

</details>

<details><summary><code>wave cancel</code> in detail</summary>

`wave cancel` records `wave.cancelled`, stops the live run of each task of the wave as `brigade runs stop` does and
lists, per task, the run it stopped, the worktree of its last run, and the branch and the pull request it opened. A wave
already closed or cancelled exits 1 naming that event.

</details>

<details><summary><code>wave resume</code> in detail</summary>

`wave resume` records `wave.resumed` for the wave named, whatever the reason of its pause, or, without one, for every
wave paused on the forge account, the tick resuming by itself a wave paused on the quota. It prints each wave it
resumed; a wave no `wave.started` names, or one that is not paused, exits 1 naming it.

</details>

<details><summary><code>wave requeue</code> in detail</summary>

- `wave requeue` records `task.state` `queued` for a parked task of the wave named, and prints the task queued.
- It exits 1 on a task that is not parked, naming its state; on a task outside the wave, naming the wave; on a parked
  task the wave branch holds implemented, naming the branch; and on a wave no `wave.started` names, naming it.
- A queued task the wave branch holds implemented is followed through its pull request, and recorded merged once it
  is.

</details>
