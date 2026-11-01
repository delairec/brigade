How a review run judges the pull request of a task: what `brigade verify context` prints and how
`brigade verify verdict` validates and records the verdict.

```
brigade verify context <pr>                        # everything the review judges, in one read
brigade verify verdict <pr> --file <verdict.json>  # validate and record the verdict
```

Both run from the worktree of the task whose pull request they judge.

## The verdict document

```
{"head", "verdict": "pass" | "changes", "findings": [{"grade", "file", "line", "broken", "summary"}]}
```

| Key | Holds |
|---|---|
| `head` | the commit `verify context` printed |
| `verdict` | `pass` or `changes` |
| `grade` | `critical`, `high`, `medium` or `low` |
| `broken` | the `SPEC` or the rule the finding breaks |
| `summary` | what is wrong |

`verify verdict` records the ledger event `task.verdict` at that head.

> **Watch out:** `verify verdict` refuses a document of another shape, a grade outside the four, `changes` without a
> finding, and a `head` that is no longer the head of the pull request: exit 1 naming what to correct, and nothing is
> recorded.

## Details and edge cases

<details><summary>What <code>verify context</code> prints</summary>

- the head it judges;
- the task with its `awawa context` and its closure;
- the diff of the pull request against its base;
- the findings of the preflight;
- the rules of the path triggers of the files the diff touches, when `config.toml` names an instructions corpus;
- the grades of a finding: `critical`, `high`, `medium` and `low`.

Once a `task.verdict` of the task is recorded on the pull request, it also prints:

- a section `previous verdict`: the head the last one judged, its verdict, and each of its findings by its identifier
  with the answer the last `task.review_answered` recorded for it since, or none;
- a section `repair diff`: `git diff` from that head to the current head when the first is an ancestor of the second,
  otherwise `git range-diff` of the commits of the pull request on their base at each head.

</details>

<details><summary>Under <code>REVIEW approval</code></summary>

Under `REVIEW approval` of the project's `POLICY`, `verify verdict` also posts the verdict as a GitHub review of that
commit, approving or requesting changes, as the login of the key `review` of `[forge_accounts]`, and the event carries
that login. Under `REVIEW verdict`, the default, the event alone is the verdict and its login is null.

</details>
