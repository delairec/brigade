# REPORT brigade_w13

- WAVE: brigade_w13
- PROJECT: brigade
- TASK_ROW: B225 merged #281
- TASK_ROW: B227 running
- STATISTIC: tasks 2
- STATISTIC: merged 1
- STATISTIC: parked 0
- STATISTIC: runs 5
- STATISTIC: files 208
- STATISTIC: insertions 1945
- STATISTIC: deletions 8345
- INSTRUCTIONS_CHANGE: corpus/decisions.awawa +35 -239
- INSTRUCTIONS_CHANGE: corpus/tasks.awawa +71 -298
- INSTRUCTIONS_CHANGE: corpus/waves/11-report.md +0 -34
- INSTRUCTIONS_CHANGE: corpus/waves/12-report.md +48 -0
- INSTRUCTIONS_CHANGE: corpus/waves/4-report.md +0 -96
- INSTRUCTIONS_CHANGE: corpus/waves/6-report.md +0 -44
- NARRATIVE: Verdict: half delivered. B225 merged as #281 after one verification round with no finding; B227 was parked after three handed-over build segments, its run declared dead, with no pull request.
- NARRATIVE: The wave started 2026-11-01T02:40:54Z with B225 and B227; the tick then failed LaunchTask 214 times, 107 per task, every five minutes until 11:30:18Z, because .brigade/worktrees/B225 and .brigade/worktrees/B227 already existed (git worktree add exited 128); both launched at 11:35:54Z, 8 h 55 min after the start (ledger, tick.action_failed and task.state).
- NARRATIVE: Cost, summed from the 5 run.finished events of the ledger: 279 steps, 3548.3 s, 19.11 USD. B225 build 71 steps, 1045.7 s, 5.36 USD; its verify-pr 21 steps, 652.8 s, 1.25 USD; B227 three build segments of 65, 64 and 58 steps, 1849.9 s, 12.50 USD, 65 % of the cost for nothing delivered.
- NARRATIVE: B225 went well: pull request #281 opened 11:53:01Z, the preflight passed every check at head bf245fd (size info: 22 files, 1032 lines), verify-pr returned pass with no finding at 12:11:27Z, and Clauche-bot merged it at 12:15:00Z in one round (ledger, task.preflighted, task.verdict, pr.merged).
- NARRATIVE: The rows the CLI filled lag the ledger: TASK_ROW says B227 running and STATISTIC says parked 0, while the ledger records task.parked for B227 at 12:10:03Z; no PARKED_QUESTION is filled, the reason being a dead run, not a question.
- NARRATIVE: The diff statistics (208 files, +1945, -8345) do not measure the wave: they carry the deletion of the dashboard tests merged on main by #273 (tests/unit/dashboard/test_answer_dashboard_request.py -817) and of the wave reports 4, 6 and 11, so they compare main with a wave branch that lacks main's latest merges; the wave's own change is #281, 22 files and 1032 lines per its preflight (git-diff-stat document).
- NARRATIVE: The next wave should change: a LaunchTask failing on an existing worktree directory parks the task or reuses the directory instead of retrying 107 times; B227 is requeued only once the progress file of run 20261101T113554Z-330b22 says why it handed over three times; the report fills TASK_ROW and parked from task.parked and diffs the wave branch against its own base.
- REASON: B227: parked 2026-11-01T12:10:03Z, reason 'run dead: 20261101T113554Z-330b22', no blocker; the run handed over three times (65, 64 and 58 steps, exit 0, no error class) without opening a pull request, and the tick found it dead before a fourth segment. Why each segment handed over instead of finishing lies in the run's progress file, which no collector gathered.
- REASON: B225 and B227, before their launch: LaunchTask failed 107 times each from 02:40:54Z to 11:30:18Z, git worktree add exiting 128 because the worktree directory already existed, the first attempt creating task/brigade_w13/<task> from origin/integration/brigade_w13 and the next 106 adding the existing branch; the tick retried each round without clearing the directory or parking the task. Who or what left the directories is not in the collected evidence.
- SAMPLING: brigade/tick/plan.py:_is_wave_pull_request_ready and the planning of RebaseWave in #281: the guard that keeps a behind wave pull request from merging, and the exclusion of a wave whose rebase run lives or ended blocked.
- SAMPLING: brigade/adapters/forges/github.py:find_pull_request (+10 -1): how behind is read from the compare of base and head, the single input the readiness guard rests on.
- SAMPLING: brigade/tick/build_snapshot.py (+157 -20) and tests/unit/commands/test_tick.py (+399 -50), the largest additions of the diff-stat: confirm in #281 which lines are the wave's before reading, since the diff mixes in main's recent merges.

