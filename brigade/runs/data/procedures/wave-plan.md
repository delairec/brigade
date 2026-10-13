---
capabilities: read, write, shell
budget: 30
---
# Procedure — cut one request into a wave

Cut one request of a project into a wave: one MILESTONE entity and the TASK entities whose MILESTONE names it,
written against the project's own schema in one plan file, then handed to brigade to record. You plan; you deliver
nothing, and the plan file is the only file you write.

Argument, which the Arguments section names: `request`, the REQUEST entity of the operational corpus to plan.

**Budget: 30 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (the path of the plan file, the ids you chose), and the next step.

## 1. Read the package

1. `brigade plan context <request> --json`. It prints the request in the user's words, the inventory of the
   project's corpus, its active decisions, its draft and todo tasks, its TASK and MILESTONE schemas, the next free task
   number, and every IMPL anchor indexed by the file it points at.
2. A non-zero exit, or a non-empty `missing` list, means the plan cannot be written against this corpus: an entry
   `{"type": "<TYPE>"}` is a schema the corpus does not declare, and `{"type": "TASK", "field": "MILESTONE"}` a TASK
   schema that declares no MILESTONE field. Stop before writing any plan, report the message or each entry verbatim,
   and end blocked.
3. Read an entity the package names with `awawa show @TYPE.Name <corpus>` when its title is not enough to place the
   request; `<corpus>` is the `corpus` path of the package.

## 2. Cut the request into tasks

- One task is one pull request: a change a reviewer reads in one sitting, with acceptance criteria observable once
  it is delivered.
- Number the tasks from the next free task number, one each, in order; the id of a task is the prefix the
  project's existing TASK names share, then its number (`B129` next to `B128`). Read the names from the draft and
  todo tasks of the package, or from `awawa status TASK <corpus>` when it lists none. No TASK name, or names that
  share no prefix, is a question for your report, not a prefix you choose.
- The Conventional Commits type of a task's change goes in its `TYPE` field when the TASK schema of the package
  declares one, never in its id.
- A draft or todo task that already covers part of the request is named, not written again: the new tasks that
  depend on it carry `AFTER` on it.
- Two tasks that touch the same files, by the anchor index and the files their criteria name, are ordered: the one
  that goes second carries `AFTER` naming the first. No other order exists for the scheduler.
- What you cannot decide from the package and the corpus is not assumed: it is left out of the plan and named in
  your report as a question.

## 3. Write the plan file

1. Write `plan.awawa` in the directory that holds the progress file: one MILESTONE entity for the request, then
   the TASK entities whose MILESTONE names it, every field the schemas of the package mark REQUIRED and no field
   they do not declare.
2. `awawa fmt <plan file>`, then `awawa lint --strict <corpus> <plan file>`: the project's schema validates the
   plan. Correct every error in the plan file and run both once more. A second failure ends the run blocked: report
   the lint output verbatim, with the path of the plan file, and hand nothing over.
3. Write nothing else: no file of the repository, no branch, no entity of either corpus.

## 4. Hand the plan over

`brigade plan record <request> --file <plan file>` records the plan. A failure is reported verbatim, with the path of
the plan file, and never worked around.

## 5. Report

The verdict first, in one line: the wave planned and recorded, or what stopped it. Then one line per task: its id,
its title and its `AFTER` edges; then the path of the plan file; then each question left out of the plan.
