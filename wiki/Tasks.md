What a build run does from the worktree of its task with `brigade task`: read its starting package, run the checks,
open the pull request and promote the task.

## Commands

```
brigade task context [<task>]                  # the starting package of the run
brigade task check [<task>]                    # the acceptance commands and the corpus checks; exit 1 when one fails
brigade task pr [<task>] --subject <subject>   # push the branch with a lease and open the pull request on its base
brigade task promote [<task>] [--pr <n>]       # STATUS implemented and DELIVERED_BY, committed and pushed with a lease
```

A build run works in the worktree of its task, on the branch `<prefix>/<id>-<slug>` the tick cut from the branch of
its milestone, `integration/<slug>`, or from the main branch for a task naming no milestone: the prefix is the `TYPE`
of the task, `feat` becoming `feature`, the slug its `TITLE` lowercased, each run of other characters than ASCII
letters and digits made one hyphen, cut at a hyphen within 40 characters (`feature/B46-local-mode`). Its pull request
goes to that base. Every command runs from that worktree, takes the task of the branch when `<task>` is left out,
and its wave from the open wave of the ledger that holds the task. Each prints text or, with `--json`, a JSON document.
`task pr` and `task promote` push the branch with `--force-with-lease`, never with `--force`: the lease is the head of
`origin/<branch>` they read, or that the branch is absent from `origin`, so a branch the tick rebased since its last
push is pushed, and one another push moved is refused.

A task `draft` or `todo` at the branch of its milestone, a parked task being `todo`, holds the pull request of that
milestone until it is merged, moved to another milestone or archived. A milestone is reached once the user merges its
pull request, and a reached milestone takes no task: the tick serves a task naming it never and names the task on
stderr at each tick.

| Command | Records in the ledger |
|---|---|
| `task pr` | `task.pr_opened`, `milestone.created` |
| `task promote` | `task.promoted` |

> **Watch out:** `task pr` refuses a task whose last check is not of `HEAD` or has a failing command: run
> `task check` again after every commit.

## Details and edge cases

<details><summary><code>task context</code></summary>

It prints the starting package of the run: the ancestry of the worktree and the output of its setup, the task and its
closure, the rules of the files it touches, the project's `AGENTS.md`, the acceptance commands, the task number and the
attribution reserved for it.

</details>

<details><summary><code>task check</code></summary>

- It refuses a worktree whose files differ from `HEAD`, naming them.
- It runs each `ACCEPTANCE` line of the project as an argv, never through a shell, then `awawa fmt --check .` and
  `awawa lint --strict .`.
- It prints one line per command with its verdict and its duration, and the last 20 lines of each failing one.
- It records the verdicts with the sha of `HEAD` in `$XDG_STATE_HOME/brigade/checks/<project>/<task>.json`.

</details>

<details><summary><code>task pr</code></summary>

- It also refuses a task without `TYPE` and a missing subject.
- It creates the GitHub milestone named after the `TITLE` of the task's `MILESTONE` when the repository has none.
- It opens the pull request as the login of `forge_accounts.build`, titled
  `TYPE(COMPONENT): <subject> (@TASK.<task>)`, its body the task, its criteria, the verdicts of the check and the
  attribution.

</details>

<details><summary><code>task promote</code></summary>

- `DELIVERED_BY` is the pull request of the last `task.pr_opened`, unless `--pr` names another.
- It formats and lints the corpus, commits with the attribution lines and pushes; a second run replaces the
  `DELIVERED_BY` it wrote.
- It refuses a corpus whose `TASK` schema does not declare `STATUS implemented` and `DELIVERED_BY`.

</details>

<details><summary>A branch or a task that does not match</summary>

Every command exits 1 naming the cause when the branch or the task does not match.

</details>
