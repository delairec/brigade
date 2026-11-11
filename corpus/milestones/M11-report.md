# REPORT brigade_M11

- MILESTONE: M11
- PROJECT: brigade
- TASK_ROW: B242 merged #385 #382
- STATISTIC: tasks 1
- STATISTIC: merged 1
- STATISTIC: parked 0
- STATISTIC: runs 9
- STATISTIC: files 0
- STATISTIC: insertions 0
- STATISTIC: deletions 0
- NARRATIVE: Verdict: M11 delivered its one task, B242 merged by pull request 385 into integration/waves-read-at-the-forge-branch on 2026-11-08 at 17:00:02Z, 0 tasks parked and 0 failed, and 2 of the 3 verdicts asking for changes were followed by no fix.
- NARRATIVE: No REASON is written because the ledger of wave brigade_w32 records no task parked or failed; B242 is the only task of the wave.
- NARRATIVE: Cost of the 9 runs of wave brigade_w32, summed from the run.finished events of the ledger collector, collected 2026-11-08T17:01:34Z: 237 steps, 101.8 min of run time, 12.20 USD, 154154 output tokens.
- NARRATIVE: By slot, same source: build 1 run, 43 steps, 33.7 min, 3.97 USD; review 4 runs, 100 steps, 28.9 min, 5.22 USD; remediate 2 runs, 68 steps, 27.3 min, 2.58 USD; rebase 2 runs, 26 steps, 11.9 min, 0.43 USD.
- NARRATIVE: Elapsed time of the wave, wave.started 14:05:00Z to wave.closed 17:00:02Z in the ledger: 2 h 55 min 02 s for 1 task.
- NARRATIVE: Went well: 9 of 9 runs ended with outcome done and exit 0 (run.finished, ledger).
- NARRATIVE: Went well: the first verdict, 15:09:54Z at head cd769cbb, found by mutation that no test executed the forge environment of brigade/commands/task_context.py:69; commit a4419805 added the test, and the remediator recorded 3336 tests passing (task.review_answered, 16:14:15Z).
- NARRATIVE: Went well: the last verification, run e69ddc at head be76393c, passed with 0 findings in 14 steps, 1.7 min, 0.74 USD (task.verdict 16:58:13Z, run.finished).
- NARRATIVE: Went wrong: the 2 findings of the first verdict stayed unanswered from 15:09:54Z to the first changes_requested at 16:05:00Z, 55 min 06 s, across heads 52ac9a3d and 762b32fb (task.verdict, task.state).
- NARRATIVE: Went wrong: the tick recorded task.state fixing at 15:05:00Z and 15:35:00Z, before the verdicts of 15:09:54Z and 15:37:44Z, and the runs of those two states were rebase-on-base (9318d3, 6c4f6a), not remediate-pr; the third verdict names the repair diff as the rebase on 1b383f1b alone.
- NARRATIVE: Cost of that loop, the 4 runs 9318d3, d7d89a, 6c4f6a and 5f7006 (ledger): 71 of 237 steps, 25.7 of 101.8 min, 2.64 of 12.20 USD.
- NARRATIVE: Went wrong: head a4419805 failed the privacy check at 16:25:00Z on a home path at tests/unit/commands/test_task_context.py:258, after 3 preflights passing at the earlier heads, and the second remediator run abd110 cost 28 steps, 18.7 min, 1.00 USD.
- NARRATIVE: Went wrong: the answer of run abd110 (task.review_answered 16:44:38Z) restates the 2 earlier findings as fixed by a4419805 and holds no answer to the privacy finding, which the preflight of head be76393c at 16:55:56Z passed.
- NARRATIVE: Went wrong: verification run df59df took 41 steps against a shipped budget of 40 (run.finished, ledger).
- NARRATIVE: Gap: the git-diff-stat collector reads 0 files, 0 insertions and 0 deletions, the STATISTIC lines above, where the preflight of head be76393c reads 69 files and 2068 lines in 12 packages; the collector does not record what it compared, so the size to retain is that of the preflight.
- NARRATIVE: Gap: the ledger does not say why the tick started a rebase at 15:05:00Z and 15:35:00Z, nor how a verdict recorded during fixing is routed; that the verdict was lost because it arrived during fixing is a reading of the order of the events, the code was not read.
- NARRATIVE: Gap: steps_to_first_edit is null for build run 52b6f0, its reason being that the segment made no edit outside the progress file, where the pull request it opened holds 68 files at the first preflight: the metric is unusable for that run.
- NARRATIVE: Gap: no collector records a manual run of the tests below; this report ran none of them.
- NARRATIVE: The manual tests run on a checkout of integration/waves-read-at-the-forge-branch, or of main once the pull request of the milestone is merged.
- NARRATIVE: Next wave should change: a verdict recorded while its task is in fixing reaches remediation, by carrying it through the rebase or by stopping the verification the rebase supersedes; the loop above is 2.64 USD and 55 min of delay on one task.
- NARRATIVE: Next wave should change: a remediator run applies the privacy check before it pushes; run 14448e ended at 16:14:25Z and the preflight found the home path 10 min 35 s later, at the cost of run abd110.
- NARRATIVE: Next wave should change: an answer to a preflight failure names that failure, as the answers to the verdict findings name theirs.
- SAMPLING: brigade/waves/prepare_wave_tree.py, _prepare_tree_at, _holds_the_wave and locate_wave_branch_base: the ref every other read of the fix rests on; a wrong ref launches nothing and raises nothing, as wave brigade_w31 showed.
- SAMPLING: brigade/commands/task_context.py:69, the forge environment handed to brigade task context: 3 verdicts flagged it as executed by no test, until commit a4419805.
- SAMPLING: tests/unit/commands/test_task_context.py around line 258: the line that failed the privacy check at a4419805, to read as replaced at be76393c, the size moving from 2070 to 2068 lines between those preflights.
- SAMPLING: tests/cli/test_tick_after_a_task_merged_on_the_forge.py, read_the_local_and_forge_heads_of_the_milestone_branch: the test proving the lag on the sandbox, and the helper the second finding asked for.
- SAMPLING: brigade/tick/build_snapshot.py, read_implemented_tasks and the read of the tasks of a wave, with brigade/tasks/assemble_task_context.py: confirm the path of FORGE none still reads the local branch.
- SAMPLING: tests/awawa/recordings, one of the 12 packages of the preflight: no collector gives a count per package, so sample why a fix to the ref of a read changes recordings.