## Manual tests

| # | test |
| --- | --- |
| 1 | B225: brigade/tick/plan.py:_is_wave_pull_request_ready is false while the pull request of the wave is behind its base, PullRequestFacts.behind as brigade/adapters/forges/github.py:find_pull_request reads it from the compare of base and head; no MergeWavePullRequest is planned for such a pull request |
| 2 | B225: the plan holds one RebaseWave action, project, wave, branch and the recorded branch of its milestone, for each open wave whose pull request is open into that branch and behind it, unless a rebase run lives on the worktree of the wave branch or its last one ended blocked, the wave then paused on its question as SPEC 5 of TASK B214 pauses it; the executor applies it as brigade/waves/rebase_milestone_branches.py:_rebase_wave applies the rebase of SPEC 3 of TASK B214: brigade/git/rebase_onto.py in the worktree of the branch under the worktrees lock of the project, the push with --force-with-lease, a conflict aborted and a run of the rebase slot launched on that worktree with base=<the milestone branch>, no second run while one lives; a task branch of the wave is put back on its wave branch at its next launch, as SPEC 3 of TASK B214 says |
| 3 | B225: the ledger declares wave.rebased with project, wave, branch, before and after, the head of the branch before and after the rebase, and login; the executor appends it once the branch is rebased without a conflict and pushed, nothing on a conflict, the run it launches recording its own outcome, and nothing on a head left where it was; brigade ledger counts it among the events of its overview through brigade/ledger/declared_events.py |
| 4 | B225: brigade tick --dry-run prints the rebase with its wave, its branch and its base |
| 5 | B225: tests/unit/tick/test_plan.py proves, on literal rows, an open wave pull request behind its milestone branch planned its rebase and no merge, one not behind planned its merge, and one whose rebase run lives or ended blocked planned neither; tests/unit prove the executor rebasing and pushing the wave branch with lease and appending wave.rebased with the heads before and after, a conflict launching the rebase run and appending nothing, and the event read, written and declared as tests/unit/ledger/test_task_rebased.py proves task.rebased; tests/cli gains at most one flow through the fake adapter: a wave pull request whose branch its milestone branch has outrun, and brigade tick --once rebases the branch and merges nothing that round |

## Tester steps

| # | test |
| --- | --- |
| 1 | B225 readiness: on a scratch project with a milestone, open the wave pull request into its milestone branch, then push a commit to the milestone branch so the wave branch falls behind; run brigade tick --dry-run and check the plan holds no MergeWavePullRequest for that pull request. |
| 2 | B225 rebase: in the same state, run brigade tick --once; check the wave branch now sits on the milestone branch and the remote head equals the local one (git ls-remote). Then make the milestone branch conflict with the wave branch and tick again: the rebase is aborted, a run of the rebase slot is launched on the wave worktree with base set to the milestone branch, and the next tick launches no second run while it lives. |
| 3 | B225 ledger: after the clean rebase, run brigade ledger and check one wave.rebased with project, wave, branch, the heads before and after, and login, the after head equal to the pushed head; after the conflict and after a tick that leaves the head where it was, check no new wave.rebased was appended. |
| 4 | B225 dry run: with a wave branch behind its milestone branch, run brigade tick --dry-run and check the line of the rebase names the wave, the branch and its base. |
| 5 | B225 tests: run python3 -m unittest tests.unit.tick.test_plan, then python3 -m unittest tests.cli, and check the cli flow where the milestone branch outran the wave branch rebases it and merges nothing that round. |
