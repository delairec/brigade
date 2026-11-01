Answers where brigade records its events and how `brigade ledger` summarises them: an overview, a wave, a project, the step budgets and a comparison of two periods.

Every event brigade records is one JSON line appended to `$XDG_STATE_HOME/brigade/ledger/<YYYY-MM>.jsonl`, the month
of its instant in UTC, under the lock `$XDG_STATE_HOME/brigade/locks/ledger.lock`; a file is never rewritten. Each line
carries `schema_version`, `ts` (ISO 8601 UTC with `Z`), `event` and the fields that event declares in
`brigade/ledger/declared_events.py`, which refuses any other name.

## Views

```
brigade ledger                                        # events by name, first and last instant, runs and segments by outcome
brigade ledger --wave <id>                            # tasks, pull requests, steps per slot and role, pauses
brigade ledger --project <name> [--since <n>d|<YYYY-MM-DD>]
brigade ledger budgets [--last N]                     # p50 and p90 steps per procedure, 20 runs by default
brigade ledger compare --before <YYYY-MM-DD>          # the runs before that day against the runs from it on
```

Every view prints text or, with `--json`, a JSON document. A line that is not JSON, lacks its envelope or carries an
unknown `schema_version` is skipped, named with its file and line on stderr and in the document, and the command still
exits 0. A run cut and resumed is one run of several segments, one `run.finished` event each: it counts once, by the
outcome and the error class of its last segment, and is dated by it. Every summary of steps gives the runs and the
segments side by side: a run is measured by the sum of its measured segments, partial when one of them is not
measured, and kept in the percentiles; a run with no measured segment is unmeasured. The steps to the first edit of a
run add the steps of the segments before the one that edited, and are partial only when one of those is not
measured. Percentiles are taken by nearest rank, and a procedure with fewer than five measured runs is marked as an
estimate. `compare` exits 1 when one of its two periods holds no finished run.
