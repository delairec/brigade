Answers how a run of the `remediate` slot answers the review of a task: what `brigade review context` prints and how `brigade review reply` validates and records the answers.

```
brigade review context <pr>
brigade review reply <pr> --file <answers.json>
```

## `review context`

Both run from the worktree of the task whose review a run of the `remediate` slot answers. `review context` prints
the head of the pull request, the request of the preflight that moved the task to `changes_requested` when there is
one, and the findings to answer, each under its identifier: under `REVIEW verdict` the findings of the last
`task.verdict`, numbered from 1; under `REVIEW approval` the open review threads of the pull request, each by its
thread identifier.

## `review reply`

`review reply` reads `{"answers": [{"finding", "answer"}]}`, one answer per finding of the context; it refuses a
document of another shape, a finding left unanswered, answered twice or not in the context, exit 1 naming what to
correct, and records nothing. It records the ledger event `task.review_answered` at the head of the pull request.
Under `REVIEW approval` it also replies each answer on its thread as the login of the key `remediate` of
`[forge_accounts]`, and the event carries that login; under `REVIEW verdict` its login is null.
