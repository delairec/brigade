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

Once a verdict is recorded on the pull request, the package also prints a section `previous verdict`, the head that
verdict judged and each of its findings with the answer the remediation recorded for it, or none, and a section
`repair diff`, what changed since that head. The package holds a previous verdict: take the re-verification path,
step 2b, in place of steps 2 and 3. It holds none: judge the whole pull request, steps 2 and 3.

## 2. Judge each acceptance criterion

For each `SPEC` line, find the test, the command or the line of code that proves it holds, and run what can be run.
A criterion nothing proves is not met. Read every changed file in full, not only the lines of the diff.

## 2b. Re-verify: judge the answer to each previous finding and the repair diff

Judge each finding of the previous verdict by its answer. A fix is checked in the repair diff: the finding is
resolved when the diff removes what it named. A challenge is accepted only when its argument holds against the code
and the `SPEC` or the rule the finding broke. A finding left without an answer, a fix the diff does not carry, or a
challenge whose argument does not hold is not resolved: raise it again with its grade, its file and line updated to
the current head, low included.

Read in full every file the repair diff touches. Raise a new finding only inside the repair diff, and only of grade
medium, high or critical: a defect outside it, or of grade low, is not raised. Then go to step 4.

## 3. Look for defects

Wrong behaviour, missing cases, broken contracts, untested paths, and departures from the rules the package prints.
Each finding carries a grade among those the package prints, the file and the line it concerns, and the `SPEC` or the
rule it breaks, by its entity name.

## 4. Hand back the verdict

Write the verdict as a JSON document in a file under `$BRIGADE_RUN_DIR`, `head` the commit under `# head` of the
package, the one you judged, each finding with a `summary` saying in one sentence what is wrong:

```json
{"head": "8885daa", "verdict": "changes", "findings": [{"grade": "high", "file": "src/cart.py", "line": 12, "broken": "@RULE.x", "summary": "the cart is emptied twice"}]}
```

`pass` when every criterion is met and no finding asks for a change; `changes` otherwise, with at least one finding.
On the re-verification path, `pass` when every finding of the previous verdict is fixed or soundly challenged and no
new finding is raised; `changes` otherwise, carrying the findings still open and the new ones.
Then `brigade verify verdict <pr> --file <path>`. It validates the verdict and records it, and posts it as a review of
the pull request when the project's review policy asks for one. A refusal names what to correct: correct the file and
hand it back again. A refusal naming a head no longer the head of the pull request ends the run without a verdict: the
tick verifies the new head once its preflight has run. The verdict it accepts is your result; end there.
