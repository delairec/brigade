How a review run judges the pull request of a task: what `brigade review context` prints and how
`brigade review verdict` validates and records the verdict.

```
brigade review context <pr>                        # everything the review judges, in one read
brigade review verdict <pr> --file <verdict.json>  # validate and record the verdict
```

Both run from the worktree of the task whose pull request they judge.

## What the review judges

The review run judges three things, and its `SPEC` lines are never the whole of it:

| Against | Asks |
|---|---|
| each `SPEC` line | does a test, a command or a line of code prove the criterion holds? |
| the goal the task serves | does the delivery reach the goal of its milestone, the user's intent, beyond its `SPEC` lines? |
| the reference the task carries in its `REFERENCE` field | does the delivery keep the reference itself, a mockup, a page or a document, and not only what the task transcribed from it? |

A delivery that meets every `SPEC` line and misses its goal, or departs from its reference without a reason a `SPEC`,
a `RATIONALE` or a decision states, gets a finding that asks for changes; a `pass` states the goal reached. For a
rendered output, the pull request carries screenshots of the result and of the reference side by side, and their
absence is a finding.

## The verdict document

```
{"head", "verdict": "pass" | "changes", "findings": [{"grade", "file", "line", "broken", "summary"}]}
```

| Key | Holds |
|---|---|
| `head` | the commit `review context` printed |
| `verdict` | `pass` or `changes` |
| `grade` | `critical`, `high`, `medium` or `low` |
| `broken` | the `SPEC`, the milestone, the reference or the rule the finding breaks |
| `summary` | what is wrong |

`review verdict` records the ledger event `task.verdict` at that head.

> **Watch out:** `review verdict` refuses a document of another shape, a grade outside the four, `changes` without a
> finding, and a `head` that is no longer the head of the pull request: exit 1 naming what to correct, and nothing is
> recorded.

## Details and edge cases

<details><summary>What <code>review context</code> prints</summary>

- the head it judges;
- the task with its `awawa context` and its closure;
- a section `goal`: the title of the task, then the `TITLE`, `SUBJECT`, `DESC` and `SOURCE` of its milestone, read
  in the tree of the head, or `no milestone: the title of the task is its goal`;
- a section `reference`: each `REFERENCE` of the task, a URL or a repository path, with the page or the section
  its `COVERS` names, or `none`;
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

Under `REVIEW approval` of the project's `POLICY`, `review verdict` also posts the verdict as a GitHub review of that
commit, approving or requesting changes, as the login of the key `review` of `[forge_accounts]`, and the event carries
that login. Under `REVIEW verdict`, the default, the event alone is the verdict and its login is null.

</details>
