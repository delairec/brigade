---
capabilities: read, write, shell
---
# Procedure — put the branch of one task, wave or milestone back on its base

Rebase one branch onto the head of its base, in the worktree of that branch, after the tick found that git alone
could not: the rebase conflicts. The branch is the branch of a task, rebased onto the branch of its wave, or the
branch of a wave or of a milestone, rebased onto the branch of its milestone or onto the main branch. You did not
write the branch.

Arguments, which the Arguments section names: for the branch of a task, `task`, the TASK entity the branch delivers,
and either `pr`, the number of the pull request a build run opened for it, or `base`, the branch of its wave, when
the task has no pull request yet; for the branch of a wave or of a milestone, `base` alone, the branch it is rebased
onto.

**Budget: 30 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
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

Run the project's tests. Only when they pass, `brigade rebase done <pr>`: it refuses a branch that does not descend
from the head of the base, and pushes it. The push moves the task back to its preflight; end there. With no `pr`,
push nothing and end done once the tests pass: the next tick launches the build run of the task on the rebased
branch. With no `task`, the branch of a wave or of a milestone, `git push --force-with-lease origin <branch>` once
the tests pass, never a bare force, nothing on a project with no forge, then end done. When they fail after the rebase, push nothing and end blocked,
your final message naming each failing test and its failure on the lines above `brigade-end: blocked`: the tick
parks the task, or pauses the wave, on that failure.
