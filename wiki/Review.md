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
| the reference the task carries in its `REFERENCE` field, a repository path | does the delivery keep the reference itself, the section its `COVERS` names, and not only what the task transcribed from it? |

A delivery that meets every `SPEC` line and misses its goal, or departs from its reference without a reason a `SPEC`,
a `RATIONALE` or a decision states, gets a finding that asks for changes; a `pass` states the goal reached, on the second review too, where a challenge
to a goal or a reference finding is judged against the goal or the reference. For a rendered output, the review reads
every PNG slice `review context` names for each covered page, in order, the delivered page then the reference page; a
covered page with no pair is a finding, and so is a reference the review cannot open.

A goal finding takes as `file` and `line` the corpus file and line of its milestone, or of the task when it has none; a
reference finding the path of the reference and the line its section opens on.

## A reference and its captures

A `REFERENCE` is a path of the repository: the roles of the tick read files and run commands, and cannot open a URL. A
reference held elsewhere, an Artifact or a page of a website, is copied into the repository first, its commit pinning
its version: `artifact/m18-dashboard/index.html` holds the mockup of M18, whose `<section id>` each task names in its
`COVERS`. The planner reports a URL as a question, and `review context` prints it refused.

A task branch that changes the file its own `REFERENCE` names is a finding of the preflight `promotion`: the delivery
would be judged against a reference it rewrote. A task whose purpose is to deliver the reference itself says so with a
`REVISES` line under that `REFERENCE`, the reason in its words, written by the planner at ratification: the preflight
reads it at the base of the task branch, so a branch that adds it to its own task waives nothing.

```
REFERENCE "artifact/harbour/index.html"
	COVERS "tides"
	REVISES "the task draws the tide page of the mockup"
```

```
brigade build capture <task>                      # the delivered page and the reference page of HEAD, as PNG files
brigade build capture <task> --directory <dir>   # the same, written to <dir>
brigade page <page> --project <name>             # one page of the dashboard as a standalone HTML document
```

`brigade build capture` writes, for each page a `REFERENCE` of the task covers, one headless Firefox capture of the
delivered page and one of the reference page, one after the other, under `captures/<project>/<task>/<head>` of the
state directory. The home directory is shown as `~` in each page, and the Firefox profile is removed once the page is
captured.

| Page | How it renders |
|---|---|
| delivered | the recipe `capture` of the project, of command steps run in the worktree: each argv runs with `{page}` replaced by the `COVERS`, and the output of the last step is the HTML of that page; brigade's own runs `brigade page {page} --project brigade` |
| reference | an HTML reference with only its section whose id `COVERS` names shown |

`brigade page` serves `home`, `waves`, `runs`, `ledger`, `inbox`, `reports` and `awawa`, and `wave`, `run` and
`report` as the newest of the project. It fails on any other page and on a view that answers an error, so the capture
of that page fails too. The page holds what the served page shows at load: every region, the next tick of Home and the
addons of the rail included.

A section that no page renders, a stylesheet specimen, carries `READ` under its `REFERENCE`, the file its delivery is
judged by reading: `build capture` captures nothing for it, and `review context` prints the file under `read:` in place
of a PNG pair.

```
REFERENCE "artifact/m18-dashboard/index.html"
	COVERS "foundation"
	READ "brigade/dashboard/data/dashboard.css"
```

A capture taller than 2000 px is cut into ordered slices of 2000 px, `<page>-delivered-01.png` and on, the height a
claude-code `Read` of a PNG shows legibly at 1440 px of width; `review context` names every slice, numbered.

A page is not captured, and the output says why, when the project has no recipe `capture`, the task no `REFERENCE`,
the `REFERENCE` carries `READ`, the reference is a URL, no HTML page, outside the repository or absent from it, `COVERS`
names no section of it, a step of the recipe exits non-zero, or a screenshot exits non-zero, times out or writes no
image.

### Each head has its captures

- `brigade build pr` captures the checked head and shows each pair in the `## Captures` section of the body, which
  names that head.
- `brigade review context` names the pair of the head under review only. When that pair is missing and the worktree
  stands at that head, it captures it, then rewrites the `## Captures` section of the body: a head repaired after a
  review, or rebased, is judged against its own captures. Only that section is replaced, the attribution after it kept.
- A head is captured and hosted once: the section published for it is reused.

### Where the captures go

| Repository | Captures |
|---|---|
| public, as the forge says | hosted in a public gist of the build account, shown as images in the body |
| private, or its visibility unreadable | hosted nowhere: the body names the files in the state directory, where the review reads them |

> **Watch out:** the captures of a public repository are public, as the pull request is. Nothing of a private project
> leaves the machine.

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
- a section `reference`: each `REFERENCE` of the task with the page its `COVERS` names and its `REVISES`, then the
  numbered PNG slices of that page, the file `READ` names, or that brigade build capture wrote none, a URL printed
  refused with why, or `none`;
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
