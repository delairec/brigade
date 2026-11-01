Answers what a study is and how to record, run, schedule, list and pause one, which collectors it reads, what its answer holds and where its output goes.

A study is a `STUDY` entity of `studies.awawa` in the operational corpus: deterministic collectors, then at most one
judging run, then an output. Every command prints text or, with `--json`, a JSON document.

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

## Running a study

`study new` records the study through `awawa fmt`, `awawa lint --strict` and a commit, the question verbatim, and
runs it once unless `--every` is given. `study run` runs the steps `collect`, `judge` and `output`, each writing its
result under `runs/<id>/steps/` and the ledger events `order.started`, `step.done`, `step.failed`, `order.parked` and
`order.done` with the kind `study`; a failed step parks the study, and its next `study run` resumes that run at its
first undone step. `--slot none` makes a scan: no judging run, the answer holds the fields brigade filled.

## Schedules

`--every` takes minutes or hours, `<n>m` or `<n>h` such as `5m` or `1h`, `daily@HH:MM`, or a day of the week at an
hour, `mon@HH:MM` to `sun@HH:MM`, in the machine's timezone; `study new` refuses another form, exit 1 naming the value. A study is due when it never ran or when
its schedule has passed since its last `order.started`; a paused or archived study, or one parked at a step, is never
due, its next `study run` resuming it. Each tick runs every due study through `study run`, detached: a judging study
only while fewer than `study_runs` of `config.toml`, 2 by default, judging runs of studies are live on the machine, a
scan beyond that cap, and never a study while a run of it is live. `study_runs` below 1 is an error naming the key and
the file.

## Listing and pausing

`study list` prints every study with its status, its schedule, its last run and the outcome of that run, `started`,
`done` or `parked`; `study show` prints the fields of one study, its last run and its outcome. `study pause` and
`study resume` move its `STATUS` between `active` and `paused` through `awawa fmt`, `awawa lint --strict` and a commit,
leave a study already in that status as it is, and exit 1 for an archived study.

## Collectors

A collector line is a collector name and its `key=value` parameters, or `shell: <command line>`, whose items are the
lines the command prints. `study name=<study>` collects the answer of the last run of that study. `pr-list
state=<state>` collects the pull requests of the project, read on the forge as the login of the key `cli` of
`[forge_accounts]`, `open` by default, or `merged`, `closed` or `all`, each with its number, title, head and base
branches, state, author, draft state, review decision, the verdict of its check runs and the task its head branch
`task/<slug>/<task>` names; it reads every one of them, page after page, is collected afresh on every call, and is
absent under `FORGE none`: `brigade collect pr-list` exits 1 naming it and `brigade collectors list` prints it in its
`absent` column.

## The answer and its output

The answer is an entity of the type `--answer` names, `ANSWER` by default: brigade fills `STUDY`, `RUN` and one
`COLLECTED` per collector, its summary and the path of its full document; the judging run fills `NARRATIVE` and
`FINDING`. The judging run reads `study context <run>` and hands its answer to `study answer`, which validates it by
`awawa lint` against the schema of its type and refuses one that changed a field brigade filled. The output step
writes it:

| `--output`        | where the answer goes                                                                          |
|-------------------|------------------------------------------------------------------------------------------------|
| `entity:<TYPE>`   | appended to the operational corpus through `awawa fmt`, `awawa lint --strict` and a commit     |
| `file:<pattern>`  | committed on the branch `brigade/study-<study>-<run>` of the project, pushed with a pull request where the project has a forge; `{run}` in the pattern is the run |
| `inbox`           | recorded in the inbox as a signal of kind `study`, as [Inbox](Inbox.md) says                               |
| `issue`           | a forge issue of the project                                                                   |
| any other name    | `brigade-output-<name>` on `PATH`, given `{"schema_version", "study", "run", "markdown"}` on stdin |

Every output but `entity:` hands a person the Markdown rendered from the answer entity.