## Manual tests

| # | test |
| --- | --- |
| 1 | B242: the tree of a wave of a project of FORGE github, brigade/waves/prepare_wave_tree.py:prepare_wave_tree, read by the snapshot at brigade/tick/build_snapshot.py:714 and by brigade wave requeue at brigade/commands/wave_requeue.py:87, is the tree of the branch of its milestone as the forge holds it, fetched at the read: its sha is the head of origin/<branch>, whatever the local branch of the clone holds, where today _prepare_tree_at, prepare_wave_tree.py:22-24, is given the bare name cut.branch at lines 59 and 67 and git resolves it to the local branch; a project of FORGE none keeps its local branch |
| 2 | B242: the tasks of a wave, build_snapshot.py:715, and its implemented set, read_implemented_tasks at build_snapshot.py:702, follow from that tree: a task of a wave whose every AFTER is STATUS implemented at origin/<branch of its milestone>, merged there by the pull request of a task of an earlier wave, is startable at the next tick, brigade/tick/plan.py:709-715, and brigade tick --dry-run plans its launch, where today the implemented set is read at the local branch and, on 2026-11-08, the wave brigade_w31 held TASK B240 AFTER TASK B46 unlaunched from the merge of pull request 379 into integration/portability at 06:46Z to 13:26Z, the local integration/portability at 3e75cf2a, B46 todo, 93 commits behind origin/integration/portability at 49b37c79, B46 implemented, until the session fast-forwarded it by hand |
| 3 | B242: the milestone a wave belongs to, _holds_the_wave over the open cuts of prepare_wave_tree.py:49-62, and the base of a wave branch, locate_wave_branch_base at prepare_wave_tree.py:65-78, read by brigade/tick/read_integration_branches.py:117-120, are read on the same tree; the base a build run counts the next task number on, brigade/tasks/assemble_task_context.py:81-83, is read as the forge holds it on a project of FORGE github, where today worktree.base, the recorded branch of the milestone from brigade/tasks/find_task_base.py, resolves to the local branch |
| 4 | B242: tests/unit/waves/test_prepare_wave_tree.py proves the tree of a wave and the base of a wave branch read at the ref the branch of the milestone is located at on the forge on a project of FORGE github, the local branch left where it stands, and at the local branch on a project of FORGE none; a test of tests/unit/tick proves a task of a wave startable on an AFTER implemented in the set read from that tree and merged in no wave |
| 5 | B242: a test of tests/cli runs two waves of one milestone on the sandbox of tests/cli/wave_rehearser.py, on the fake forge github-over-a-bare-remote, which merges a pull request in a clone of its own and pushes the bare remote alone, the local branch of the milestone in the clone of the project standing at its cut: once the first wave has merged a task into the branch of the milestone, a task AFTER that task reaches the branch of the milestone on the remote, as tests/cli/test_tick_after_a_milestone_head_moved.py pushes a commit on it, the test proves the lag by git rev-parse of the local branch and of the branch on the remote, brigade tick --dry-run plans the launch of that task and the next brigade tick --once starts its wave and launches it, task.state running in the ledger, where today the tick starts the wave and launches nothing; the test runs no git command on the clone of the project between the merge and the tick |
| 6 | B242: wiki/Tick-and-scheduler.md, read at 4843e42d, says in Launching a task, next to its item of lines 108-110 on the base fetched and the task branch cut from origin/<base>, that on a project of FORGE github the tick reads the tasks of a wave and what is implemented at the branch of its milestone as the forge holds it, fetched at each read, never at the local branch of the clone, and that a project of FORGE none keeps its local branch |

