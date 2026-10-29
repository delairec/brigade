---
capabilities: read, write, shell
budget: 75
---
# Procedure — deliver one task, test first, up to its pull request

Deliver one task of a project whose specification is an awawa corpus, in the worktree the tick cut for it: from its
entity to an open pull request carrying the code, what the task changes in the corpus, and its promotion. Deliver
that task and no other.

Arguments, which the Arguments section names: `task`, the TASK entity to deliver, and `base`, the branch of the wave
its pull request goes to. The brief names the worktree and its branch.

**Budget: 75 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (a ruling, a pull request number), and the next step.

## 1. Read the package

`brigade task context`, from the worktree. It prints the ancestry of the worktree and the output of its setup, the
task and its closure, the rules of the files it touches, the project's `AGENTS.md`, the acceptance commands, the task
number reserved for the run and the attribution lines. Its `TITLE` is what you deliver, its `SPEC` lines are your
acceptance criteria, its `RATIONALE` the design already settled. A live `BLOCKED_BY` question means the task is not
startable: stop and end blocked, naming it.

## 2. Write the failing tests of each SPEC

For each `SPEC` line, write the test that demands it before any line of the code it demands, and run it: it fails on
the business assertion, never on an import, a reference or a type error. A new module starts as a stub that raises a
not implemented error, so that the stub is the only cause of the failure. Keep the evidence of each failure for the
report.

## 3. Implement

Write only the code the failing tests demand, until they pass; then the broader tests of the project. Refactor with
the tests green. Record in the corpus, as you take it, each ruling the task leaves open: a `DECISION` naming the task,
in the file of its type, appended. A `SPEC` you cannot satisfy as worded, or that a ruling of the project
contradicts, is not yours to reword or override: stop and end blocked, naming the `SPEC` and the ruling, as step 1
does for a live `BLOCKED_BY`. Anchor each `SPEC` with an `IMPL` pointing at the code that delivers it.

## 4. Prove each branch is demanded

For each branch the implementation added (a condition, an arm, a guard, an early return, a fallback), remove it and
run the tests. A branch whose removal fails a test is demanded: put it back, and keep the test that failed for the
report. A branch whose removal fails no test is deleted: write the test that demands it and see it fail on its
business assertion, then write the branch anew from that test, as if for the first time; never paste the removed
branch back as it was.

## 5. Commit, then check until it passes

Commit the work with a Conventional Commits subject, the attribution lines of the package closing the message.
`brigade task check` refuses a worktree whose files differ from `HEAD`, so every change is committed before it runs.
It runs the acceptance commands of the project, then `awawa fmt --check` and `awawa lint --strict` on the corpus, then
the privacy check on the lines the branch adds since its base, each finding as `file:line`: a failure is corrected in
a new commit and the check run again, until it passes. A failure is investigated, never masked.

## 6. Open the pull request

`brigade task pr --subject <subject>`, the subject in the imperative and in English. It refuses a check that is not of
`HEAD` or that failed: run the check again rather than work around it. It prints the number of the pull request.

## 7. Promote

`brigade task promote`. It sets the task `implemented`, delivered by the pull request just opened, then formats,
lints, commits and pushes the corpus. Never promote before the pull request exists.

## 8. Report

The verdict first, in one line: the task delivered, or what stopped it. Then one fact per line: the pull request by
its number, the branch, the verdict of each acceptance command, the evidence of each failing test seen before its
code, the test each added branch failed on its removal, the entities written in the corpus by name, and the question
left to a ruling, verbatim, if there is one.

A run that stops on a ruling, at step 1, at step 3, or on a failing check whose repair needs a decision the task did
not settle, pushes nothing and ends blocked: its final message states the question on the lines above
`brigade-end: blocked`, and the tick parks the task on that question.
