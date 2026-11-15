# REPORT brigade_M12

- MILESTONE: M12
- PROJECT: brigade
- TASK_ROW: B243 merged #403
- TASK_ROW: B244 merged #406
- TASK_ROW: B245 merged #404
- TASK_ROW: B246 merged #405
- TASK_ROW: B248 merged #410
- TASK_ROW: B249 merged #407
- TASK_ROW: B250 merged #408
- STATISTIC: tasks 7
- STATISTIC: merged 7
- STATISTIC: parked 0
- STATISTIC: runs 47
- STATISTIC: files 143
- STATISTIC: insertions 4935
- STATISTIC: deletions 1195
- INSTRUCTIONS_CHANGE: corpus/_schema.awawa +4 -0
- INSTRUCTIONS_CHANGE: corpus/decisions.awawa +114 -65
- INSTRUCTIONS_CHANGE: corpus/milestones.awawa +2 -0
- INSTRUCTIONS_CHANGE: corpus/tasks.awawa +158 -18
- NARRATIVE: M12 is delivered whole: its seven tasks merged in three waves, from 2026-11-14 10:30 to 2026-11-15 17:55; brigade_w51 merged six of them (#403 to #408) by 15:20, and B248 needed brigade_w52 and brigade_w54 for #410
- NARRATIVE: the ledger records 47 runs, 1513 steps, 12.0 hours of run time and 66.44 USD: brigade_w51 37 runs, 1217 steps, 10.2 h, 55.75 USD; brigade_w52 6 runs, 190 steps, 1.3 h, 6.07 USD; brigade_w54 4 runs, 106 steps, 0.5 h, 4.61 USD
- NARRATIVE: the cost is a lower bound: the three runs that ended on wall_limit (B246 and B250 build, B248 remediation) report 0 USD for 47, 47 and 31.5 minutes of work
- NARRATIVE: B248 alone took 506 of the 1513 steps and 22.66 USD, a third of the milestone, over two parks and three waves; the six other tasks cost 43.78 USD
- NARRATIVE: went well: B243 and B245 passed their first verification and merged at 11:30, 1 h after the wave started; B249 and B250 merged after one remediation, B244 and B246 at their third round of review, after remediations and rebases
- NARRATIVE: went well: verification stopped eleven findings of grade high or medium before the merge, among them a TypeError of brigade tick --dry-run --json on a stall (B244), a study relaunched at every tick (B249), a SPEC of B143 left false (B246) and a leftover removal deleting untracked files with no trace (B248)
- NARRATIVE: went wrong: the first build segment of B246 (84 steps) and of B250 (49 steps) ended on the 47-minute wall limit, each then finished in under 10 minutes by a second segment; build-task also ran as a check repair (state fixing) on three tasks whose pull request was open, B244 twice, B246 and B249
- NARRATIVE: went wrong: in brigade_w52 the client login of the machine expired, two remediation runs of B248 failed in about a second, and the repair-round count parked a task no run could reach
- NARRATIVE: outside the milestone, two pull requests into main came out of it: #409 recorded the ruling that unblocked B248 (the worktrees a brigade command creates are created locked), and #411 pauses the wave on a lost client login instead of parking its task
- NARRATIVE: the next wave should: record the cost of a run cut by the wall limit, and size the wall limit of the build slot so a task of the size of B246 or B250 fits one segment
- REASON: B248, parked in brigade_w51 on 2026-11-14 at 12:30: its third build segment ended blocked on a ruling; the tick removed as a leftover the detached worktree brigade plan record was still working in, since is_run_live_on recognises a run only by its cwd, so three tests of tests/cli failed; the user chose option A, the worktrees a brigade command creates are created locked, recorded by #409 and written as a SPEC of B248
- REASON: B248, parked in brigade_w52 on 2026-11-14 at 17:35 as past 2 repair rounds: the remediation of the high finding (a gone base looked up as the base of the wave, not the base of the pull request) ended on wall_limit after 68 steps and 31.5 minutes, then its second segment and a fresh remediation failed on error_class execution because the client login had reached its time limit; no repair was attempted after the wall limit
- REASON: B248 was requeued, rebuilt in brigade_w54 on 2026-11-15 and merged after one remediation, the last finding being PullRequestCompareFailed escaping build_snapshot because it derived from BrigadeError
- SAMPLING: brigade/tick/read_leftovers.py (+180, B248): the guards that decide which branch and worktree the tick deletes; the verification of brigade_w52 found three defects in it (untracked files lost, a locked worktree whose directory is gone, merge-base exit 128), so read what deletes data
- SAMPLING: brigade/tick/plan.py (+146 -73) and brigade/tick/build_snapshot.py (+49 -62): the plan of the tick took four features in one milestone, the AFTER order (B243), the stall signal (B244), the quota gate (B249) and the removal of leftovers (B248); read how they compose
- SAMPLING: brigade/tick/read_integration_branches.py (+52 -6) with brigade/errors.py: the record of a gone base, rejected by two verifications (the wrong base looked up, then PullRequestCompareFailed escaping build_snapshot)
- SAMPLING: brigade/studies/read_quota_resumes.py (+38, B249): the reset mapping that relaunched a study at every tick before its remediation; read the rule keeping a rate_limit cut only when the latest order.parked follows it
- SAMPLING: brigade/tasks/push_task_branch.py and brigade/commands/task_push.py (B246), with brigade/commands/rebase_done.py: every task branch now reaches the forge through them; read the refusal of a HEAD with no passing check
- SAMPLING: brigade/waves/read_served_milestones.py (+64, B243): the AFTER order and the cycle detection that decide which milestone the tick serves
- SAMPLING: corpus/decisions.awawa (+114 -65) and corpus/tasks.awawa (+158 -18): the rulings recorded by the tasks, the archive of B143 made false by B246 among them

## Manual tests

| # | test |
| --- | --- |
| 1 | B243: SCHEMA MILESTONE of corpus/_schema.awawa declares FIELD AFTER @MILESTONE, REPEATABLE, CONVERSE BEFORE, DESC the milestone that must be reached before this one |
| 2 | B243: the tick cuts no branch, opens no wave and selects no new task of a milestone one AFTER of which is not STATUS reached at PROJECT.MAIN, and names it on stderr at each tick |
| 3 | B243: a wave already open of a milestone given an AFTER not reached goes to its end: the tick serves its tasks until the wave closes |
| 4 | B243: a planned milestone stays unserved whatever its AFTER |
| 5 | B243: a milestone with no AFTER is served as today |
| 6 | B243: a cycle of AFTER serves none of its milestones, each named on stderr at each tick |
| 7 | B243: the pull request that delivers the task writes an AFTER naming MILESTONE M12 on MILESTONE M8 and an AFTER naming MILESTONE M8 on MILESTONE ADD0 |
| 8 | B243: a test of tests/unit/tick proves an active milestone with an AFTER not reached unserved and named, its open wave going to its end, one whose AFTER is reached served, a planned one unserved whatever its AFTER, and a cycle serving none |
| 9 | B244: a key of config.toml sets the delay of a stall in minutes, 60 when the key is absent |
| 10 | B244: the last action of the tick on a task is the latest ledger event keyed by that task among task.state, run.started, run.finished and tick.action_failed |
| 11 | B244: a task of an open wave whose last action is older than the delay raises one signal in the inbox, of a kind of its own, fingerprinted by the project, the wave and the task, so that the same stall at the next tick folds into it |
| 12 | B244: a task holding a live run raises no stall signal, whatever the age of its last action |
| 13 | B244: a merged task, a parked task and a task paused on the quota raise no stall signal |
| 14 | B244: a test of tests/unit/tick proves the signal raised once the delay is passed and not before, the delay read from config.toml, none raised for a task holding a live run, a merged task, a parked task or a task paused on the quota, and the same fingerprint recorded at the next tick |
| 15 | B245: the collector inbox-families hands the model the name and the TITLE of each PATTERN the operational corpus holds |
| 16 | B245: an answer of the triage may add EVIDENCE to a PATTERN the operational corpus holds, each opening on the fingerprint of a signal inbox-families collected; check_patterns and deliver_patterns accept it, and after the run the held PATTERN carries each EVIDENCE added |
| 17 | B245: a triage run whose families match the subject of a PATTERN the operational corpus already holds, ratified or not, adds the new signals to that PATTERN as EVIDENCE and proposes no new one on that subject |
| 18 | B245: a test of tests/unit/studies proves inbox-families printing the name and the TITLE of each held PATTERN, an answer adding EVIDENCE to a held PATTERN accepted and written on that PATTERN, an added EVIDENCE opening on no collected fingerprint refused, and a second run on signals of a subject with a held PATTERN writing no new PATTERN |
| 19 | B246: a run that builds a task pushes its branch only once every ACCEPTANCE command of the project passes on its worktree, coverage report included; a failing command is repaired before the push, or reported as a blocker with its output |
| 20 | B246: brigade task push pushes the branch of the task with lease, force-with-lease after a rebase, and refuses, pushing nothing, a HEAD on which no brigade task check passed |
| 21 | B246: the procedures build-task.md, remediate-pr.md and rebase-on-base.md of brigade/runs/data/procedures push the branch of a task through brigade task push |
| 22 | B246: brigade task promote pushes only once a brigade task check passed on the parent of the promotion commit and that commit, touching the corpus alone, passes awawa fmt --check and awawa lint --strict |
| 23 | B246: the AGENTS.md of brigade names brigade task check and the uvx forms of the ACCEPTANCE commands for a role launched by hand, so that coverage is provable locally with neither ruff nor coverage on PATH |
| 24 | B246: a test of tests/unit proves a build run whose ACCEPTANCE command fails pushing nothing |
| 25 | B246: brigade task context prints awawa show of the task, its RATIONALE whole, and awawa context <task> --depth 1 --skip reasoning --with-schema for its neighbours |
| 26 | B246: build-task.md says the package holds the task whole and its neighbours at depth 1 without their reasoning, and that the run reads a further entity with awawa show when it needs it |
| 27 | B246: a test of tests/unit/tasks proves brigade task context running awawa show of the task, and awawa context of the task with --depth 1, --skip reasoning and --with-schema |
| 28 | B246: once delivered, the pattern oversized_output_re_read_in_runs raises no new signal on the runs launched after the delivery |
| 29 | B248: the tick removes each local branch the scan stale_branches signals and each worktree the scan worktrees signals; a branch or a worktree so removed is an item of its scan no more at the next run of the scan |
| 30 | B248: a removal is planned only under the guards of TASK B234: no run live on the worktree, no lock git lists on it, and the head of the local branch reached the forge |
| 31 | B248: a branch carrying a commit outside its merged pull request is kept and named with that commit once, not at each tick |
| 32 | B248: an integration branch whose base the forge no longer holds is recorded once and compared no more: the tick writes no error for it at the ticks that follow |
| 33 | B248: a worktree a brigade command creates for its own work, under the state or the cache directory of brigade (brigade plan record, the publication of a task or a milestone report, the answer written to a file, the proof of a head), is created locked with a reason naming that command, which removes it; the guard no lock git lists on it keeps it from the tick while the command works, and a worktree a crash left stays locked, kept and named by the scan worktrees |
| 34 | B248: a test of tests/unit proves the tick removing a stale branch and its worktree, removing none under a live run, a lock or a local head that did not reach the forge, naming once a branch kept for a commit outside its merged pull request, and recording once a base gone from the forge |
| 35 | B249: once a run of the machine ends on error_class rate_limit, the tick launches no run of any slot until the reset that run names: no build run, no verification of a pull request or of a delivered head, verify-pr included, no remediation, no check repair and no study |
| 36 | B249: a study parked by a run that ended on error_class rate_limit is due again once the reset that run names has passed, instead of staying parked as failed; a study parked on any other cause stays parked until the user resumes it |
| 37 | B249: a test of tests/unit/tick proves no build, verification, repair or study run launched between a run.finished on rate_limit and its reset, a study parked on rate_limit due again after the reset, and a study parked on another cause still parked |
| 38 | B250: brigade/system/describe_linger_warning.py asks loginctl for the user of the run, loginctl show-user <user> --property=Linger, where at f7d2deae describe_linger_warning runs loginctl show-user -p Linger with no user |
| 39 | B250: with linger on, brigade doctor and brigade scheduler install report linger ok and warn no linger no more |
| 40 | B250: a test of tests/unit/system proves the user passed to loginctl and Linger=yes read as ok |

## Tester steps

| # | test |
| --- | --- |
| 1 | all tasks: from the milestone branch, run python3 -m unittest and check every test passes, the tests of tests/unit/tick, tests/unit/studies, tests/unit/tasks and tests/unit/system included |
| 2 | B243: open corpus/_schema.awawa and check SCHEMA MILESTONE declares FIELD AFTER @MILESTONE, REPEATABLE, CONVERSE BEFORE; open corpus/milestones.awawa and check M8 carries AFTER @MILESTONE.M12 and ADD0 carries AFTER @MILESTONE.M8 |
| 3 | B243: once M8 is active and M12 not yet merged into main, run brigade tick --dry-run and check it cuts no branch for M8, opens no wave and names M8 on stderr; after the merge of M12, check the next tick serves M8 |
| 4 | B243: in a test project, make two active milestones AFTER each other and check the tick serves neither and names both on stderr at each tick; give an AFTER not reached to a milestone holding an open wave and check that wave still runs to its close; check a planned milestone stays unserved and a milestone with no AFTER is served as before |
| 5 | B244: set stall_after to 1 in config.toml, leave a task of an open wave without any run for more than a minute, and check brigade inbox lists one stall signal for that project, wave and task; after the next tick, check it is still one signal, not two |
| 6 | B244: with a stall in the plan, run brigade tick --dry-run --json and check it prints valid JSON, the time of the last action as a string; remove stall_after from config.toml and check no stall is signalled before 60 minutes |
| 7 | B244: check no stall signal appears for a task whose run is live in brigade runs, nor for a merged, parked or quota-paused task, however old its last action |
| 8 | B245: run brigade collect inbox-families and check it lists the name and the TITLE of each PATTERN of the operational corpus |
| 9 | B245: run the triage study on an inbox holding new signals of a subject a held PATTERN already covers, and check the PATTERN gains those fingerprints as EVIDENCE and no new PATTERN is proposed; hand back an answer adding an EVIDENCE whose fingerprint was not collected and check brigade study answer refuses it |
| 10 | B246: in a task worktree, commit a change that fails ruff or lowers coverage and run brigade task push: it refuses and pushes nothing; run brigade task check, fix the change, and check brigade task push then pushes with lease, and with force-with-lease after a rebase |
| 11 | B246: run brigade task promote with a promotion commit touching corpus/ alone on a parent that passed brigade task check, and check it pushes; break awawa lint --strict in that commit and check it refuses |
| 12 | B246: read build-task.md, remediate-pr.md and rebase-on-base.md under brigade/runs/data/procedures: each pushes through brigade task push, and rebase-on-base.md gives no contradictory push order for a task with no pull request |
| 13 | B246: on a machine with neither ruff nor coverage on PATH, run the uvx forms of the ACCEPTANCE commands that AGENTS.md names, and check coverage is reported |
| 14 | B246: run brigade task context on a task and check it prints the task whole with its RATIONALE, then its neighbours at depth 1 without their reasoning and with the schema |
| 15 | B246: a few days after the merge, check brigade inbox shows no new signal of the pattern oversized_output_re_read_in_runs for the runs launched since |
| 16 | B248: after a task pull request is merged, leave its local branch and worktree, and check a later tick removes both and the scans stale_branches and worktrees list them no more |
| 17 | B248: repeat with a run live in the worktree, with the worktree locked by git worktree lock, with untracked files in it, and with a local commit not pushed: the tick removes none of them |
| 18 | B248: add a commit outside its merged pull request to a merged branch, and check the tick keeps the branch and names the commit once, not at every tick |
| 19 | B248: for an integration branch whose base the forge no longer holds, such as integration/brigade_w27 on integration/hardening, check the tick records it once and writes no 404 error for it at the following ticks |
| 20 | B248: while brigade plan record or the publication of a report runs, run git worktree list and check its worktree under the state or cache directory of brigade is locked with a reason naming the command, the tick leaves it, and it is gone once the command ends |
| 21 | B249: after a run ends on error_class rate_limit, check in brigade ledger the reset it names, then check brigade tick --dry-run plans no run of any slot (build, verify-pr, remediation, check repair, study) until that reset, and plans them again after it |
| 22 | B249: check a study parked by that rate_limit run is due again after the reset, while a study parked on another cause stays parked until resumed by hand, including one resumed once after a reset and parked again |
| 23 | B250: with linger on (loginctl enable-linger), run brigade doctor and brigade scheduler install and check both report linger ok with no warning; turn linger off and check the warning comes back |
