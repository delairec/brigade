---
capabilities: read, shell
---
# Procedure — judge one run of a study

Answer the question of one study from the evidence its collectors gathered, and nothing else: the collectors already
collected, and a fact they did not gather is a gap the answer names, not a search you run.

Arguments, which the Arguments section names: `study`, the STUDY entity of the operational corpus, and `run`, the
run of that study you judge.

**Budget: 20 steps**, a declared estimate: no run of this procedure is recorded yet. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below.

## 1. Read the package

`brigade study context <run> --json` prints the question, each collector's summary with the path of its full
document, the answer entity with the fields brigade filled, the prose fields left to you, and the schema of its type.
Read a full document only where its summary does not settle a point of the answer.

## 2. Write the answer

Copy the answer entity of the package into a file of the directory for your temporary files, then fill the prose
fields the package leaves to you, as the schema of the type declares them. Change no field brigade filled: the
answer is refused if you do.

## 3. Hand it back

`brigade study answer <run> --file <path>`. It validates the answer against the schema of its type and records it.
A refusal names what to correct: correct it and hand it back again. The answer it accepts is your result; end there.
