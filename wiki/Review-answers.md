How a run of the `remediate` slot answers the review of a task: what `brigade review context` prints and how
`brigade review reply` validates and records the answers.

```
brigade review context <pr>                       # the findings to answer
brigade review reply <pr> --file <answers.json>   # validate and record the answers
```

Both run from the worktree of the task whose review a run of the `remediate` slot answers.

## The answers document

```
{"answers": [{"finding", "answer"}]}
```

One answer per finding of the context. `review reply` records the ledger event `task.review_answered` at the head of
the pull request.

| Project's `POLICY` | Findings listed by `review context` | Where the answers go |
|---|---|---|
| `REVIEW verdict`, the default | those of the last `task.verdict`, numbered from 1 | the ledger alone; the event's login is null |
| `REVIEW approval` | the open review threads of the pull request, each by its thread identifier | each answer replied on its thread as the login of the key `remediate` of `[forge_accounts]`, which the event carries |

> **Watch out:** `review reply` refuses a document of another shape, a finding left unanswered, answered twice or not
> in the context: exit 1 naming what to correct, and nothing is recorded.

<details><summary>What else <code>review context</code> prints</summary>

Before the findings, each under its identifier, it prints the head of the pull request and the request of the
preflight that moved the task to `changes_requested`, when there is one.

</details>