## Tester steps

| # | test |
| --- | --- |
| 1 | Test 1, the tree of a wave follows the forge: in a throwaway clone of a registered project of FORGE github with an open wave, set the local branch of the milestone back one commit behind origin/<branch>, run brigade tick --dry-run, and expect the same plan as before the move, the local branch still at the older commit; on a project of FORGE none, expect the plan to follow the local branch. |
| 2 | Test 2, a task whose dependency merged on the forge is launched: find a wave of a project of FORGE github with a task whose every AFTER is STATUS implemented at origin/<branch> and still todo on the local branch, confirm with git rev-parse <branch> and git rev-parse origin/<branch> that the two differ, run brigade tick --dry-run without fast-forwarding, and expect the plan to launch that task; before the fix, wave brigade_w31 stayed unlaunched in that state. |
| 3 | Test 3, the base a build run counts the next task number on: run python3 -m unittest tests.unit.commands.test_task_context and expect test_should_fetch_the_base_of_the_task_as_the_login_bound_to_the_cli_account to pass, then read brigade/tasks/assemble_task_context.py and brigade/waves/prepare_wave_tree.py and confirm that the base of a project of FORGE github, locate_wave_branch_base and the milestone held by _holds_the_wave are read at the ref on the forge. |
| 4 | Test 4, the unit proofs: run python3 -m unittest tests.unit.waves.test_prepare_wave_tree and python3 -m unittest discover -s tests/unit/tick -t . and expect all to pass, then confirm by reading them that a case covers the local branch left where it stands on FORGE github, one covers the local branch on FORGE none, and one covers a task startable on an AFTER merged in no wave. |
| 5 | Test 5, the two waves on the sandbox: run python3 -m unittest tests.cli.test_tick_after_a_task_merged_on_the_forge and expect it to pass, then confirm by reading it that the local and remote heads of the milestone differ, that brigade tick --dry-run plans the launch, that brigade tick --once records task.state running, and that no git command touches the clone between the merge and the tick. |
| 6 | Test 6, the documentation: open wiki/Tick-and-scheduler.md at the section Launching a task and confirm that, next to the item on the base fetched, it says a project of FORGE github reads the tasks of a wave and what is implemented at the branch of its milestone as the forge holds it, fetched at each read, and that a project of FORGE none keeps its local branch. |
