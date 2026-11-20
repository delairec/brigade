How M6 was proven after the fact: the closed waves the tick delivered on brigade from 2026-11-18 to 2026-11-19, 17
tasks merged, and their turns set against the baseline of the user's notes of 2026-10-03, measured before the ledger
existed. The figures were taken on 2026-11-20 by the run of TASK B236; the page is dated and not refreshed.

## The range

- TASK B37, #309, carries the measure of the turns to the first edit; it reached `main` with M6, #371, merged on
  2026-11-07T17:51:30Z, and the tick runs from the main checkout: the `AGENTS.md` of the repository read on 2026-11-20,
  "The tick runs from the main checkout through `bin/brigade`: a fix to brigade reaches the tick once `main` is pulled
  there".
- The range opens on 2026-11-18, ten days after, and closes on 2026-11-19: it holds three waves, every one closed, and
  no other wave of a registered project started or ended in it, `brigade wave list`.

| Wave          | Started              | Closed               | Tasks merged                                                                  |
|---------------|----------------------|----------------------|-------------------------------------------------------------------------------|
| `brigade_w57` | 2026-11-18T01:00:01Z | 2026-11-18T05:50:29Z | 4: B91, B144, B231, B241                                                      |
| `brigade_w58` | 2026-11-18T22:35:27Z | 2026-11-19T12:30:27Z | 12: B197, B264, B266, B267, B268, B269, B270, B271, B272, B273, B274, B275    |
| `brigade_w59` | 2026-11-19T12:30:27Z | 2026-11-19T16:35:27Z | 1: B265, parked in `brigade_w58` past 2 repair rounds                         |

17 tasks merged in all, each by a pull request the tick merged into its milestone branch.

## Against the baseline

The baseline is the user's notes of 2026-10-03 on their largest project, 119 sessions and 217 launches by hand, which
count the agent turns as steps: turns to first edit p50 23, turns per task run p50 47, 146 oversized output turns over
67 launches, 2.18 per launch. What each measure reads, quoted from the wiki page Ledger as it stood on 2026-11-20:

| Measure                             | What the range gives                                                |
|-------------------------------------|---------------------------------------------------------------------|
| `turns_to_first_edit_p50`           | the p50 of the turns to the first edit of its runs                  |
| `task_run_turns_p50`                | the p50 of the turns of its runs naming a task                      |
| `oversized_output_turns_per_launch` | the oversized output turns per segment reporting them, two decimals |

- "A run is measured by the sum of its measured segments, partial when one of them is not measured, and kept in the
  percentiles; a run with no measured segment is unmeasured."
- "The turns to the first edit of a run add the turns of the segments before the one that edited, and are partial only
  when one of those is not measured."
- "A range is two days `YYYY-MM-DD` in UTC, the end day included; a run belongs to the range its last segment finished
  in."
- From the wiki page Runs: "The first edit of a segment is its first change to the worktree of the run outside the
  progress file, whatever tool made it".

```
brigade ledger compare --range 2026-11-18..2026-11-19 --reference turns_to_first_edit_p50=23 --reference task_run_turns_p50=47 --reference oversized_output_turns_per_launch=2.18
```

```
from 2026-11-18 to 2026-11-19: 138 runs finished, 175 segments
  turns:
    runs p50 19  p90 73  measured 138  partial 0  unmeasured 0
    segments p50 17  p90 63  measured 175  unmeasured 0
  turns to first edit:
    runs p50 22  p90 56  measured 33  partial 0  unmeasured 105
    segments p50 16  p90 32  measured 36  unmeasured 139
  oversized output turns: not reported
  turns to first edit p50: 22
  turns per task run p50: 19
  oversized output turns per launch: -
reference:
  turns to first edit p50: 23
  turns per task run p50: 47
  oversized output turns per launch: 2.18
```

| Measure                           | Baseline, by hand | 2026-11-18..2026-11-19, brigade |
|-----------------------------------|-------------------|---------------------------------|
| turns to first edit p50           | 23                | 22, over 33 runs measured       |
| turns per task run p50            | 47                | 19, over 138 runs               |
| oversized output turns per launch | 2.18              | none reported                   |

- The turns per task run count every run naming a task, its review, remediation and rebase runs among them; the
  baseline counted the agents launched on a task.
- No segment of the range reports its oversized output turns: no writer of brigade fills `oversized_output_turns` of
  `run.finished`, so the third measure has no figure on any range of the ledger.

## The waves

`brigade wave show <wave> --events` of each wave, its stderr left out.

<details><summary><code>brigade wave show brigade_w57 --events</code></summary>

