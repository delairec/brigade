---
capabilities: read, shell
---
# Procedure — review one pull request of a wave

Judge one pull request a build run opened for its task, in the worktree of that task, and hand back a verdict: pass,
or changes with the findings that ask for them. You did not write the pull request; change nothing in it.

Arguments, which the Arguments section names: `pr`, the number of the pull request, absent for a task of a project
without a forge, which has none, and `task`, the TASK entity it delivers.

**Budget**: the turns the Budget section names, the cap of your role. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (a finding and its evidence), and the next step.

## 1. Read the package

`brigade review context <pr>`, from the worktree, `<pr>` left out when the Arguments name none: the package then
judges the head of the task branch against the branch of its milestone. It prints the task with its awawa context and
its closure; under `# goal`, the goal the task serves: its title, and the title, subject, description and source of
its milestone, the user's own words, or that it has no milestone; under `# reference`, each `REFERENCE` of the
task, a repository path, with the page it covers and the PNG files of that page captured at the head under review, the delivered
page and the reference page, which `review context` captures itself when they are missing, or none; a `REFERENCE` that is a URL is printed refused, with why; the diff of the pull request
against its base,
the findings of the preflight, the rules of the files the diff touches, and the grades a finding takes.

You judge three things: each `SPEC` line, an acceptance criterion; the delivery against the goal it serves; the
delivery against the reference it cites. The `SPEC` lines are never the whole of the judgment: a delivery that meets
each of them and misses its goal, or departs from its reference, does not pass. The task's `RATIONALE` is the design
already settled; the preflight already judged the ancestry, the checks, the corpus, the promotion, the untouched
files, the privacy and the body, so do not judge them again.

Once a verdict is recorded on the pull request, the package also prints a section `previous verdict`, the head that
verdict judged and each of its findings with the answer the remediation recorded for it, or none, and a section
`repair diff`, what changed since that head. The package holds a previous verdict: take the second-review path,
step 2b, in place of steps 2 to 5. It holds none: judge the whole pull request, steps 2 to 5.

## 2. Judge each acceptance criterion

For each `SPEC` line, find the test, the command or the line of code that proves it holds, and run what can be run.
A criterion nothing proves is not met. Read every changed file in full, not only the lines of the diff.

## 2b. Review again: judge the answer to each previous finding and the repair diff

Judge each finding of the previous verdict by its answer. A fix is checked in the repair diff: the finding is
resolved when the diff removes what it named. A challenge is accepted only when its argument holds against the code
and the `SPEC`, the goal, the reference or the rule the finding broke: a challenge to a goal finding is judged against
the goal under `# goal`, a challenge to a reference finding against the reference and its captures under
`# reference`, never against the `SPEC` lines alone. A finding left without an answer, a fix the diff does not carry, or a
challenge whose argument does not hold is not resolved: raise it again with its grade, its file and line updated to
the current head, low included.

Read in full every file the repair diff touches. Raise a new finding only inside the repair diff, and only of grade
medium, high or critical: a defect outside it, or of grade low, is not raised. Then judge the head against its goal
and its reference, steps 3 and 4, whatever the repair diff touches: a goal missed or a reference departed from is
raised again. Then go to step 6.

## 3. Judge the delivery against its goal

Ask what the task is for beyond its `SPEC` lines: the goal under `# goal`, the milestone it serves as the user put it,
or, for a task of no milestone, its own title. Judge whether the delivery, as its user meets it, reaches that goal.
A delivery that meets every `SPEC` line and misses the goal is a finding that asks for changes: `broken` names the
milestone, `@MILESTONE.<name>`, or the task, and the summary says what of the goal the delivery misses.

## 4. Judge the delivery against its reference

The reference is each entry under `# reference`, the `REFERENCE` values of the task: a mockup, a page or a
document, by its repository path. It is one of the criteria, never an example of a rule: compare the
delivery with the reference itself, the page or the section its `COVERS` names, never only with what the `SPEC`
lines transcribed from it, and its forms and interactions are kept, a selector staying a selector. A gap from it that no
`SPEC`, `RATIONALE` or recorded decision justifies is a finding that asks for changes, `broken` naming the
reference; it is never dismissed as a difference from an example. For a rendered output, a page, a view or a
document, read with your read capability every PNG slice the package names for each covered page, in the order it
numbers them, the delivered page then the reference page, and compare them: a capture taller than 2000 px is cut into
slices of 2000 px so that each reads legibly, and skipping one leaves part of the page unjudged. The pull request
body shows the whole pair side by side. A covered page
with no PNG pair is a finding: the delivery is not proven against it. An entry naming `read:` is a section no page
renders: read that file in full and compare it with the section, which needs no PNG pair; a `read:` file you cannot
open, a URL among them, is a finding. An entry naming `revises:` is a reference the task delivers itself, as the
planner ratified it at the base: judge the file the branch writes against the goal. The package reads each
`REFERENCE`, its `REVISES` and its `READ` at the base of the branch; ask whether the `READ` and the `REVISES` you are
shown stand at the base, the preflight promotion failing a branch that adds, changes or removes them, or that removes a
`REFERENCE`. A reference you cannot open, a URL among them, is a finding. A task
with no `REFERENCE` skips this step.

## 5. Look for defects

Wrong behaviour, missing cases, broken contracts, untested paths, and departures from the rules the package prints.
Each finding carries a grade among those the package prints, the file and the line it concerns, and the `SPEC`, the
goal, the reference or the rule it breaks, by its entity name or its repository path.

## 6. Hand back the verdict

Write the verdict as a JSON document in a file under `$BRIGADE_RUN_DIR`, `head` the commit under `# head` of the
package, the one you judged, each finding with a `summary` saying in one sentence what is wrong:

```json
{"head": "8885daa", "verdict": "changes", "findings": [{"grade": "high", "file": "src/cart.py", "line": 12, "broken": "@RULE.x", "summary": "the cart is emptied twice"}]}
```

A goal finding takes as `file` and `line` the corpus file and the line of the milestone entity, or of the task when
it has no milestone, as `awawa status MILESTONE .` prints them; a reference finding takes the path of the reference and
the line where the section its `COVERS` names opens.

`pass` when every criterion is met, the goal is reached, the reference is kept and no finding asks for a change: a
`pass` states the goal reached. `changes` otherwise, with at least one finding.
On the second-review path, `pass` when every finding of the previous verdict is fixed or soundly challenged, no
new finding is raised, the goal is reached and the reference kept: that `pass` states the goal reached too; `changes` otherwise, carrying the findings still open and the new ones.
Then `brigade review verdict <pr> --file <path>`, `<pr>` left out as in step 1. It validates the verdict and records
it, and posts it as a review of the pull request when the project's review policy asks for one; a verdict naming no
pull request is recorded in the ledger alone. A refusal names what to correct: correct the file and
hand it back again. A refusal naming a head no longer the head of the pull request, or of the task branch, ends the run without a verdict: the
tick reviews the new head once its preflight has run. The verdict it accepts is your result; end there.
