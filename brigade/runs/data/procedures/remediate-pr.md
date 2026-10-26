---
capabilities: read, write, shell
budget: 50
---
# Procedure — answer the review of one pull request of a wave

Answer the changes requested on one pull request a build run opened for its task, in the worktree of that task: fix
what each finding shows to be wrong, or challenge it with the reason it does not hold, push, and record the answer to
each. You did not review the pull request.

Arguments, which the Arguments section names: `pr`, the number of the pull request, and `task`, the TASK entity it
delivers.

**Budget: 50 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below: the step done in one line, the facts the next
step needs and no command gives back (a commit, an answer decided), and the next step.

## 1. Read the request

`brigade review context <pr>`, from the worktree. It prints the head of the pull request, the request of the
preflight when one moved the task to changes requested, and the findings to answer: the findings of the verdict when
the project's review policy is verdict, the open review threads when it is approval. Each finding carries the
identifier its answer names.

## 2. Answer each finding

Read the code each finding points at. Fix what it shows to be wrong, test first, or challenge it with the reason it
does not hold. A finding that needs a decision the task did not settle is not yours to decide: push nothing, and end
blocked, your final message stating the question and the finding it comes from on the lines above
`brigade-end: blocked`. The tick parks the task on that question.

## 3. Push

Run the project's tests, commit, and push the branch of the pull request only when they pass. The push moves the task
back to its preflight.

## 4. Record the answers

Write the answers as a JSON document in a file under `$BRIGADE_RUN_DIR`, one entry per finding of the context, by its
identifier:

```json
{"answers": [{"finding": "1", "answer": "fixed by 8885daa: the cart total ignores removed lines"}]}
```

Then `brigade review reply <pr> --file <path>`. It records the answers, and posts each on its review thread when the
project's review policy is approval. A refusal names what to correct: correct the file and hand it back again. The
answers it accepts are your result; end there.