```
wave brigade_w57 of @PROJECT.brigade on None, started 2026-11-18T01:00:01Z, last event wave.closed, pull request -
task  state   pull request  run                      reason
B91   merged  443           20261118T040503Z-a4c940  -
B144  merged  444           20261118T054529Z-71abc4  -
B231  merged  441           20261118T020001Z-a8f913  -
B241  merged  442           20261118T025529Z-c3b8d7  -
wave brigade_w57: 2026-11-18T01:00:01Z to 2026-11-18T05:50:29Z, wall time 4h50m
cost: 41.28 USD
tokens: input 1498, output 459296, cache creation 1998790, cache read 87600111
tasks:
  B231  turns 104  duration 0h34m  cost 6.85 USD
  B241  turns 123  duration 0h56m  cost 6.44 USD
  B91  turns 127  duration 0h47m  cost 7.17 USD
  B144  turns 415  duration 2h21m  cost 20.82 USD
pull requests: #441 B231 rounds 1, #442 B241 rounds 2, #443 B91 rounds 3, #444 B144 rounds 3
turns by slot:
  build
    runs p50 73  p90 253  measured 4  partial 0  unmeasured 0
    segments p50 65  p90 80  measured 7  unmeasured 0
  rebase
    runs p50 11  p90 16  measured 4  partial 0  unmeasured 0
    segments p50 11  p90 16  measured 4  unmeasured 0
  remediate
    runs p50 17  p90 64  measured 2  partial 0  unmeasured 0
    segments p50 17  p90 64  measured 2  unmeasured 0
  review
    runs p50 16  p90 40  measured 9  partial 0  unmeasured 0
    segments p50 16  p90 40  measured 9  unmeasured 0
turns by role:
  ada
    runs p50 73  p90 253  measured 4  partial 0  unmeasured 0
    segments p50 65  p90 80  measured 7  unmeasured 0
  prudence
    runs p50 16  p90 40  measured 9  partial 0  unmeasured 0
    segments p50 16  p90 40  measured 9  unmeasured 0
  rebaser
    runs p50 11  p90 16  measured 4  partial 0  unmeasured 0
    segments p50 11  p90 16  measured 4  unmeasured 0
  remediator
    runs p50 17  p90 64  measured 2  partial 0  unmeasured 0
    segments p50 17  p90 64  measured 2  unmeasured 0
halts: 2, 0h08m in all
  2026-11-18T01:00:01Z to 2026-11-18T01:02:38Z  0h02m
  2026-11-18T01:05:29Z to 2026-11-18T01:11:14Z  0h05m
handovers: B144 ada build segment 2, B144 ada build segment 3, B144 ada build segment 4
parked: none
events:
  2026-11-18T01:00:01Z  wave.started
  2026-11-18T01:00:01Z  wave.parked
  2026-11-18T01:02:38Z  wave.resumed
  2026-11-18T01:05:29Z  wave.parked
  2026-11-18T01:11:14Z  wave.resumed
  2026-11-18T01:15:29Z  task.state  B231
  2026-11-18T01:15:29Z  task.state  B241
  2026-11-18T01:44:44Z  task.pr_opened  B231
  2026-11-18T01:45:15Z  run.finished  B231
  2026-11-18T01:45:00Z  task.state  B231
  2026-11-18T01:46:50Z  task.pr_opened  B241
  2026-11-18T01:47:25Z  run.finished  B241
  2026-11-18T01:50:29Z  task.state  B241
  2026-11-18T02:00:01Z  task.preflighted  B231
  2026-11-18T02:00:01Z  task.state  B231
  2026-11-18T02:00:01Z  task.preflighted  B241
  2026-11-18T02:00:01Z  task.state  B241
  2026-11-18T02:05:51Z  task.verdict  B241
  2026-11-18T02:06:06Z  run.finished  B241
  2026-11-18T02:06:25Z  task.verdict  B231
  2026-11-18T02:06:45Z  run.finished  B231
  2026-11-18T02:10:29Z  task.state  B231
  2026-11-18T02:10:29Z  task.state  B241
  2026-11-18T02:10:29Z  pr.merged  B231
  2026-11-18T02:10:29Z  task.state  B231
  2026-11-18T02:10:29Z  tick.action_failed  B241
  2026-11-18T02:10:29Z  task.state  B241
  2026-11-18T02:10:29Z  task.state  B91
  2026-11-18T02:10:29Z  task.state  B144
  2026-11-18T02:29:00Z  run.finished  B144
  2026-11-18T02:36:25Z  run.finished  B144
  2026-11-18T02:39:18Z  run.finished  B241
  2026-11-18T02:40:00Z  task.rebased  B241
  2026-11-18T02:40:00Z  task.state  B241
  2026-11-18T02:43:53Z  task.pr_opened  B91
  2026-11-18T02:44:23Z  run.finished  B91
  2026-11-18T02:45:29Z  task.state  B91
  2026-11-18T02:46:28Z  run.finished  B144
  2026-11-18T02:55:29Z  task.preflighted  B91
  2026-11-18T02:55:29Z  task.state  B91
  2026-11-18T02:55:29Z  task.preflighted  B241
  2026-11-18T02:55:29Z  task.state  B241
  2026-11-18T02:57:31Z  task.verdict  B241
  2026-11-18T02:57:40Z  run.finished  B241
  2026-11-18T03:00:10Z  task.verdict  B91
  2026-11-18T03:00:24Z  run.finished  B91
  2026-11-18T03:00:01Z  task.state  B241
  2026-11-18T03:00:01Z  task.state  B91
  2026-11-18T03:00:01Z  pr.merged  B241
  2026-11-18T03:00:01Z  task.state  B241
  2026-11-18T03:00:01Z  task.state  B91
  2026-11-18T03:18:45Z  run.finished  B91
  2026-11-18T03:20:29Z  task.state  B91
  2026-11-18T03:21:19Z  task.pr_opened  B144
  2026-11-18T03:22:07Z  run.finished  B144
  2026-11-18T03:25:29Z  task.state  B144
  2026-11-18T03:25:29Z  task.state  B144
  2026-11-18T03:25:29Z  task.state  B144
  2026-11-18T03:25:29Z  task.preflighted  B144
  2026-11-18T03:35:26Z  task.preflighted  B91
  2026-11-18T03:35:26Z  task.state  B91
  2026-11-18T03:37:12Z  task.verdict  B91
  2026-11-18T03:37:20Z  run.finished  B91
  2026-11-18T03:40:00Z  task.state  B91
  2026-11-18T03:40:00Z  task.state  B91
  2026-11-18T03:45:36Z  run.finished  B144
  2026-11-18T03:50:08Z  task.review_answered  B91
  2026-11-18T03:50:17Z  run.finished  B91
  2026-11-18T03:50:03Z  task.state  B91
  2026-11-18T04:00:01Z  task.preflighted  B144
  2026-11-18T04:00:01Z  task.state  B144
  2026-11-18T04:05:03Z  task.preflighted  B91
  2026-11-18T04:05:03Z  task.state  B91
  2026-11-18T04:06:37Z  task.verdict  B91
  2026-11-18T04:06:50Z  run.finished  B91
  2026-11-18T04:10:00Z  task.state  B91
  2026-11-18T04:10:00Z  pr.merged  B91
  2026-11-18T04:10:00Z  task.state  B91
  2026-11-18T04:13:50Z  task.verdict  B144
  2026-11-18T04:14:08Z  run.finished  B144
  2026-11-18T04:15:29Z  task.state  B144
  2026-11-18T04:41:14Z  run.finished  B144
  2026-11-18T04:45:29Z  task.state  B144
  2026-11-18T04:55:29Z  task.preflighted  B144
  2026-11-18T04:55:29Z  task.state  B144
  2026-11-18T05:00:25Z  task.verdict  B144
  2026-11-18T05:00:41Z  run.finished  B144
  2026-11-18T05:05:29Z  task.state  B144
  2026-11-18T05:05:29Z  task.state  B144
  2026-11-18T05:30:16Z  task.review_answered  B144
  2026-11-18T05:30:28Z  run.finished  B144
  2026-11-18T05:30:29Z  task.state  B144
  2026-11-18T05:45:29Z  task.preflighted  B144
  2026-11-18T05:45:29Z  task.state  B144
  2026-11-18T05:49:00Z  task.verdict  B144
  2026-11-18T05:49:14Z  run.finished  B144
  2026-11-18T05:50:29Z  task.state  B144
  2026-11-18T05:50:29Z  pr.merged  B144
  2026-11-18T05:50:29Z  task.state  B144
  2026-11-18T05:50:29Z  wave.closed
```

</details>

<details><summary><code>brigade wave show brigade_w58 --events</code></summary>

