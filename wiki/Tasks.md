What a build run does from the worktree of its task with `brigade task`: read its starting package, run the checks,
open the pull request and promote the task.

## Commands

```
brigade task context [<task>]                  # the starting package of the run
brigade task check [<task>]                    # the acceptance commands and the corpus checks; exit 1 when one fails
brigade task pr [<task>] --subject <subject>   # push the branch and open the pull request on the wave's branch
brigade task promote [<task>] [--pr <n>]       # STATUS implemented and DELIVERED_BY, committed and pushed
```

A build run works in the worktree of its task, on the branch `task/<slug>/<task>` the tick cut from the wave's branch
`integration/<slug>`. Every command runs from that worktree and takes the task of the branch when `<task>` is left
out. Each prints text or, with `--json`, a JSON document.

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
