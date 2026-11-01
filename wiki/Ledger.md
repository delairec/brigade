Where brigade records its events and how `brigade ledger` summarises them: an overview, a wave, a task, a project, the
step budgets and a comparison of two ranges of days, or of one range with reference figures.

## Views

```
brigade ledger                                        # events by name, first and last instant, runs and segments by outcome
brigade ledger --wave <id>                            # cost, tokens, steps, duration and cost per task, pull requests, pauses
brigade ledger --task <id>                            # the runs of a task: outcome, steps, duration, cost
brigade ledger --project <name>                       # waves, orders, pull requests, signals, patterns, constraints
brigade ledger budgets [--last N]                     # p50 and p90 steps per procedure, 20 runs by default
brigade ledger compare --range <start>..<end> --range <start>..<end>
brigade ledger compare --range <start>..<end> --reference <measure>=<value> ...
```

Every view prints text or, with `--json`, a JSON document. `--since <n>d|<YYYY-MM-DD>` narrows the overview, `--wave`,
`--task` and `--project` to the events from that instant on.

## Comparing ranges

A range is two days `YYYY-MM-DD` in UTC, the end day included; a run belongs to the range its last segment finished in.
`compare` sets two ranges against each other, or one range against reference figures, such as a baseline measured
before the ledger existed:

| Measure                             | What the range gives                                                |
|-------------------------------------|---------------------------------------------------------------------|
| `steps_to_first_edit_p50`           | the p50 of the steps to the first edit of its runs                  |
| `task_run_steps_p50`                | the p50 of the steps of its runs naming a task                      |
| `oversized_output_steps_per_launch` | the oversized output steps per segment reporting them, two decimals |

`--reference` is repeated once per measure, for example
`--reference steps_to_first_edit_p50=23 --reference task_run_steps_p50=47 --reference oversized_output_steps_per_launch=2.18`.

## Where events are recorded

Every event brigade records is one JSON line appended to `$XDG_STATE_HOME/brigade/ledger/<YYYY-MM>.jsonl`, the month
of its instant in UTC; a file is never rewritten. Each line carries `schema_version`, `ts` (ISO 8601 UTC with `Z`),
`event` and the fields that event declares in `brigade/ledger/declared_events.py`, which refuses any other name.

> **Watch out:** a run cut and resumed is one run of several segments, one `run.finished` event each: it counts once,
> by the outcome and the error class of its last segment, and is dated by it.

## Details and edge cases

<details><summary>Lines the views skip</summary>

A line that is not JSON, lacks its envelope or carries an unknown `schema_version` is skipped, named with its file and
line on stderr and in the document, and the command still exits 0. Lines are appended under the lock
`$XDG_STATE_HOME/brigade/locks/ledger.lock`.

</details>

<details><summary>How steps are counted</summary>

- Every summary of steps gives the runs and the segments side by side.
- A run is measured by the sum of its measured segments, partial when one of them is not measured, and kept in the
  percentiles; a run with no measured segment is unmeasured.
- The steps of a task in `--wave` sum those of its runs, partial when one of its runs is.
- The steps to the first edit of a run add the steps of the segments before the one that edited, and are partial only
  when one of those is not measured.
- The cost and the tokens of a wave, and the duration and the cost of a task or a run, sum the `run.finished` events
  that carry them; none is printed when no event does.
- Percentiles are taken by nearest rank, and a procedure with fewer than five measured runs is marked as an estimate.

</details>

<details><summary><code>compare</code> with an empty range</summary>

`compare` exits 1 when one of its ranges holds no finished run, and 2 unless it is given two `--range`, or one
`--range` and at least one `--reference`, or when two `--reference` name the same measure.

</details>