```
wave brigade_w58 of @PROJECT.brigade on None, started 2026-11-18T22:35:27Z, last event wave.closed, pull request -
task  state   pull request  run                      reason
B197  merged  449           20261119T004001Z-08b04a  -
B264  merged  447           20261119T020001Z-2e4e5b  -
B265  parked  451           20261119T042933Z-c7e334  past 2 repair rounds
B266  merged  454           20261119T101000Z-dea2a6  -
B267  merged  453           20261119T082000Z-b9ce21  -
B268  merged  452           20261119T040000Z-e5776d  -
B269  merged  457           20261119T074500Z-45d755  -
B270  merged  455           20261119T091002Z-d48f08  -
B271  merged  456           20261119T065000Z-ff12fa  -
B272  merged  458           20261119T111001Z-04d614  -
B273  merged  448           20261119T001000Z-6ad177  -
B274  merged  450           20261119T031000Z-b65ddc  -
B275  merged  459           20261119T121527Z-3c4536  -
wave brigade_w58: 2026-11-18T22:35:27Z to 2026-11-19T12:30:27Z, wall time 13h55m
cost: 161.67 USD
tokens: input 6416, output 1966672, cache creation 9707843, cache read 307528367
tasks:
  B197  turns 178  duration 1h20m  cost 9.23 USD
  B264  turns 237  duration 2h13m  cost 11.99 USD
  B273  turns 155  duration 1h08m  cost 10.71 USD
  B274  turns 207  duration 2h01m  cost 11.08 USD
  B265  turns 151  duration 1h27m  cost 7.25 USD
  B266  turns 409  duration 3h38m  cost 17.34 USD
  B267  turns 292  duration 3h23m  cost 13.86 USD
  B268  turns 159  duration 1h29m  cost 8.63 USD
  B269  turns 361  duration 2h18m  cost 19.35 USD
  B270  turns 284  duration 3h25m  cost 13.66 USD
  B271  turns 188  duration 1h38m  cost 9.44 USD
  B272  turns 379  duration 5h14m  cost 13.23 USD
  B275  turns 328  duration 4h35m  cost 15.89 USD
pull requests: #448 B273 rounds 2, #449 B197 rounds 2, #447 B264 rounds 3, #450 B274 rounds 2, #452 B268 rounds 2, #456 B271 rounds 2, #457 B269 rounds 3, #453 B267 rounds 4, #455 B270 rounds 3, #454 B266 rounds 6, #458 B272 rounds 4, #459 B275 rounds 6
turns by slot:
  build
    runs p50 66  p90 112  measured 24  partial 0  unmeasured 0
    segments p50 51  p90 77  measured 30  unmeasured 0
  rebase
    runs p50 13  p90 45  measured 29  partial 0  unmeasured 0
    segments p50 11  p90 18  measured 43  unmeasured 0
  remediate
    runs p50 44  p90 77  measured 17  partial 0  unmeasured 0
    segments p50 28  p90 47  measured 27  unmeasured 0
  review
    runs p50 16  p90 26  measured 40  partial 0  unmeasured 0
    segments p50 16  p90 26  measured 40  unmeasured 0
turns by role:
  ada
    runs p50 66  p90 112  measured 24  partial 0  unmeasured 0
    segments p50 51  p90 77  measured 30  unmeasured 0
  prudence
    runs p50 16  p90 26  measured 40  partial 0  unmeasured 0
    segments p50 16  p90 26  measured 40  unmeasured 0
  rebaser
    runs p50 13  p90 45  measured 29  partial 0  unmeasured 0
    segments p50 11  p90 18  measured 43  unmeasured 0
  remediator
    runs p50 44  p90 77  measured 17  partial 0  unmeasured 0
    segments p50 28  p90 47  measured 27  unmeasured 0
halts: 1, 1h15m in all
  2026-11-19T05:15:00Z to 2026-11-19T06:30:27Z  1h15m
handovers: B264 remediator remediate segment 2, B274 remediator remediate segment 2, B266 ada build segment 2, B269 ada build segment 2, B270 ada build segment 2, B269 ada build segment 3, B268 remediator remediate segment 2, B272 ada build segment 2, B275 ada build segment 2, B267 rebaser rebase segment 2, B267 rebaser rebase segment 3, B267 rebaser rebase segment 4, B267 rebaser rebase segment 5, B271 remediator remediate segment 2, B269 remediator remediate segment 2, B275 remediator remediate segment 2, B266 remediator remediate segment 2, B270 remediator remediate segment 2, B272 remediator remediate segment 2, B267 remediator remediate segment 2, B272 rebaser rebase segment 2, B272 rebaser rebase segment 3, B272 rebaser rebase segment 4, B272 rebaser rebase segment 5, B275 rebaser rebase segment 2, B272 rebaser rebase segment 2, B272 rebaser rebase segment 3, B272 rebaser rebase segment 4, B275 rebaser rebase segment 2, B275 rebaser rebase segment 3
parked: B264, B197, B265
events:
  2026-11-18T22:35:27Z  wave.started
  2026-11-18T22:35:27Z  task.state  B197
  2026-11-18T22:35:27Z  task.state  B264
  2026-11-18T22:35:27Z  task.state  B273
  2026-11-18T23:05:33Z  task.pr_opened  B264
  2026-11-18T23:06:00Z  run.finished  B264
  2026-11-18T23:10:00Z  task.state  B264
  2026-11-18T23:10:46Z  task.pr_opened  B273
  2026-11-18T23:11:15Z  run.finished  B273
  2026-11-18T23:15:01Z  task.state  B273
  2026-11-18T23:17:08Z  task.pr_opened  B197
  2026-11-18T23:17:36Z  run.finished  B197
  2026-11-18T23:20:27Z  task.state  B197
  2026-11-18T23:20:27Z  task.preflighted  B264
  2026-11-18T23:20:27Z  task.state  B264
  2026-11-18T23:25:27Z  task.preflighted  B273
  2026-11-18T23:25:27Z  task.state  B273
  2026-11-18T23:34:46Z  task.verdict  B273
  2026-11-18T23:35:00Z  run.finished  B273
  2026-11-18T23:35:00Z  task.preflighted  B197
  2026-11-18T23:35:00Z  task.state  B273
  2026-11-18T23:35:00Z  task.state  B197
  2026-11-18T23:35:00Z  task.state  B273
  2026-11-18T23:36:10Z  run.finished  B264
  2026-11-18T23:40:00Z  task.state  B264
  2026-11-18T23:41:29Z  run.finished  B264
  2026-11-18T23:45:01Z  task.parked  B264
  2026-11-18T23:47:02Z  task.state  B264
  2026-11-18T23:50:02Z  task.preflighted  B264
  2026-11-18T23:50:02Z  task.state  B264
  2026-11-18T23:50:34Z  run.finished  B197
  2026-11-18T23:50:02Z  task.state  B197
  2026-11-18T23:57:46Z  task.review_answered  B273
  2026-11-18T23:57:59Z  run.finished  B273
  2026-11-19T00:00:18Z  task.verdict  B264
  2026-11-19T00:00:34Z  run.finished  B264
  2026-11-19T00:00:02Z  task.state  B273
  2026-11-19T00:00:02Z  task.state  B264
  2026-11-19T00:00:02Z  task.state  B264
  2026-11-19T00:04:06Z  run.finished  B197
  2026-11-19T00:05:00Z  task.parked  B197
  2026-11-19T00:06:46Z  task.state  B197
  2026-11-19T00:10:00Z  task.preflighted  B197
  2026-11-19T00:10:00Z  task.state  B197
  2026-11-19T00:10:00Z  task.preflighted  B273
  2026-11-19T00:10:00Z  task.state  B273
  2026-11-19T00:12:26Z  task.verdict  B197
  2026-11-19T00:12:44Z  run.finished  B197
  2026-11-19T00:14:50Z  task.verdict  B273
  2026-11-19T00:15:03Z  run.finished  B273
  2026-11-19T00:15:00Z  task.state  B197
  2026-11-19T00:15:00Z  task.state  B273
  2026-11-19T00:15:00Z  task.state  B197
  2026-11-19T00:15:00Z  pr.merged  B273
  2026-11-19T00:15:00Z  task.state  B273
  2026-11-19T00:15:00Z  task.state  B274
  2026-11-19T00:26:00Z  task.review_answered  B197
  2026-11-19T00:26:09Z  run.finished  B197
  2026-11-19T00:30:00Z  task.state  B197
  2026-11-19T00:31:30Z  run.finished  B264
  2026-11-19T00:40:32Z  task.review_answered  B264
  2026-11-19T00:40:01Z  task.preflighted  B197
  2026-11-19T00:40:01Z  task.state  B197
  2026-11-19T00:40:44Z  run.finished  B264
  2026-11-19T00:40:01Z  task.state  B264
  2026-11-19T00:41:58Z  task.verdict  B197
  2026-11-19T00:42:10Z  run.finished  B197
  2026-11-19T00:45:00Z  task.state  B197
  2026-11-19T00:45:00Z  pr.merged  B197
  2026-11-19T00:45:00Z  task.state  B197
  2026-11-19T00:49:51Z  task.pr_opened  B274
  2026-11-19T00:50:33Z  run.finished  B274
  2026-11-19T00:50:05Z  task.state  B264
  2026-11-19T00:50:05Z  task.state  B274
  2026-11-19T00:50:05Z  task.state  B264
  2026-11-19T00:50:05Z  task.preflighted  B264
  2026-11-19T01:00:50Z  task.state  B274
  2026-11-19T01:00:50Z  task.state  B274
  2026-11-19T01:00:50Z  task.preflighted  B274
  2026-11-19T01:16:16Z  run.finished  B264
  2026-11-19T01:18:46Z  run.finished  B274
  2026-11-19T01:20:27Z  task.rebased  B274
  2026-11-19T01:20:27Z  task.state  B274
  2026-11-19T01:30:02Z  task.preflighted  B264
  2026-11-19T01:30:02Z  task.state  B264
  2026-11-19T01:32:30Z  task.verdict  B264
  2026-11-19T01:32:43Z  run.finished  B264
  2026-11-19T01:35:27Z  task.state  B264
  2026-11-19T01:35:27Z  task.preflighted  B274
  2026-11-19T01:35:27Z  task.state  B264
  2026-11-19T01:35:27Z  task.state  B274
  2026-11-19T01:48:23Z  run.finished  B274
  2026-11-19T01:48:46Z  task.review_answered  B264
  2026-11-19T01:48:56Z  run.finished  B264
  2026-11-19T01:50:27Z  task.state  B264
  2026-11-19T01:50:27Z  task.state  B274
  2026-11-19T02:00:01Z  task.preflighted  B274
  2026-11-19T02:00:01Z  task.state  B274
  2026-11-19T02:00:01Z  task.preflighted  B264
  2026-11-19T02:00:01Z  task.state  B264
  2026-11-19T02:11:32Z  task.verdict  B264
  2026-11-19T02:11:43Z  run.finished  B264
  2026-11-19T02:12:13Z  task.verdict  B274
  2026-11-19T02:12:27Z  run.finished  B274
  2026-11-19T02:15:27Z  task.state  B264
  2026-11-19T02:15:27Z  task.state  B274
  2026-11-19T02:15:27Z  pr.merged  B264
  2026-11-19T02:15:27Z  task.state  B264
  2026-11-19T02:15:27Z  task.state  B274
  2026-11-19T02:15:27Z  task.state  B265
  2026-11-19T02:15:27Z  task.state  B266
  2026-11-19T02:15:27Z  task.state  B267
  2026-11-19T02:15:27Z  task.state  B268
  2026-11-19T02:26:11Z  run.finished  B266
  2026-11-19T02:43:15Z  task.pr_opened  B265
  2026-11-19T02:43:41Z  task.pr_opened  B268
  2026-11-19T02:43:47Z  run.finished  B265
  2026-11-19T02:44:11Z  run.finished  B268
  2026-11-19T02:45:00Z  task.state  B265
  2026-11-19T02:45:00Z  task.state  B268
  2026-11-19T02:45:00Z  task.state  B269
  2026-11-19T02:45:00Z  task.state  B270
  2026-11-19T02:48:01Z  task.pr_opened  B267
  2026-11-19T02:48:09Z  run.finished  B274
  2026-11-19T02:48:32Z  run.finished  B267
  2026-11-19T02:50:00Z  task.state  B267
  2026-11-19T02:50:00Z  task.state  B271
  2026-11-19T02:50:47Z  run.finished  B269
  2026-11-19T02:55:00Z  task.preflighted  B268
  2026-11-19T02:55:00Z  task.state  B268
  2026-11-19T02:57:26Z  task.review_answered  B274
  2026-11-19T02:57:40Z  run.finished  B274
  2026-11-19T02:58:55Z  task.verdict  B268
  2026-11-19T02:59:01Z  run.finished  B270
  2026-11-19T02:59:09Z  run.finished  B268
  2026-11-19T03:00:00Z  task.preflighted  B265
  2026-11-19T03:00:00Z  task.state  B265
  2026-11-19T03:00:00Z  task.state  B268
  2026-11-19T03:00:00Z  task.state  B274
  2026-11-19T03:00:00Z  task.state  B268
  2026-11-19T03:02:08Z  task.pr_opened  B266
  2026-11-19T03:02:38Z  run.finished  B266
  2026-11-19T03:05:06Z  task.verdict  B265
  2026-11-19T03:05:21Z  run.finished  B265
  2026-11-19T03:05:00Z  task.state  B266
  2026-11-19T03:05:00Z  task.preflighted  B267
  2026-11-19T03:05:00Z  task.state  B267
  2026-11-19T03:05:00Z  task.state  B272
  2026-11-19T03:05:00Z  task.state  B265
  2026-11-19T03:05:00Z  task.state  B265
  2026-11-19T03:10:00Z  task.preflighted  B274
  2026-11-19T03:10:00Z  task.state  B274
  2026-11-19T03:12:05Z  run.finished  B269
  2026-11-19T03:17:06Z  task.review_answered  B265
  2026-11-19T03:17:13Z  run.finished  B265
  2026-11-19T03:17:14Z  task.verdict  B274
  2026-11-19T03:17:30Z  run.finished  B274
  2026-11-19T03:18:10Z  task.pr_opened  B270
  2026-11-19T03:18:38Z  run.finished  B270
  2026-11-19T03:20:36Z  task.pr_opened  B271
  2026-11-19T03:20:00Z  task.state  B265
  2026-11-19T03:20:00Z  task.preflighted  B266
  2026-11-19T03:20:00Z  task.state  B266
  2026-11-19T03:20:00Z  task.state  B270
  2026-11-19T03:20:00Z  task.state  B274
  2026-11-19T03:21:07Z  run.finished  B271
  2026-11-19T03:20:00Z  task.state  B271
  2026-11-19T03:20:00Z  pr.merged  B274
  2026-11-19T03:20:00Z  task.state  B274
  2026-11-19T03:21:33Z  run.finished  B272
  2026-11-19T03:20:00Z  task.state  B275
  2026-11-19T03:28:58Z  task.verdict  B267
  2026-11-19T03:28:59Z  task.verdict  B266
  2026-11-19T03:29:12Z  run.finished  B266
  2026-11-19T03:29:12Z  run.finished  B267
  2026-11-19T03:32:04Z  run.finished  B268
  2026-11-19T03:37:10Z  task.pr_opened  B269
  2026-11-19T03:37:41Z  run.finished  B269
  2026-11-19T03:30:00Z  task.state  B265
  2026-11-19T03:30:00Z  task.state  B266
  2026-11-19T03:30:00Z  task.state  B267
  2026-11-19T03:30:00Z  task.state  B265
  2026-11-19T03:30:00Z  task.state  B269
  2026-11-19T03:30:00Z  task.preflighted  B270
  2026-11-19T03:30:00Z  task.state  B271
  2026-11-19T03:30:00Z  task.preflighted  B265
  2026-11-19T03:30:00Z  task.state  B270
  2026-11-19T03:30:00Z  task.state  B271
  2026-11-19T03:30:00Z  task.preflighted  B271
  2026-11-19T03:42:36Z  task.state  B269
  2026-11-19T03:42:36Z  task.state  B269
  2026-11-19T03:42:36Z  task.preflighted  B269
  2026-11-19T03:51:51Z  task.review_answered  B268
  2026-11-19T03:52:02Z  run.finished  B268
  2026-11-19T03:52:44Z  run.finished  B270
  2026-11-19T03:55:13Z  run.finished  B275
  2026-11-19T03:55:00Z  task.state  B268
  2026-11-19T03:55:00Z  task.state  B270
  2026-11-19T03:58:14Z  task.pr_opened  B272
  2026-11-19T03:58:42Z  run.finished  B265
  2026-11-19T03:58:44Z  run.finished  B266
  2026-11-19T03:58:46Z  run.finished  B267
  2026-11-19T03:58:50Z  run.finished  B272
  2026-11-19T03:59:32Z  run.finished  B271
  2026-11-19T04:00:00Z  task.rebased  B265
  2026-11-19T04:00:00Z  task.state  B265
  2026-11-19T04:00:00Z  task.rebased  B266
  2026-11-19T04:00:00Z  task.state  B266
  2026-11-19T04:00:00Z  task.rebased  B271
  2026-11-19T04:00:00Z  task.state  B271
  2026-11-19T04:00:00Z  task.state  B272
  2026-11-19T04:00:00Z  task.state  B272
  2026-11-19T04:02:20Z  run.finished  B269
  2026-11-19T04:00:00Z  task.preflighted  B270
  2026-11-19T04:00:00Z  task.state  B270
  2026-11-19T04:00:00Z  task.state  B272
  2026-11-19T04:00:00Z  task.rebased  B269
  2026-11-19T04:00:00Z  task.state  B269
  2026-11-19T04:00:00Z  task.preflighted  B272
  2026-11-19T04:00:00Z  task.preflighted  B268
  2026-11-19T04:00:00Z  task.state  B268
  2026-11-19T04:07:04Z  task.verdict  B270
  2026-11-19T04:07:15Z  run.finished  B270
  2026-11-19T04:10:00Z  task.state  B270
  2026-11-19T04:10:00Z  task.state  B270
  2026-11-19T04:12:28Z  task.pr_opened  B275
  2026-11-19T04:12:58Z  run.finished  B275
  2026-11-19T04:13:58Z  task.verdict  B268
  2026-11-19T04:14:09Z  run.finished  B268
  2026-11-19T04:15:00Z  task.preflighted  B265
  2026-11-19T04:15:00Z  task.preflighted  B266
  2026-11-19T04:15:00Z  task.state  B266
  2026-11-19T04:15:00Z  task.state  B268
  2026-11-19T04:15:00Z  task.state  B275
  2026-11-19T04:16:29Z  run.finished  B267
  2026-11-19T04:15:00Z  task.state  B265
  2026-11-19T04:15:00Z  pr.merged  B268
  2026-11-19T04:15:00Z  task.state  B268
  2026-11-19T04:15:00Z  task.preflighted  B269
  2026-11-19T04:15:00Z  task.preflighted  B271
  2026-11-19T04:17:13Z  task.verdict  B266
  2026-11-19T04:17:26Z  run.finished  B266
  2026-11-19T04:15:00Z  task.state  B269
  2026-11-19T04:18:00Z  run.finished  B272
  2026-11-19T04:26:09Z  run.finished  B265
  2026-11-19T04:15:00Z  task.state  B271
  2026-11-19T04:15:00Z  task.state  B265
  2026-11-19T04:15:00Z  task.state  B266
  2026-11-19T04:15:00Z  task.state  B272
  2026-11-19T04:15:00Z  task.preflighted  B275
  2026-11-19T04:15:00Z  task.state  B272
  2026-11-19T04:15:00Z  task.state  B275
  2026-11-19T04:15:00Z  task.preflighted  B272
  2026-11-19T04:29:35Z  run.finished  B269
  2026-11-19T04:29:33Z  task.state  B265
  2026-11-19T04:29:33Z  task.state  B269
  2026-11-19T04:29:33Z  task.state  B265
  2026-11-19T04:29:33Z  task.preflighted  B265
  2026-11-19T04:34:38Z  task.review_answered  B270
  2026-11-19T04:34:47Z  run.finished  B270
  2026-11-19T04:35:17Z  run.finished  B267
  2026-11-19T04:35:00Z  task.state  B270
  2026-11-19T04:38:54Z  run.finished  B272
  2026-11-19T04:40:23Z  run.finished  B275
  2026-11-19T04:40:00Z  task.state  B270
  2026-11-19T04:40:00Z  task.state  B275
  2026-11-19T04:40:00Z  task.state  B270
  2026-11-19T04:40:00Z  task.preflighted  B270
  2026-11-19T04:44:55Z  run.finished  B271
  2026-11-19T04:45:00Z  task.preflighted  B269
  2026-11-19T04:45:00Z  task.state  B269
  2026-11-19T04:45:00Z  task.rebased  B271
  2026-11-19T04:45:00Z  task.state  B271
  2026-11-19T04:46:05Z  run.finished  B266
  2026-11-19T04:45:00Z  task.rebased  B266
  2026-11-19T04:45:00Z  task.state  B266
  2026-11-19T04:48:27Z  task.verdict  B269
  2026-11-19T04:48:33Z  run.finished  B265
  2026-11-19T04:48:39Z  run.finished  B269
  2026-11-19T04:50:00Z  task.rebased  B265
  2026-11-19T04:50:00Z  task.state  B265
  2026-11-19T04:50:00Z  task.state  B269
  2026-11-19T04:50:00Z  task.state  B269
  2026-11-19T04:50:00Z  task.preflighted  B272
  2026-11-19T04:50:00Z  task.state  B272
  2026-11-19T04:50:00Z  task.preflighted  B275
  2026-11-19T04:50:00Z  task.state  B275
  2026-11-19T04:53:52Z  run.finished  B267
  2026-11-19T04:54:49Z  task.verdict  B272
  2026-11-19T04:55:07Z  run.finished  B272
  2026-11-19T04:55:00Z  task.state  B272
  2026-11-19T04:55:00Z  task.state  B272
  2026-11-19T04:58:42Z  run.finished  B270
  2026-11-19T05:00:00Z  task.state  B270
  2026-11-19T05:00:00Z  task.preflighted  B271
  2026-11-19T05:00:00Z  task.state  B271
  2026-11-19T05:00:00Z  task.preflighted  B266
  2026-11-19T05:00:00Z  task.state  B266
  2026-11-19T05:02:37Z  task.verdict  B266
  2026-11-19T05:02:48Z  run.finished  B266
  2026-11-19T05:04:32Z  task.verdict  B271
  2026-11-19T05:04:48Z  run.finished  B271
  2026-11-19T05:05:00Z  task.preflighted  B265
  2026-11-19T05:05:00Z  task.state  B266
  2026-11-19T05:05:00Z  task.state  B271
  2026-11-19T05:05:00Z  task.parked  B265
  2026-11-19T05:05:00Z  task.state  B266
  2026-11-19T05:05:00Z  task.state  B271
  2026-11-19T05:07:57Z  task.review_answered  B272
  2026-11-19T05:08:06Z  run.finished  B272
  2026-11-19T05:08:18Z  task.verdict  B275
  2026-11-19T05:08:34Z  run.finished  B275
  2026-11-19T05:10:00Z  task.state  B272
  2026-11-19T05:10:00Z  task.state  B275
  2026-11-19T05:10:00Z  task.state  B275
  2026-11-19T05:12:12Z  run.finished  B267
  2026-11-19T05:12:57Z  run.finished  B269
  2026-11-19T05:15:00Z  wave.blocked
  2026-11-19T05:15:00Z  task.state  B269
  2026-11-19T05:17:44Z  run.finished  B266
  2026-11-19T05:19:28Z  run.finished  B270
  2026-11-19T05:20:02Z  task.state  B266
  2026-11-19T05:20:02Z  task.state  B270
  2026-11-19T05:20:42Z  run.finished  B271
  2026-11-19T05:20:02Z  task.preflighted  B272
  2026-11-19T05:20:02Z  task.state  B272
  2026-11-19T05:20:55Z  run.finished  B275
  2026-11-19T05:20:02Z  task.state  B271
  2026-11-19T05:20:02Z  task.state  B275
  2026-11-19T06:30:27Z  wave.resumed
  2026-11-19T06:30:27Z  task.state  B266
  2026-11-19T06:30:27Z  task.state  B269
  2026-11-19T06:30:27Z  task.state  B270
  2026-11-19T06:30:27Z  task.state  B271
  2026-11-19T06:30:27Z  task.state  B275
  2026-11-19T06:30:27Z  task.rebased  B267
  2026-11-19T06:30:27Z  task.state  B267
  2026-11-19T06:32:18Z  task.verdict  B272
  2026-11-19T06:32:30Z  run.finished  B272
  2026-11-19T06:35:00Z  task.state  B272
  2026-11-19T06:35:00Z  task.state  B272
  2026-11-19T06:40:42Z  task.review_answered  B271
  2026-11-19T06:40:53Z  run.finished  B271
  2026-11-19T06:41:17Z  task.review_answered  B269
  2026-11-19T06:41:30Z  run.finished  B269
  2026-11-19T06:45:00Z  task.preflighted  B267
  2026-11-19T06:45:00Z  task.state  B267
  2026-11-19T06:45:00Z  task.state  B269
  2026-11-19T06:45:00Z  task.state  B271
  2026-11-19T06:47:08Z  task.verdict  B267
  2026-11-19T06:47:20Z  run.finished  B267
  2026-11-19T06:49:32Z  task.review_answered  B275
  2026-11-19T06:49:43Z  run.finished  B275
  2026-11-19T06:50:00Z  task.state  B267
  2026-11-19T06:50:00Z  task.state  B275
  2026-11-19T06:50:00Z  task.state  B267
  2026-11-19T06:50:00Z  task.preflighted  B271
  2026-11-19T06:50:00Z  task.state  B271
  2026-11-19T06:54:32Z  task.verdict  B271
  2026-11-19T06:54:43Z  run.finished  B271
  2026-11-19T06:55:00Z  task.preflighted  B269
  2026-11-19T06:55:00Z  task.state  B269
  2026-11-19T06:55:00Z  task.state  B271
  2026-11-19T06:55:00Z  pr.merged  B271
  2026-11-19T06:55:00Z  task.state  B271
  2026-11-19T06:58:21Z  task.review_answered  B266
  2026-11-19T06:58:33Z  run.finished  B266
  2026-11-19T06:58:43Z  task.verdict  B269
  2026-11-19T06:58:58Z  run.finished  B269
  2026-11-19T07:00:00Z  task.state  B266
  2026-11-19T07:02:20Z  run.finished  B270
  2026-11-19T07:07:51Z  run.finished  B272
  2026-11-19T07:00:00Z  task.state  B266
  2026-11-19T07:00:00Z  task.state  B269
  2026-11-19T07:00:00Z  task.state  B266
  2026-11-19T07:00:00Z  task.state  B270
  2026-11-19T07:00:00Z  task.state  B275
  2026-11-19T07:00:00Z  task.preflighted  B266
  2026-11-19T07:00:00Z  task.state  B275
  2026-11-19T07:00:00Z  task.preflighted  B275
  2026-11-19T07:12:49Z  task.review_answered  B267
  2026-11-19T07:12:33Z  task.state  B267
  2026-11-19T07:15:00Z  task.preflighted  B267
  2026-11-19T07:19:04Z  task.review_answered  B272
  2026-11-19T07:19:12Z  run.finished  B272
  2026-11-19T07:20:02Z  task.state  B272
  2026-11-19T07:22:38Z  run.finished  B267
  2026-11-19T07:22:59Z  task.review_answered  B267
  2026-11-19T07:23:14Z  run.finished  B267
  2026-11-19T07:25:00Z  task.state  B267
  2026-11-19T07:27:56Z  run.finished  B266
  2026-11-19T07:27:57Z  run.finished  B269
  2026-11-19T07:28:29Z  run.finished  B270
  2026-11-19T07:28:43Z  run.finished  B275
  2026-11-19T07:30:00Z  task.rebased  B269
  2026-11-19T07:30:00Z  task.state  B269
  2026-11-19T07:30:00Z  task.rebased  B270
  2026-11-19T07:30:00Z  task.state  B270
  2026-11-19T07:30:00Z  task.preflighted  B272
  2026-11-19T07:30:00Z  task.state  B272
  2026-11-19T07:30:00Z  task.rebased  B275
  2026-11-19T07:30:00Z  task.state  B275
  2026-11-19T07:32:32Z  task.verdict  B272
  2026-11-19T07:32:43Z  run.finished  B272
  2026-11-19T07:35:13Z  task.state  B272
  2026-11-19T07:36:30Z  run.finished  B267
  2026-11-19T07:35:13Z  task.state  B267
  2026-11-19T07:35:13Z  task.state  B272
  2026-11-19T07:45:00Z  task.preflighted  B266
  2026-11-19T07:45:00Z  task.state  B266
  2026-11-19T07:45:00Z  task.preflighted  B269
  2026-11-19T07:45:00Z  task.state  B269
  2026-11-19T07:45:00Z  task.preflighted  B275
  2026-11-19T07:45:00Z  task.state  B275
  2026-11-19T07:45:00Z  task.preflighted  B270
  2026-11-19T07:45:00Z  task.state  B270
  2026-11-19T07:46:56Z  task.verdict  B269
  2026-11-19T07:47:04Z  task.verdict  B275
  2026-11-19T07:47:06Z  run.finished  B269
  2026-11-19T07:45:00Z  task.preflighted  B267
  2026-11-19T07:45:00Z  task.state  B267
  2026-11-19T07:47:07Z  task.review_answered  B272
  2026-11-19T07:47:12Z  run.finished  B272
  2026-11-19T07:47:14Z  run.finished  B275
  2026-11-19T07:45:00Z  task.state  B269
  2026-11-19T07:45:00Z  task.state  B272
  2026-11-19T07:45:00Z  task.state  B275
  2026-11-19T07:45:00Z  pr.merged  B269
  2026-11-19T07:45:00Z  task.state  B269
  2026-11-19T07:45:00Z  tick.action_failed  B275
  2026-11-19T07:48:53Z  task.verdict  B267
  2026-11-19T07:49:06Z  run.finished  B267
  2026-11-19T07:50:00Z  task.verdict  B266
  2026-11-19T07:50:11Z  run.finished  B266
  2026-11-19T07:56:16Z  task.verdict  B270
  2026-11-19T07:56:26Z  run.finished  B270
  2026-11-19T07:45:00Z  task.state  B275
  2026-11-19T07:45:00Z  task.state  B266
  2026-11-19T07:45:00Z  task.state  B267
  2026-11-19T07:45:00Z  task.state  B270
  2026-11-19T08:05:00Z  task.state  B272
  2026-11-19T08:05:00Z  task.state  B272
  2026-11-19T08:05:00Z  task.preflighted  B272
  2026-11-19T08:09:57Z  run.finished  B267
  2026-11-19T08:10:00Z  task.state  B267
  2026-11-19T08:16:24Z  run.finished  B275
  2026-11-19T08:17:27Z  run.finished  B270
  2026-11-19T08:17:46Z  run.finished  B266
  2026-11-19T08:20:00Z  task.rebased  B266
  2026-11-19T08:20:00Z  task.state  B266
  2026-11-19T08:20:00Z  task.rebased  B270
  2026-11-19T08:20:00Z  task.state  B270
  2026-11-19T08:20:00Z  task.rebased  B275
  2026-11-19T08:20:00Z  task.state  B275
  2026-11-19T08:20:00Z  task.preflighted  B267
  2026-11-19T08:20:00Z  task.state  B267
  2026-11-19T08:23:23Z  task.verdict  B267
  2026-11-19T08:23:35Z  run.finished  B267
  2026-11-19T08:24:41Z  run.finished  B272
  2026-11-19T08:25:27Z  task.state  B267
  2026-11-19T08:25:27Z  pr.merged  B267
  2026-11-19T08:25:27Z  task.state  B267
  2026-11-19T08:43:42Z  run.finished  B272
  2026-11-19T08:35:27Z  task.state  B266
  2026-11-19T08:35:27Z  task.state  B270
  2026-11-19T08:35:27Z  task.state  B275
  2026-11-19T08:35:27Z  task.state  B266
  2026-11-19T08:35:27Z  task.state  B270
  2026-11-19T08:35:27Z  task.state  B275
  2026-11-19T08:35:27Z  task.preflighted  B266
  2026-11-19T08:35:27Z  task.preflighted  B270
  2026-11-19T08:35:27Z  task.preflighted  B275
  2026-11-19T08:55:13Z  run.finished  B270
  2026-11-19T09:02:42Z  run.finished  B272
  2026-11-19T09:02:57Z  run.finished  B266
  2026-11-19T09:03:44Z  run.finished  B275
  2026-11-19T09:05:00Z  task.rebased  B266
  2026-11-19T09:05:00Z  task.state  B266
  2026-11-19T09:05:00Z  task.rebased  B275
  2026-11-19T09:05:00Z  task.state  B275
  2026-11-19T09:10:02Z  task.preflighted  B270
  2026-11-19T09:10:02Z  task.state  B270
  2026-11-19T09:20:00Z  task.preflighted  B266
  2026-11-19T09:20:00Z  task.state  B266
  2026-11-19T09:20:00Z  task.preflighted  B275
  2026-11-19T09:20:00Z  task.state  B275
  2026-11-19T09:20:49Z  task.verdict  B270
  2026-11-19T09:21:00Z  run.finished  B270
  2026-11-19T09:21:43Z  run.finished  B272
  2026-11-19T09:20:00Z  task.state  B270
  2026-11-19T09:22:05Z  task.verdict  B266
  2026-11-19T09:22:14Z  run.finished  B266
  2026-11-19T09:20:00Z  pr.merged  B270
  2026-11-19T09:20:00Z  task.state  B270
  2026-11-19T09:30:41Z  task.verdict  B275
  2026-11-19T09:30:53Z  run.finished  B275
  2026-11-19T09:20:00Z  task.state  B266
  2026-11-19T09:20:00Z  task.state  B275
  2026-11-19T09:40:43Z  run.finished  B272
  2026-11-19T09:45:00Z  task.state  B272
  2026-11-19T09:50:50Z  run.finished  B266
  2026-11-19T09:51:15Z  run.finished  B275
  2026-11-19T09:55:00Z  task.rebased  B266
  2026-11-19T09:55:00Z  task.state  B266
  2026-11-19T10:00:33Z  run.finished  B275
  2026-11-19T10:00:01Z  task.state  B272
  2026-11-19T10:00:01Z  task.state  B275
  2026-11-19T10:04:43Z  run.finished  B272
  2026-11-19T10:10:00Z  task.preflighted  B266
  2026-11-19T10:10:00Z  task.state  B266
  2026-11-19T10:15:00Z  task.preflighted  B272
  2026-11-19T10:15:00Z  task.state  B272
  2026-11-19T10:15:00Z  task.preflighted  B275
  2026-11-19T10:15:00Z  task.state  B275
  2026-11-19T10:17:09Z  task.verdict  B275
  2026-11-19T10:17:18Z  run.finished  B275
  2026-11-19T10:20:15Z  task.verdict  B266
  2026-11-19T10:20:25Z  run.finished  B266
  2026-11-19T10:20:26Z  task.state  B266
  2026-11-19T10:20:26Z  task.state  B275
  2026-11-19T10:20:26Z  pr.merged  B266
  2026-11-19T10:20:26Z  task.state  B266
  2026-11-19T10:20:26Z  tick.action_failed  B275
  2026-11-19T10:23:44Z  run.finished  B272
  2026-11-19T10:20:26Z  task.state  B275
  2026-11-19T10:42:44Z  run.finished  B272
  2026-11-19T10:48:48Z  run.finished  B275
  2026-11-19T10:50:00Z  task.rebased  B275
  2026-11-19T10:50:00Z  task.state  B275
  2026-11-19T10:53:37Z  run.finished  B272
  2026-11-19T10:55:27Z  task.state  B272
  2026-11-19T11:05:27Z  task.preflighted  B275
  2026-11-19T11:05:27Z  task.state  B275
  2026-11-19T11:10:01Z  task.preflighted  B272
  2026-11-19T11:10:01Z  task.state  B272
  2026-11-19T11:11:51Z  task.verdict  B272
  2026-11-19T11:12:00Z  run.finished  B272
  2026-11-19T11:15:34Z  task.verdict  B275
  2026-11-19T11:15:44Z  run.finished  B275
  2026-11-19T11:15:11Z  task.state  B272
  2026-11-19T11:15:11Z  pr.merged  B272
  2026-11-19T11:15:11Z  task.state  B272
  2026-11-19T11:15:11Z  task.state  B275
  2026-11-19T11:15:11Z  task.state  B275
  2026-11-19T11:46:31Z  run.finished  B275
  2026-11-19T12:00:01Z  task.state  B275
  2026-11-19T12:05:32Z  run.finished  B275
  2026-11-19T12:05:41Z  run.finished  B275
  2026-11-19T12:15:27Z  task.preflighted  B275
  2026-11-19T12:15:27Z  task.state  B275
  2026-11-19T12:27:24Z  task.verdict  B275
  2026-11-19T12:27:32Z  run.finished  B275
  2026-11-19T12:30:27Z  task.state  B275
  2026-11-19T12:30:27Z  pr.merged  B275
  2026-11-19T12:30:27Z  task.state  B275
  2026-11-19T12:30:27Z  wave.closed
```

