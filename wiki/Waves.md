How work enters brigade and is batched: a request and the plan it receives, then a wave of ratified tasks, how a wave
is started, shown, listed, cancelled and resumed, and how a parked task is queued again.

## Commands

```
brigade request new <project> <text>     # record a request and launch its planner
brigade request show <request>
brigade request list [--project P]
brigade request cancel <request>
brigade request replan <request>         # launch the planner again on a planning request whose planner stopped
brigade plan record <request> --file <plan>
brigade wave start <project> [--task T ...]   # one wave per milestone served, one for the tasks naming none
brigade wave show <wave> [--events]
brigade wave list [--project P]
brigade wave cancel <wave>
brigade wave resume [<wave>]
brigade wave requeue <wave> <task>       # queue a parked task again for the next tick
```

Each prints text or, with `--json`, a JSON document.

## From a request to a plan

A request is a `REQUEST` entity of `requests.awawa` in the registry: what the user wants for one project,
in their words, and the plan it receives.

1. `request new` records the request as `<project>_r<n>` with the status `planning`, launches the planner on it
   detached, and prints the request, the run and `brigade run show <run> --log`, the command that follows the planner.
2. The planner hands its plan, one `MILESTONE` and its tasks, to `plan record`, which commits it on `plan/<request>`
   and delivers it to the main branch.
3. The request goes `planned` with its `MILESTONE` and, under `github`, its `PR`.

| Forge and `POLICY` | How the plan reaches the main branch |
|---|---|
| `none` | the main branch is fast-forwarded to the plan commit at once |
| `github`, `PLAN_REVIEW auto` (the default) | brigade opens a pull request and merges it itself, squash |
| `github`, `PLAN_REVIEW ask` | brigade opens a pull request; the merge is the user's |

## Starting and following a wave

A wave is a batch of ratified tasks started together, recorded in the ledger alone, with no branch and no pull
request of its own. `wave start` composes the waves without a model, one per milestone it serves and one for the
tasks naming no milestone, and names each `<project>_w<n>`; each task of a wave runs on a branch of its own, cut from
the branch of its milestone, or from the main branch for a task naming none. A wave is open until `wave.closed`, which
the tick records once every task of the wave is merged or parked, or `wave.cancelled`.

A task joins the wave of its milestone when it:

- is `todo` in the project corpus at the branch of its milestone, the main branch until that branch is cut, or at the
  main branch for a task naming no milestone, and holds a number in its name;
- names a milestone that is `active` and whose `AFTER` milestones are all `reached`, or names none: the tasks of a
  `planned` milestone, or of one whose `AFTER` is not reached, are not taken;
- belongs to no open wave and has no live blocker;
- has every task of its `AFTER` implemented or in the wave.

The tasks join in the order of their number; `--task` takes exactly the tasks named instead, in one wave, which takes
the tasks of one milestone or tasks naming none.

`wave show` prints each task of a wave with its state, its pull request, its last run and, for a parked task, its
reason. `wave list` prints one row per wave, the open waves first.

> **Watch out:** a task parked in a closed wave is `todo` again for the tick, which serves it in a new wave, unless
> that wave parked it on the question of a run that ended `blocked`: such a task waits, named on stderr at each tick
> with its wave and its question, until its entity at the branch read differs from the one the wave read, or until
> `brigade wave requeue <wave> <task>` queues it; the next tick then launches it again in its existing worktree.

> **Watch out:** `wave cancel` leaves every worktree, branch and pull request of the wave in place, and the tasks of a
> cancelled wave are candidates of the next wave.

## Details and edge cases

<details><summary>Which commands need the registry</summary>

Every command but `wave show`, `wave list`, `wave cancel` and `wave resume`, which read the ledger alone, `wave show
--json` reading besides the milestone of the wave from the corpus of its project, and
`wave requeue`, which reads the ledger until the task proves parked, exits 1 naming `brigade init` until the corpus
exists.

</details>

<details><summary>Requests in detail</summary>

- `request new` takes `n` one above the highest its project holds, under the lock of the corpus, with the UTC instant
  of its creation. The planner is launched as
  `brigade run start request-plan --slot plan --project <project> --detach request=<name>`. A project that is not registered or
  is paused exits 1.
- `request show` prints a request, its status, its milestone, its pull request and the instant of its creation, `-`
  for a field it does not hold yet. `request list` prints one row per request, those of one project with `--project`.
- `request cancel` moves a `planning` or `planned` request to `cancelled`; a request of another status exits 1 naming
  it.
- `request replan` launches the planner again on a `planning` request whose planner run is no longer live, as
  `request new` launches it, and prints the request, the run and `brigade run show <run> --log`. A request of another
  status, a request whose planner run is live, or a paused project exits 1 naming it.
