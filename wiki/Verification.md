Answers how a review run judges the pull request of a task: what `brigade verify context` prints and how `brigade verify verdict` validates and records the verdict.

```
brigade verify context <pr>
brigade verify verdict <pr> --file <verdict.json>
```

## `verify context`

Both run from the worktree of the task whose pull request they judge. `verify context` prints in one read the head
it judges, the task with its `awawa context` and its closure, the diff of the pull request against its base, the
findings of the preflight, the rules of the path triggers of the files the diff touches when `config.toml` names an
instructions corpus, and the grades of a finding: `critical`, `high`, `medium` and `low`. Once a `task.verdict` of
the task is recorded on the pull request, it also prints a section `previous verdict`, the head the last one judged,
its verdict and each of its findings by its identifier with the answer the last `task.review_answered` recorded for
it since, or none, and a section `repair diff`: `git diff` from that head to the current head when the first is an
ancestor of the second, otherwise `git range-diff` of the commits of the pull request on their base at each head.

## `verify verdict`

`verify verdict` reads `{"head", "verdict": "pass" | "changes", "findings": [{"grade", "file", "line", "broken",
"summary"}]}`, where `head` is the commit `verify context` printed, `broken` names the `SPEC` or the rule the finding
breaks and `summary` says what is wrong; it
refuses a document of another shape, a grade outside the four, `changes` without a finding, and a `head` that is no
longer the head of the pull request, exit 1 naming what to correct, and records nothing. It records the ledger event
`task.verdict` at that head. Under `REVIEW approval` of the project's `POLICY` it also posts the verdict as a GitHub
review of that commit, approving or requesting changes, as the login of the key `review` of `[forge_accounts]`, and
the event carries that login; under `REVIEW verdict`, the default, the event alone is the verdict and its login is
null.
