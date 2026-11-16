---
capabilities: read, shell
---
# Procedure — judge the usage report of one reviewed pull request

Report what working with the corpus cost and returned on one pull request, from the evidence the collectors of the
order gathered, and nothing else: a fact they did not gather is a gap the report names, not a search you run.

Arguments, which the Arguments section names: `order`, the ORDER entity of the operational corpus, and `run`, the
run of that order you judge.

**Budget**: the steps the Budget section names, the cap of your role. On reaching it, stop and
summarise what is done, what is not, and what the next run picks up.

**Progress**: the file the Progress file section names. Read it first: holding an entry, it is an interrupted run to
resume at the step it names. Append one entry after each step below.

## 1. Read the package

`brigade order context <run> --json` prints each collector's summary with the path of its full document (the ledger
of the project, the review threads of the open pull requests, the corpus), the RESULT entity with the fields brigade
filled, and the schema of its type. The pull request judged is the one the order names in its parameter `pr`. Read a
full document only where its summary does not settle a point of the report.

## 2. Write the report

Copy the RESULT entity of the package into a file of the directory for your temporary files, then fill its prose
fields with this template, one field per line, in this order:

- `NARRATIVE "verdict: <the verdict on the pull request, in one line>"`
- `FINDING "went well: <a fact, with the document and the line that show it>"`, one per fact
- `FINDING "went wrong: <a fact, with the document and the line that show it>"`, one per fact
- `FINDING "remediation: <the change that would have avoided a fact that went wrong>"`, one per remediation
- `NARRATIVE "recurring: <a point the threads or the ledger show more than once>"`, one per point

Change no field brigade filled: the answer is refused if you do.

## 3. Hand it back

`brigade order answer <run> --file <path>`. It validates the answer against the schema of its type and records it.
A refusal names what to correct: correct it and hand it back again. The answer it accepts is your result; end there.
