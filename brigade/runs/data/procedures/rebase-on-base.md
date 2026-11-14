---
capabilities: read, write, shell
---
# Procedure — put the branch of one task, wave or milestone back on its base

Rebase one branch onto the head of its base, in the worktree of that branch, after the tick found that git alone
could not: the rebase conflicts, or, for the branch of a milestone, git rebased it cleanly onto the main branch but
the rebased head fails the setup, the acceptance commands or the checks of the corpus of the project. The branch is
the branch of a task, rebased onto the branch of its wave, or the branch of a wave or of a milestone, rebased onto
the branch of its milestone or onto the main branch. You did not write the branch.

Arguments, which the Arguments section names: for the branch of a task, `task`, the TASK entity the branch delivers,
and either `pr`, the number of the pull request a build run opened for it, or `base`, the branch of its wave, when
the task has no pull request yet; for the branch of a wave or of a milestone, `base` alone, the branch it is rebased
onto. A run that repairs a red head rebases nothing and takes `branch` and `head`, the red commit, with no `base`:
alone, they name a milestone branch red at that head, repaired in place in its worktree, section 4; with `into`, the
main branch of the project, they name that main branch red at that head, repaired on the branch `branch` cut from it,
section 5.

**Budget**: the steps the Budget section names, the cap of your role. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (a conflict resolved and how), and the next step.

## 1. Read the conflict

`brigade rebase context <pr>`, from the worktree, or `brigade rebase context` when the arguments name no `pr`. It
prints the branch, its base, and the files git reports in conflict between them.

## 2. Rebase

`git rebase origin/<base>`, or `git rebase <base>` on a project with no forge. Resolve each conflict by keeping what both sides meant. A conflict whose resolution needs
a decision the task did not settle is not settled: `git rebase --abort`, push nothing, and end blocked, your final
message stating the question, the files in conflict and what each side meant on the lines above
`brigade-end: blocked`. The tick parks the task on that question, pauses the wave of a wave branch on it, and names
it at each tick for a milestone branch.

## 3. Hand the branch back

Run the project's tests. On the branch of a task, `brigade task check` until it passes, then `brigade task push`,
which pushes the branch with `--force-with-lease` and refuses a `HEAD` on which no check passed; then, with a `pr`,
`brigade rebase done <pr>`: it refuses a branch that does not descend from the head of the base. The push moves the task back to its preflight; end there. With no `pr`,
push nothing and end done once the tests pass: the next tick launches the build run of the task on the rebased
branch. With no `task`, the branch of a wave or of a milestone, `git push --force-with-lease origin <branch>` once
the tests pass, never a bare force, nothing on a project with no forge, then end done. When they fail after the rebase, push nothing and end blocked,
your final message naming each failing test and its failure on the lines above `brigade-end: blocked`: the tick
parks the task, or pauses the wave, on that failure.

On the branch of a milestone, a failure after the rebase is repaired in this run, as the waves of the milestone wait
for it: the worktree holds the head the tick rebased and did not push. Find what the main branch and the milestone
branch each meant where they meet, change the code so that both hold, commit it on the branch as
`fix(<scope>): <what the repair restores>`, and run the tests again; push once they pass, as above. A repair that
needs a decision the branch did not settle is not made: push nothing and end blocked, naming each failing test, its
failure and the question on the lines above `brigade-end: blocked`; the tick names it at each tick.

## 4. Repair a red branch in place

With the arguments `branch` and `head` alone. `brigade rebase context --head <head>`, from the worktree, prints the
branch, its red commit and each command that failed at it. The worktree holds the branch at that commit: rebase
nothing. Run the failing commands, find what each failure breaks, change the code so that they pass, and commit it
on the branch as `fix(<scope>): <what the repair restores>`. Run the project's tests; once they pass,
`git push --force-with-lease origin <branch>`, never a bare force, nothing on a project with no forge, then end done:
the tasks, the pull requests and the rebases waiting on the branch resume once the tick reads its head green. A
repair that needs a decision the branch did not settle is not made: push nothing and end blocked, naming each failing
command, its failure and the question on the lines above `brigade-end: blocked`; the tick names it at each tick and
launches no other repair of that head.

## 5. Repair the main branch on a fix branch

With the arguments `branch`, `head` and `into`. `brigade rebase context --head <head> --into <into>`, from the
worktree, prints the fix branch, the red commit of the main branch and each check that failed at it. The worktree
holds the branch `branch`, cut from that commit: repair the failures there as section 4 does, commit as
`fix(<scope>): <what the repair restores>`, run the project's tests, and once they pass
`brigade rebase pr --into <into>`: it pushes the branch and opens its pull request into `<into>`, its title the subject
of the commit, as the login of the run, and records that login in the ledger; never `git push` nor `gh pr create`
yourself. End done on the pull request, which the user merges: every
rebase onto the main branch waits until its head is green again. On a project with no forge, push nothing and
end done naming the branch, which the user merges. A repair that needs a decision is not made: push
nothing and end blocked as section 4 does.