- Every write to the registry goes through the lock, `awawa fmt`, `awawa lint --strict` and the commit of
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

- `--task` exits 1 on a task in an open wave, a task with no number in its name, a task the corpus does not define,
  one whose `AFTER` is neither implemented nor named, and tasks naming two milestones, or a milestone and none, naming
  the milestone of each. A start with no task to take exits 1 naming the project.
- Without `--task`, an `active` milestone whose `AFTER` names a milestone not `reached` is named on stderr with that
  `AFTER`, and its tasks wait.
- `n` is one above the highest wave number of the project in the ledger. `wave start` records `wave.started` with the
  wave, the project, the tasks and the digest of each task entity under the lock of the ledger, and no branch.
- It then locates the base of the wave. For tasks naming no milestone, it is the main branch. For a milestone, it is
  its branch `integration/<slug of its TITLE>`: the one a `milestone.branch_cut` records, cut again from the main branch
  when the forge no longer holds it; otherwise cut from the main branch, pushed under the forge `github` and recorded as
  `milestone.branch_cut`.
- A branch of that name that no `milestone.branch_cut` records, local or remote, exits 1, and so does one recorded for
  another milestone.

</details>

<details><summary><code>wave show</code> and <code>wave list</code> in detail</summary>

- `wave show` prints a wave, the branch its `wave.started` holds where a wave of an earlier brigade recorded one, the
  instant it started and its last wave event, then each task with its last `task.state`, its pull request, its last
  run in the wave and, for a parked task, the reason of its `task.parked`, `-` when none. With `--events`, it adds what `brigade ledger` once printed for a wave: its cost and tokens, the
  turns, duration and cost of each task, its merged pull requests, its turns by slot and by role, its halts, its
  handovers, its parked tasks, then every event the ledger holds for the wave, in the order recorded.
  With `--json`, it names the milestone the tasks of the wave name, `null` for tasks naming none, read at the
  branch of that milestone as the last fetch of the tick left it: it reaches no forge.
- `wave list` prints one row per wave of the ledger, its project, the branch recorded as in `wave show`, its last wave
  event and its task count, the open waves first, those of one project with `--project`. With `--json`, each wave
  also carries `started_at`; `ended_at`, the instant of its `wave.closed` or `wave.cancelled`, `null` while it is
  open; `ended_by`, the name of that event, `null` while it is open; `task_states`, each task with its last state, `null` for a task no event served yet; `halt`, the `reason` and
  the `resume_at` of the pause in force, `null` once resumed or ended; `rounds`, the most review rounds one of its
  merged pull requests took, `0` when none merged; and `cost_usd`, the sum of the costs its runs record, `null` when
  none records one: a floor, since a run of a client that reports no cost adds nothing.

</details>

<details><summary><code>wave cancel</code> in detail</summary>

`wave cancel` records `wave.cancelled`, stops the live run of each task of the wave as `brigade run stop` does and
lists, per task, the run it stopped, the worktree of its last run, and the branch and the pull request it opened. A wave
already closed or cancelled exits 1 naming that event.

</details>

<details><summary><code>wave resume</code> in detail</summary>

`wave resume` records `wave.resumed` for the wave named, whatever the reason of its pause, or, without one, for every
wave parked on the forge account, the tick resuming by itself a wave blocked on the quota. It prints each wave it
resumed; a wave no `wave.started` names, or one that is not paused, exits 1 naming it.

A wave parked on the client login, the reason `client_login`, is resumed by naming it, once you have signed in to the
AI client again: the next tick launches its task again from the state it holds, as
[Tick and scheduler](Tick-and-scheduler.md#quota-blocks-forge-account-and-client-login-parks) says.

</details>

<details><summary><code>wave requeue</code> in detail</summary>

- `wave requeue` records `task.state` `queued` for a parked task of the wave named, and prints the task queued.
- It exits 1 on a task that is not parked, naming its state; on a task outside the wave, naming the wave; on a parked
  task the branch of its milestone, or the main branch, holds implemented, naming the branch; and on a wave no `wave.started` names, naming it.
- On an open wave, it also exits 1 on a task the main branch ruled since the branch the wave reads, the branch of its
  milestone, left it: its entity on the main branch differs from the one on that branch and from the one at the merge
  base of the two. It names both branches and `brigade wave cancel`, whose new wave reads the ruling. A task ruled on
  the branch of its milestone alone, by a pull request into that branch, is queued.
- A queued task that branch holds implemented is followed through its pull request, and recorded merged once it
  is.

</details>
