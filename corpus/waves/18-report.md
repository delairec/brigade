# REPORT brigade_w18

- WAVE: brigade_w18
- PROJECT: brigade
- TASK_ROW: B35 running
- STATISTIC: tasks 1
- STATISTIC: merged 0
- STATISTIC: parked 0
- STATISTIC: runs 2
- STATISTIC: files 0
- STATISTIC: insertions 0
- STATISTIC: deletions 0
- NARRATIVE: Verdict: brigade_w18 delivered nothing; its one task, B35, parked on a question about its own SPEC 8, with no pull request opened.
- NARRATIVE: Wave started 2026-11-01T17:20:00Z on integration/brigade_w18 with B35 alone; B35 parked at 17:50:26Z (ledger collector, events wave.started and task.parked).
- NARRATIVE: Build run 20261101T172000Z-5b875a, role ada, segment 1: 58 steps, 898 s, 4.20 USD, outcome handed_over (ledger, run.finished at 17:36:01Z).
- NARRATIVE: Same run, segment 2: 49 steps, 636 s, 2.67 USD, outcome blocked (ledger, run.finished at 17:46:37Z).
- NARRATIVE: Wave total: 107 steps, 1534 s of run time, 6.87 USD across the 2 segments, sum of the two run.finished events of the ledger.
- NARRATIVE: Both segments exceeded fifty steps of the build-task procedure: 58 and 49, the first ending on a handover.
- NARRATIVE: The CLI-filled TASK_ROW "B35 running" and STATISTIC "parked 0" lag the ledger, which records task.parked for B35 at 17:50:26Z, the same second as wave.reported: the report was built before the parking was counted.
- NARRATIVE: Diff stat 0 files: the 7 commits of task/brigade_w18/B35 are local to the worktree .brigade/worktrees/B35, never pushed, so the wave branch holds none of them (git-diff-stat collector, run message of segment 2).
- NARRATIVE: Delivered on the task branch, unmerged: the session-read-twice defect fixed in da86ddfb, SPEC 9 in a5c9bee7, SPEC 8 written in d47f724b pending the name; SPEC 10, the IMPL anchors, the DECISION entities and steps 5 to 8 not done (run message of segment 2).
- NARRATIVE: Checks on the task branch at the block: unit tests OK; tests/cli 11 failures and 3 errors, caused by fixtures writing a paused STUDY mine-transcripts that invalidates the operational corpus (run message of segment 2).
- NARRATIVE: Next wave: rule on the name in SPEC 8 of B35, then requeue B35 with brigade wave requeue brigade_w18 B35; the worktree and its 7 commits are the starting point.
- NARRATIVE: Next wave: the report should be built after the task.parked event is folded into TASK_ROW and STATISTIC, so that the filled fields match the ledger.
- NARRATIVE: Next wave: a task specifying an entity name could be linted for that name at refinement, before its ratification, since awawa L017 alone stopped this wave.
- REASON: B35 parked: SPEC 8 says "the built-in study mine-transcripts …; a STUDY of the operational corpus named mine-transcripts replaces it", yet awawa lint --strict on STUDY mine-transcripts gives L017 "entity name must be an identifier", so no STUDY can carry that name (run 20261101T172000Z-5b875a, segment 2).
- REASON: B35 waits for one of two rulings the run proposed: rename the study mine_transcripts in the TITLE and SPEC 8 to 10 of B35, lint verified to pass; or keep mine-transcripts and drop the replacement clause from SPEC 8.
- SAMPLING: da86ddfb on task/brigade_w18/B35, local and unpushed: the read_sessions key (client, session), one read per session from the last run.finished; the run reports 6 test failures when the key is removed.
- SAMPLING: d47f724b on task/brigade_w18/B35, local and unpushed: the built-in study of SPEC 8 and the CLI fixtures that write a paused STUDY mine-transcripts, the source of the 11 failures and 3 errors of tests/cli; it is the commit the ruling on the name rewrites.
- SAMPLING: a5c9bee7 on task/brigade_w18/B35, local and unpushed: SPEC 9, the TRANSCRIPT_FINDINGS entry of check_patterns and the filter on CITED_ITEMS_BY_COLLECTOR checking EVIDENCE against transcript-findings.

## Tester steps

| # | test |
| --- | --- |
| 1 | No manual test: no task of brigade_w18 was merged, so the wave carries no MANUAL_TEST line. |
