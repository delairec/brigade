What a study is and how to record, run, schedule, list and pause one, which collectors it reads, what its answer
holds and where its output goes.

## Commands

```
brigade study new <name> --title T --output O [--question Q] [--project P] [--collector LINE ...] [--slot S] [--every E] [--answer TYPE]
brigade study run <name>
brigade study context <run>
brigade study answer <run> --file <answer.awawa>
brigade study list
brigade study show <name>
brigade study pause <name>
brigade study resume <name>
```

Every command prints text or, with `--json`, a JSON document.

## What a study does

A study is a `STUDY` entity of `studies.awawa` in the operational corpus, run in three steps:

1. `collect` — deterministic collectors gather items, without a model;
2. `judge` — at most one judging run reads `study context <run>` and hands its answer to `study answer`;
3. `output` — the answer goes where `--output` says.

`study new` records the study, the question verbatim, and runs it once unless `--every` is given. `--slot none` makes
a scan: no judging run, the answer holds the fields brigade filled.

## Schedules

| `--every` | Example |
|---|---|
| minutes or hours, `<n>m` or `<n>h` | `5m`, `1h` |
| every day at an hour, `daily@HH:MM` | `daily@07:30` |
| a day of the week at an hour, `mon@HH:MM` to `sun@HH:MM` | `mon@09:00` |

Times are in the machine's timezone. Each tick runs every due study through `study run`, detached.

## Collectors

A collector line is a collector name and its `key=value` parameters, or `shell: <command line>`, whose items are the
lines the command prints.

| Collector | Collects |
|---|---|
| `shell: <command line>` | the lines the command prints |
| `study name=<study>` | the answer of the last run of that study |
| `pr-list state=<state>` | the pull requests of the project: `open` by default, or `merged`, `closed` or `all` |

## Where the answer goes

| `--output`        | where the answer goes                                                                          |
|-------------------|------------------------------------------------------------------------------------------------|
| `entity:<TYPE>`   | appended to the operational corpus through `awawa fmt`, `awawa lint --strict` and a commit     |
| `file:<pattern>`  | committed on the branch `brigade/study-<study>-<run>` of the project, pushed with a pull request where the project has a forge; `{run}` in the pattern is the run |
| `inbox`           | recorded in the inbox as a signal of kind `study`, as [Inbox](Inbox.md) says                               |
| `issue`           | a forge issue of the project                                                                   |
| any other name    | `brigade-output-<name>` on `PATH`, given `{"schema_version", "study", "run", "markdown"}` on stdin |

Every output but `entity:` hands a person the Markdown rendered from the answer entity.

> **Watch out:** a failed step parks the study, and a parked study is never due: its next `study run` resumes that run
> at its first undone step.

## Built-in scans

A scan is a study with `SLOT none` whose output is `inbox`: it runs its collectors, no judging run, and records one
signal of kind `scan` per item they print, so that the same fact found again raises the count of one signal and a
dismissal holds. An item without a `fingerprint` key parks the run at its output step, naming the collector.

For each registered project `P`, brigade ships four scans, due once a day and listed by `study list`; a `STUDY` of the
same name in the operational corpus replaces the built-in one, `STATUS paused` included. They report and remove
nothing.

| Scan | Collector | One item per | Fingerprint of the item |
|---|---|---|---|
| `corpus_lint_P` | `corpus-lint` | diagnostic of `awawa lint --strict` on the corpus at `PROJECT.MAIN`, none without `CORPUS` | `<rule>:<file>:<TYPE.Name or none>` |
| `corpus_fmt_P` | `corpus-fmt` | file `awawa fmt --check` would rewrite at `PROJECT.MAIN` | the file |
| `stale_branches_P` | `stale-branches` | local branch, `MAIN` aside, heading at least one pull request and no open one | the branch |
| `worktrees_P` | `stale-worktrees` | linked worktree on a stale branch, on a branch that no longer exists, or detached with no live run in it | the path |


<details><summary>Steps, ledger events and resumption</summary>

`study run` runs the steps `collect`, `judge` and `output`, each writing its result under `runs/<id>/steps/` and the
ledger events `order.started`, `step.done`, `step.failed`, `order.parked` and `order.done` with the kind `study`.
`study new` records the study through `awawa fmt`, `awawa lint --strict` and a commit.

</details>

<details><summary>When a study is due, and the cap on judging runs</summary>

- `study new` refuses a schedule of another form, exit 1 naming the value.
- A study is due when it never ran or when its schedule has passed since its last `order.started`.
- A paused or archived study, or one parked at a step, is never due, its next `study run` resuming it.
- A tick runs a judging study only while fewer than `study_runs` of `config.toml`, 2 by default, judging runs of
  studies are live on the machine; a scan runs beyond that cap; and no study runs while a run of it is live.
- `study_runs` below 1 is an error naming the key and the file.

</details>

<details><summary>Listing and pausing</summary>

- `study list` prints every study with its status, its schedule, its last run and the outcome of that run, `started`,
  `done` or `parked`. `study show` prints the fields of one study, its last run and its outcome.
- `study pause` and `study resume` move its `STATUS` between `active` and `paused` through `awawa fmt`,
  `awawa lint --strict` and a commit, leave a study already in that status as it is, and exit 1 for an archived study.

</details>

<details><summary>The <code>pr-list</code> collector in detail</summary>

- It reads the pull requests on the forge as the login of the key `cli` of `[forge_accounts]`.
- Each carries its number, title, head and base branches, state, author, draft state, review decision, the verdict of
  its check runs and the task its head branch `task/<slug>/<task>` names.
- It reads every one of them, page after page, and is collected afresh on every call.
- It is absent under `FORGE none`: `brigade collect pr-list` exits 1 naming it, and `brigade collectors list` prints it
  in its `absent` column.

</details>

<details><summary>The answer entity</summary>

- The answer is an entity of the type `--answer` names, `ANSWER` by default.
- brigade fills `STUDY`, `RUN` and one `COLLECTED` per collector, its summary and the path of its full document; the
  judging run fills `NARRATIVE` and `FINDING`.
- `study answer` validates the answer by `awawa lint` against the schema of its type, and refuses one that changed a
  field brigade filled. The output step then writes it.

</details>
