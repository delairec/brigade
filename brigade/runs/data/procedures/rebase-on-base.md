---
capabilities: read, write, shell
budget: 30
---
# Procedure — put one pull request of a wave back on its base

Rebase the branch of one pull request a build run opened for its task onto the head of the branch of its wave, in the
worktree of that task, after the tick found that git alone could not: the rebase conflicts. You did not write the
pull request.

Arguments, which the Arguments section names: `pr`, the number of the pull request, and `task`, the TASK entity it
delivers.

**Budget: 30 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (a conflict resolved and how), and the next step.

## 1. Read the conflict

`brigade rebase context <pr>`, from the worktree. It prints the branch of the pull request, its base, the branch of
the wave, and the files git reports in conflict between them.

## 2. Rebase

`git rebase origin/<base>`. Resolve each conflict by keeping what both sides meant. A conflict whose resolution needs
a decision the task did not settle is not settled: `git rebase --abort`, push nothing, and end blocked, your final
message stating the question, the files in conflict and what each side meant on the lines above
`brigade-end: blocked`. The tick parks the task on that question.

## 3. Hand the branch back

Run the project's tests. Only when they pass, `brigade rebase done <pr>`: it refuses a branch that does not descend
from the head of the base, and pushes it. The push moves the task back to its preflight; end there. When they fail
after the rebase, push nothing and end blocked, your final message naming each failing test and its failure on the
lines above `brigade-end: blocked`: the tick parks the task on that failure.
