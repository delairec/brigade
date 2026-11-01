# REPORT brigade_w16

- WAVE: brigade_w16
- PROJECT: brigade
- TASK_ROW: B228 merged #288
- STATISTIC: tasks 1
- STATISTIC: merged 1
- STATISTIC: parked 0
- STATISTIC: runs 5
- STATISTIC: files 0
- STATISTIC: insertions 0
- STATISTIC: deletions 0
- NARRATIVE: Verdict: the wave delivered its one task, B228, merged into integration/brigade_w16 as PR 288 after two repair rounds, in 50 min 53 s of wall clock (wave.started 14:00:01Z to pr.merged 14:50:54Z, ledger).
- NARRATIVE: Cost: five runs, all outcome done, 102 steps, 1 621 s of run time and 5.94 USD (sum of the run.finished events of the ledger).
- NARRATIVE: Build run 20261101T140001Z-05bec1 (ada): 42 steps, 593 s, 2.81 USD, opened PR 288 at 14:09:50Z; it carried 47 % of the cost of the wave.
- NARRATIVE: Went wrong: the first preflight, at head c3ee644, failed the CI checks 'Tests and zipapp on Python 3.11' and 'on Python 3.x' (task.preflighted, 14:15:54Z): the build run opened its pull request on a red CI.
- NARRATIVE: Fix run 20261101T141554Z-fecb9b (ada): 20 steps, 682 s, 1.12 USD; the next head ffc76f3 passed every check and grew from 9 to 11 files, adding the package tests/awawa/recordings, which suggests a missing awawa recording was the cause; the ledger does not name it.
- NARRATIVE: Verification run 20261101T143054Z-b0608b (prudence): 19 steps, 200 s, 1.13 USD, verdict changes with one low finding on corpus/decisions.awawa:4902, a RATIONALE holding the timing of two awawa status runs instead of the reason of the ruling (rule decision_holds_ruling_rejections_reason).
- NARRATIVE: Remediation run 20261101T143554Z-2183ef (remediator): 12 steps, 117 s, 0.45 USD, fixed the finding in aebaf8d7; the second verification run 20261101T144549Z-2e46e1 (prudence): 9 steps, 30 s, 0.43 USD, verdict pass with no finding.
- NARRATIVE: Went well: no task parked or failed, every run ended done on its first segment, the review finding was answered in one round, and the eight CI checks of PR 288 are green at merge (pr-list document).
- NARRATIVE: Gap: the git-diff-stat collector reports 0 files, 0 insertions and 0 deletions, while the last preflight sized PR 288 at 11 files and 240 lines; the statistics files, insertions and deletions of this report understate the wave, and the collector most likely diffed the wave branch against a base that already held the merge.
- NARRATIVE: Next wave: have the build run wait for its CI before it reports, since the red CI cost a whole fix run (1.12 USD, 11 min); and make the git-diff-stat collector diff the wave branch against the merge base with main.
- SAMPLING: brigade/corpus: the reading that falls back to the branch of the MAIN field when no ref is named, and the single whole awawa status that now carries the types; the heart of B228.
- SAMPLING: brigade/commands: how brigade corpus and the Corpus view answer when neither --ref nor --worktree is given, in place of the usage they printed before.
- SAMPLING: tests/awawa/recordings: the recordings added by the fix run after the red CI, to see whether they record the awawa output the tests needed or only mask a dependency on the local awawa.
- SAMPLING: corpus/decisions.awawa: the RATIONALE of DECISION EveryReadingOfBrigadeCorpusRunsOneWholeAwawaStatusAndNoRefReadsTheMainBranch as rewritten in aebaf8d7, the one point the review sent back.

## Manual tests

| # | test |
| --- | --- |
| 1 | B228: brigade corpus <project> named with neither --ref nor --worktree reads the project at the branch of its MAIN field, and the ref of its document names that branch |
| 2 | B228: every reading of brigade corpus carries types, the entity types of the corpus at the ref read, whether --type is given or not |
| 3 | B228: the Corpus view opened on a project with no ref, the link of the project choice, answers 200 with the selector, its ref field pre-filled with that branch and its type list offering the types read, in place of the usage of brigade corpus |
| 4 | B228: tests/cli proves the path a user follows: GET /views/corpus/<project> with no parameter answers 200 with the ref pre-filled and the types offered, and GET /api/corpus/<project> with no parameter answers the document of the main branch with its types |

## Tester steps

| # | test |
| --- | --- |
| 1 | B228: from any directory, run brigade corpus brigade --json with neither --ref nor --worktree; check that the ref of the document printed is main, the branch the MAIN field of the project names. |
| 2 | B228: run brigade corpus brigade --json, then again with --type TASK; check that both documents carry a types list naming the entity types of the corpus (DECISION, MILESTONE, TASK and the others). |
| 3 | B228: start brigade serve, open the dashboard, choose the project brigade on the Corpus view; check that the page loads with its selector, the ref field pre-filled with main and the type list offering the types read, and that no usage text of brigade corpus is shown. |
| 4 | B228: with brigade serve running, request GET /views/corpus/brigade and GET /api/corpus/brigade with no parameter; check that both answer 200, the first with the ref main pre-filled and the types offered, the second with the document of the main branch and its types; python3 -m unittest tests.cli runs the same path. |
