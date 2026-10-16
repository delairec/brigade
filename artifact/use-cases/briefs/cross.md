# Brief of the cross-cutting pass

One run, role `max`, launched once the three inventories are written. `<OUT>` and `<TMP>` sit in the session's
scratchpad. Before the launch, the session gathers every issue of the three files into `<OUT>/issues-index.json`,
each keeping its `id`.

---

Goal: the cross-cutting pass over the inventory of brigade's use cases, holes and defects that three light-reasoning
runs produced. Done = `<OUT>/cross.json` exists, valid JSON, in the shape below, and the final message gives a
15-line summary. Temp files go in `<TMP>`. Change nothing in the repository.

Context: the repository root, branch `main` at `<SHA>`. Read the corpus only through awawa commands. Triggers met:
corpus_found, python_project. Run no brigade command that writes state; use a scratch `XDG_*` under `<TMP>`.

Inputs in `<OUT>`: `usecases-A.json`, `usecases-B.json`, `usecases-C.json`, and `issues-index.json`. Each use case is
a code-grounded sequence diagram; each issue is `{id, kind, severity, title, detail, evidence, use_cases,
addressed_by, suggestion}`, French text. State here what the session already verified itself.

The user's request, verbatim: "Une fois cette liste de cas d'utilisation répertoriée, il faudra ajouter lister les
\"trous\" et les \"défauts\" (comme par exemple: passer des commandes en chaine de caractère, ce n'est pas une bonne
idée, il y avait mieux à faire: lancer les commandes en séquence). […] jusqu'à ce qu'on ait une photo complète du
projet et de nos ambitions."

The work:

1. Verify against the code and the corpus every issue of severity high, and every medium one whose claim is
   surprising or load-bearing: confirmed, refuted, or adjusted (severity or claim corrected).
2. Group the duplicates across families and name the one to keep.
3. Add the cross-cutting holes and defects a single family cannot see: identity and linkage of entities across the
   lifecycle (request, wave, task, run, pull request), failure atomicity and recovery, states nobody writes, plan
   ordering, duplicated tasks, corpus hygiene, the gap between the product promise (unattended waves) and what the
   current milestone delivers. Each with evidence.
4. The critical path to the night delivery, "je veux que la vague se livre seule pendant la nuit": the ordered tasks
   that must land, their status, what each unblocks, and the steps no task covers.

Shape of `cross.json`:

```
{"verdicts":[{"id":"B3","verdict":"confirmed|refuted|adjusted","severity":"high|medium|low","note":"French, with evidence"}],
 "duplicates":[{"keep":"A7","drop":["B9","C4"],"note":"French"}],
 "issues":[{"kind":"hole|defect","severity":"high|medium|low","title":"French","detail":"French, 1-3 sentences",
   "evidence":"file:line or @ENTITY","use_cases":["use-case ids"],"addressed_by":"@DECISION.X / @TASK.X or null","suggestion":"French"}],
 "critical_path":[{"task":"@TASK.B141","status":"todo","title":"French, short","unblocks":"French, short"}],
 "critical_gaps":["French: a step of the night delivery no task covers, with evidence"]}
```
