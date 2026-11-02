# Rehearsal of B21 on claude-code and vibe (2026-11-02)

Both clients delivered the three-task wave of B21 unattended, from `brigade request new` to the merged wave and milestone pull requests: 3 of 3 tasks merged on each client, every task verified on its first verdict.
The normalised results of claude-code lack `cost_usd` on one run and nothing else; those of vibe never carry `cost_usd`, with no reason in `nulls`, and the one vibe segment cut by its turn cap has `usage` null.

| Client | Runs finished | Runs done | Tasks merged | Runs with `main_steps` null | Runs with `usage` null | Runs without `cost_usd` |
|---|---|---|---|---|---|---|
| claude-code | 9 | 8 | 3 of 3 | 0 | 0 | 1 |
| vibe | 9 | 7 | 3 of 3 | 1 | 2 | 9 |

Perimeter: the sandbox ledger of the rehearsal, 18 runs finished between 18:56Z and 19:35Z on 2026-11-02, read by the script `list_missing_fields.py` of the run that wrote this report, which prints each `result.json` under the runs of the sandbox state; `cost_usd` is counted when the key is absent or null.

## Setup

- Repository `Clauche-bot/fake-repository-for-testing`, one branch per client, `rehearsal3-claude-code` and `rehearsal3-vibe`, both cut at `7114350`, the state B21 delivered its wave from.
- Two projects, `rehearsal3_claude_code` and `rehearsal3_vibe`, each `CLIENT` set on its PROJECT entity, `CHECK_RUNS none`, acceptance `python3 -m unittest`.
- One request per project asking for the three cart changes of B21: remove one item, count the items, refuse an empty item name; each plan run wrote three tasks, S2, S3 and S4, chained by `AFTER`.
- vibe 2.26.1, its Rust CLI, no `[reasoning]` row in `config.toml`, so every level ran on `mistral-medium-3.5`; claude-code on the built-in rows.
- A brigade of the branch of B44, with an isolated `XDG_CONFIG_HOME`, `XDG_STATE_HOME` and `XDG_CACHE_HOME`, ticked once a minute until both milestones were integrated.

## Runs and what their normalised results lack

| Client | Procedure, slot | Run | Outcome | Steps | Null or missing measures, with the reason `nulls` gives |
|---|---|---|---|---|---|
| claude-code | wave-plan, plan | 20261102T185618Z-5478cd | done | 12 | none |
| claude-code | study, triage | 20261102T185625Z-a5fe6a | done | 8 | none |
| claude-code | build-task, build (S2) | 20261102T191855Z-32380e | done | 28 | none |
| claude-code | verify-pr, review (S2) | 20261102T192223Z-6d36e9 | done | 7 | none |
| claude-code | build-task, build (S3) | 20261102T192434Z-78588c | done | 22 | none |
| claude-code | verify-pr, review (S3) | 20261102T192647Z-59f6a4 | done | 12 | none |
| claude-code | build-task, build (S4) | 20261102T192849Z-b56633 | done | 17 | none |
| claude-code | verify-pr, review (S4) | 20261102T193041Z-1bcca8 | done | 11 | none |
| claude-code | study, report | 20261102T193355Z-94b898 | stopped | 12 | `cost_usd` (no reason); `exit` (stopped by a signal) |
| vibe | wave-plan, plan | 20261102T185619Z-de6fa0 | failed, `unreadable_output` | null | `main_steps`, `total_steps`, `session` (the client reported no session); `usage` (the client reported no usage); `cost_usd` (no reason) |
| vibe | wave-plan, plan | 20261102T190006Z-3f0e05 | done | 17 | `cost_usd` (no reason) |
| vibe | build-task, build (S2) | 20261102T191806Z-5aaa1a | done | 46 | `cost_usd` (no reason) |
| vibe | verify-pr, review (S2) | 20261102T192020Z-61b485 | done | 32 | `cost_usd` (no reason) |
| vibe | build-task, build (S3) | 20261102T192223Z-32665a | done | 38 | `cost_usd` (no reason) |
| vibe | verify-pr, review (S3) | 20261102T192434Z-23c320 | done | 25 | `cost_usd` (no reason) |
| vibe | build-task, build (S4) | 20261102T192647Z-21d38c | done | 76 | `cost_usd` (no reason) |
| vibe | verify-pr, review (S4) | 20261102T193041Z-430df7 | done | 22 | `cost_usd` (no reason) |
| vibe | study, report | 20261102T193315Z-645fee | `turn_limit` | 26 | `usage` (the client reported no usage); `cost_usd` (no reason) |

