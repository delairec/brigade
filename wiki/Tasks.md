Answers what a build run does from the worktree of its task: read its starting package, run the checks, open the pull request and promote the task, with `brigade task`.

A build run works in the worktree of its task, on the branch `task/<slug>/<task>` the tick cut from the wave's branch
`integration/<slug>`. Every command below runs from that worktree, takes the task of the branch when `<task>` is left
out, exits 1 naming the cause when the branch or the task does not match, and prints text or, with `--json`, a JSON
document.

## Commands

```
brigade task context [<task>]
brigade task check [<task>]
brigade task pr [<task>] --subject <subject>
brigade task promote [<task>] [--pr <n>]
```

## What each command does

`task context` prints the starting package of the run: the ancestry of the worktree and the output of its setup, the
task and its closure, the rules of the files it touches, the project's `AGENTS.md`, the acceptance commands, the task
number and the attribution reserved for it. `task check` refuses a worktree whose files differ from `HEAD`, naming them,
then runs each `ACCEPTANCE` line of the project as an argv, never through a shell, then `awawa fmt --check .` and `awawa
lint --strict .`, prints one line per command with its verdict and its duration, and the last 20 lines of each failing
one; it records the verdicts with the sha of `HEAD` in `$XDG_STATE_HOME/brigade/checks/<project>/<task>.json` and exits
1 when one fails. `task pr` refuses a task whose last check is not of `HEAD` or has a failing command, a task without
`TYPE` and a missing subject; it pushes the branch, creates the GitHub milestone named after the `TITLE` of the task's
`MILESTONE` when the repository has none, and opens the pull request on the wave's branch as the login of
`forge_accounts.build`, titled `TYPE(COMPONENT): <subject> (@TASK.<task>)`, its body the task, its criteria, the
verdicts of the check and the attribution. `task promote` sets `STATUS implemented` and `DELIVERED_BY` on the task, the
pull request of the last `task.pr_opened` unless `--pr` names another, formats and lints the corpus, commits with the
attribution lines and pushes, a second run replacing the `DELIVERED_BY` it wrote; it refuses a corpus whose `TASK`
schema does not declare them. The three record `task.pr_opened`, `milestone.created` and `task.promoted` in the ledger.
