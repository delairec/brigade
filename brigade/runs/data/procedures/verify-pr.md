---
capabilities: read, shell
budget: 40
---
# Procedure — verify one pull request of a wave

Judge one pull request a build run opened for its task, in the worktree of that task, and hand back a verdict: pass,
or changes with the findings that ask for them. You did not write the pull request; change nothing in it.

Arguments, which the Arguments section names: `pr`, the number of the pull request, and `task`, the TASK entity it
delivers.

**Budget: 40 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (a finding and its evidence), and the next step.

## 1. Read the package

`brigade verify context <pr>`, from the worktree. It prints the task with its awawa context and its closure, the diff
of the pull request against its base, the findings of the preflight, the rules of the files the diff touches, and the
grades a finding takes. The task's `SPEC` lines are the acceptance criteria you judge, its `RATIONALE` the design
already settled; the preflight already judged the ancestry, the checks, the corpus, the promotion, the untouched
files, the privacy and the body, so do not judge them again.

## 2. Judge each acceptance criterion

For each `SPEC` line, find the test, the command or the line of code that proves it holds, and run what can be run.
A criterion nothing proves is not met. Read every changed file in full, not only the lines of the diff.

## 3. Look for defects

Wrong behaviour, missing cases, broken contracts, untested paths, and departures from the rules the package prints.
Each finding carries a grade among those the package prints, the file and the line it concerns, and the `SPEC` or the
rule it breaks, by its entity name.

## 4. Hand back the verdict

Write the verdict as a JSON document in a file under `$BRIGADE_RUN_DIR`:

```json
{"verdict": "changes", "findings": [{"grade": "high", "file": "src/cart.py", "line": 12, "broken": "@RULE.x"}]}
```

`pass` when every criterion is met and no finding asks for a change; `changes` otherwise, with at least one finding.
Then `brigade verify verdict <pr> --file <path>`. It validates the verdict and records it, and posts it as a review of
the pull request when the project's review policy asks for one. A refusal names what to correct: correct the file and
hand it back again. The verdict it accepts is your result; end there.