</details>

<details><summary><code>brigade wave show brigade_w59 --events</code></summary>

```
wave brigade_w59 of @PROJECT.brigade on None, started 2026-11-19T12:30:27Z, last event wave.closed, pull request -
task  state   pull request  run                      reason
B265  merged  451           20261119T163027Z-5e36e3  -
wave brigade_w59: 2026-11-19T12:30:27Z to 2026-11-19T16:35:27Z, wall time 4h05m
cost: 4.67 USD
tokens: input 302, output 51763, cache creation 505815, cache read 8935315
tasks:
  B265  turns 151  duration 2h44m  cost 4.67 USD
pull requests: #451 B265 rounds 2
turns by slot:
  build
    runs p50 12  p90 21  measured 2  partial 0  unmeasured 0
    segments p50 12  p90 21  measured 2  unmeasured 0
  rebase
    runs p50 64  p90 64  measured 1  partial 0  unmeasured 0
    segments p50 7  p90 30  measured 5  unmeasured 0
  remediate
    runs p50 24  p90 24  measured 1  partial 0  unmeasured 0
    segments p50 24  p90 24  measured 1  unmeasured 0
  review
    runs p50 9  p90 21  measured 2  partial 0  unmeasured 0
    segments p50 9  p90 21  measured 2  unmeasured 0
turns by role:
  ada
    runs p50 12  p90 21  measured 2  partial 0  unmeasured 0
    segments p50 12  p90 21  measured 2  unmeasured 0
  prudence
    runs p50 9  p90 21  measured 2  partial 0  unmeasured 0
    segments p50 9  p90 21  measured 2  unmeasured 0
  rebaser
    runs p50 64  p90 64  measured 1  partial 0  unmeasured 0
    segments p50 7  p90 30  measured 5  unmeasured 0
  remediator
    runs p50 24  p90 24  measured 1  partial 0  unmeasured 0
    segments p50 24  p90 24  measured 1  unmeasured 0
halts: 0, 0h00m in all
handovers: B265 rebaser rebase segment 2, B265 rebaser rebase segment 3, B265 rebaser rebase segment 4, B265 rebaser rebase segment 5
parked: none
events:
  2026-11-19T12:30:27Z  wave.started
  2026-11-19T12:30:27Z  task.state  B265
  2026-11-19T12:30:27Z  task.state  B265
  2026-11-19T12:30:27Z  task.pr_opened  B265
  2026-11-19T12:30:27Z  task.preflighted  B265
  2026-11-19T13:01:00Z  run.finished  B265
  2026-11-19T13:05:27Z  task.state  B265
  2026-11-19T13:05:27Z  task.state  B265
  2026-11-19T13:05:27Z  task.preflighted  B265
  2026-11-19T13:35:25Z  run.finished  B265
  2026-11-19T13:54:25Z  run.finished  B265
  2026-11-19T14:13:26Z  run.finished  B265
  2026-11-19T14:32:26Z  run.finished  B265
  2026-11-19T14:51:27Z  run.finished  B265
  2026-11-19T14:55:27Z  task.rebased  B265
  2026-11-19T14:55:27Z  task.state  B265
  2026-11-19T15:10:27Z  task.preflighted  B265
  2026-11-19T15:10:27Z  task.state  B265
  2026-11-19T15:35:27Z  task.state  B265
  2026-11-19T15:37:03Z  run.finished  B265
  2026-11-19T15:45:27Z  task.preflighted  B265
  2026-11-19T15:45:27Z  task.state  B265
  2026-11-19T15:49:06Z  task.verdict  B265
  2026-11-19T15:49:20Z  run.finished  B265
  2026-11-19T15:50:27Z  task.state  B265
  2026-11-19T15:50:27Z  task.state  B265
  2026-11-19T16:13:33Z  task.review_answered  B265
  2026-11-19T16:13:43Z  run.finished  B265
  2026-11-19T16:15:27Z  task.state  B265
  2026-11-19T16:30:27Z  task.preflighted  B265
  2026-11-19T16:30:27Z  task.state  B265
  2026-11-19T16:32:10Z  task.verdict  B265
  2026-11-19T16:32:20Z  run.finished  B265
  2026-11-19T16:35:27Z  task.state  B265
  2026-11-19T16:35:27Z  pr.merged  B265
  2026-11-19T16:35:27Z  task.state  B265
  2026-11-19T16:35:27Z  wave.closed
```

</details>
