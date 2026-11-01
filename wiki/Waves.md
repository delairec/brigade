Answers how work enters brigade and is batched: a request and the plan it receives, then a wave of ratified tasks, how a wave is started, shown, listed, cancelled and resumed, and how a parked task is queued again.

A request is a `REQUEST` entity of `requests.awawa` in the operational corpus: what the user wants for one
project, in their words, and the plan it receives. Every command below but `wave show`, `wave list`, `wave cancel`
and `wave resume`, which read the ledger alone, and `wave requeue`, which reads the ledger until the task proves
parked, exits 1 naming `brigade init` until the corpus exists, and each prints text or, with `--json`, a JSON document.

## Commands

```
brigade request new <project> <text>
brigade request show <request>
brigade request list [--project P]
brigade request cancel <request>
brigade plan record <request> --file <plan>
brigade wave start <project> [--task T ...]
brigade wave show <wave>
brigade wave list [--project P]
brigade wave cancel <wave>
brigade wave resume [<wave>]
brigade wave requeue <wave> <task>
```

## Requests and plans

`request new` records the request as `<project>_r<n>`, `n` one above the highest its project holds, under the lock
of the corpus, with the UTC instant of its creation and the status `planning`, then launches the planner on it
detached, `brigade run wave-plan --slot plan --project <project> --detach request=<name>`, and prints the request and
the run, then the line `brigade runs show <run> --log`, the command that follows the planner. A project that is not
registered or is paused exits 1. `request show` prints a request, its status, its milestone, its pull request and the
instant of its creation, `-` for a field it does not hold yet; `request list` prints one row per request, those of one
project with `--project`. `request cancel` moves a `planning` or `planned` request to `cancelled`; a request of
another status exits 1 naming it. `plan record` takes the plan of a `planning` request, one `MILESTONE` and its
tasks, writes it in a detached worktree of the project's main branch, beside the entities of their types, runs
`awawa lint --strict` and commits it on `plan/<request>`; under the forge `none` it fast-forwards the main branch to
that commit at once, and under `github` it pushes the branch and opens a pull request to the main branch, titled
`docs(plan): <milestone title> (@REQUEST.<request>)`, as the login of the key `cli` of `[forge_accounts]`. Under
`PLAN_REVIEW auto`, the default, brigade merges that pull request itself, squash, as the same login, the login of the
key `review` approving it first when the forge requires an approving review; under `PLAN_REVIEW ask` the merge is
the user's. The request goes `planned` with its `MILESTONE` and, under `github`, its `PR`. A plan record replayed
once `plan/<request>` exists commits nothing again: it takes the pull request of that branch, pushes the branch and
opens it when the forge finds none, and marks the request planned. Every write to the operational corpus goes
through the lock, `awawa fmt`, `awawa lint --strict` and the commit of the registry's writes.

## Starting and following a wave

A wave is a batch of ratified tasks started together, recorded in the ledger alone. `wave start` composes it without a
model from the tasks `todo` of the project corpus at the main branch that hold a number in their name, belong to no
open wave and have no live blocker, admitting a task once every task of its `AFTER` is implemented or in the wave, in
the order of their number; `--task` takes exactly the tasks named and exits 1 on a task in an open wave, a task with no
number in its name, a task the corpus does not define or one whose `AFTER` is neither implemented nor named, and an
empty wave exits 1 naming the project. It names the wave `<project>_w<n>`, `n` one above the highest wave number of
the project in the ledger, records `wave.started` with the wave, the project, the branch and the tasks under the lock
of the ledger, then cuts `integration/<project>_w<n>` from the main branch and pushes it under the forge `github`; the
missing branch of an open wave is cut again, and a branch of the name that no `wave.started` names, local or remote,
exits 1. A wave is open until `wave.closed` or `wave.cancelled`. `wave show` prints a wave, its branch, the instant it
started and its last wave event, then each task with its last `task.state`, its pull request, its last run in the
wave and, for a parked task, the reason of its `task.parked`, `-` when none; `wave list` prints one row per wave of the ledger, its project, branch, last wave event and task
count, the open waves first, those of one project with `--project`. `wave cancel` records `wave.cancelled`, stops the
live run of each task of the wave as `brigade runs stop` does and lists, per task, the run it stopped, the worktree of
its last run, and the branch and the pull request it opened, all left in place; a wave already closed or cancelled
exits 1 naming that event. The tasks of a cancelled wave are candidates of the next wave.

## Resuming a wave

`wave resume` records `wave.resumed` for the wave named, whatever the reason of its pause, or, without one, for every
wave paused on the forge account, the tick resuming by itself a wave paused on the quota; it prints each wave it
resumed, and a wave no `wave.started` names, or one that is not paused, exits 1 naming it.

## Queuing a parked task again

`wave requeue` records `task.state` `queued` for a parked task of the wave named, so that the next tick launches it
again in its existing worktree; it prints the task queued, and a task that is not parked exits 1 naming its state, a
task outside the wave exits 1 naming the wave, a parked task the wave branch holds implemented exits 1 naming the
branch, and a wave no `wave.started` names exits 1 naming it. The tick never queues a parked task again by itself; a
queued task the wave branch holds implemented is followed through its pull request, and recorded merged once it is.