One more claude-code segment is not in the table: build run 20261102T190058Z-3f2556 of S2 was killed with the tick loop of the previous segment of this task and wrote no `result.json`; the tick parked S2 as `run dead`, and `brigade wave requeue` sent it back.

## Findings

1. vibe results carry no `cost_usd` key and `nulls` names no reason for it: 9 of 9 vibe results; claude-code results carry it on 8 of 9, the stopped one excepted. A reader of the ledger cannot tell a cost the client does not report from a cost lost.
2. The vibe segment cut by `--max-turns`, report study 20261102T193315Z-645fee, has 26 steps and `usage` null: the steps were counted, the usage of the turns it ran was not, though its journal holds a usage per model call.
3. The first vibe plan run, 20261102T185619Z-de6fa0, failed in 1 918 ms on `Error: session/start`, written on stdout with exit 1, so classified `unreadable_output`: the run was detached through the whitelist of the process runner and its launch carried no D-Bus session bus. Fixed in this pull request by `@DECISION.ADetachedBrigadeCarriesTheSessionBusAddressOfTheBrigadeThatDetachesIt`; the replanned run 20261102T190006Z-3f0e05 and every later vibe run reached the keyring.
4. vibe spends about twice the steps of claude-code on the same procedure: build-task p50 46 against 22, verify-pr p50 25 against 11; the S4 build took 76 steps, one above the budget of 75 of `build-task`, under its turn cap of 94.
5. The wave-report study of `rehearsal3_vibe` parked on `the judging run 20261102T193315Z-645fee gave no answer`: the report procedure, budget 20, ran out of turns on vibe at 26 steps.
6. The claude-code report study 20261102T193355Z-94b898 was stopped by a signal when the tick loop of the rehearsal ended on both milestones integrated: an artefact of the rehearsal harness, not of brigade.

## `brigade ledger budgets --client claude-code`

```
steps over the last 20 runs finished of each procedure:
  build-task  estimate
    runs p50 22  p90 28  measured 3  partial 0  unmeasured 0
    segments p50 22  p90 28  measured 3  unmeasured 0
  study  estimate
    runs p50 8  p90 12  measured 2  partial 0  unmeasured 0
    segments p50 8  p90 12  measured 2  unmeasured 0
  verify-pr  estimate
    runs p50 11  p90 12  measured 3  partial 0  unmeasured 0
    segments p50 11  p90 12  measured 3  unmeasured 0
  wave-plan  estimate
    runs p50 12  p90 12  measured 1  partial 0  unmeasured 0
    segments p50 12  p90 12  measured 1  unmeasured 0
```

## `brigade ledger budgets --client vibe`

```
steps over the last 20 runs finished of each procedure:
  build-task  estimate
    runs p50 46  p90 76  measured 3  partial 0  unmeasured 0
    segments p50 46  p90 76  measured 3  unmeasured 0
  study  estimate
    runs p50 26  p90 26  measured 1  partial 0  unmeasured 0
    segments p50 26  p90 26  measured 1  unmeasured 0
  verify-pr  estimate
    runs p50 25  p90 32  measured 3  partial 0  unmeasured 0
    segments p50 25  p90 32  measured 3  unmeasured 0
  wave-plan  estimate
    runs p50 17  p90 17  measured 1  partial 0  unmeasured 1
    segments p50 17  p90 17  measured 1  unmeasured 1
```
