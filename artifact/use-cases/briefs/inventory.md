# Brief of an inventory run

One run per family, three launched in one message, role `dora`. Replace `<F>`, `<TITLE>`, `<SCOPE>`, `<OUT>` and
`<TMP>` from the table below; `<OUT>` and `<TMP>` sit in the session's scratchpad, never in the repository.

| `<F>` | `<TITLE>`                      | `<SCOPE>` |
|-------|--------------------------------|-----------|
| A     | Mise en place et configuration | `brigade init`, `doctor`, `project add/list/show/pause/resume`, `scheduler install/status`, `roles list/show/lint`, `adapter *`, `corpus` and `corpus -- <awawa args>`, `processes list/show`, `config.toml` and `[slot_clients]`; milestones M0 and M7; the open questions of the corpus about init |
| B     | Exécution des vagues           | `wave new/start/list/show`, `plan` context and record, `tick` once or in a loop, `run` of a procedure as a slot, `runs list/show --follow/stop/prune`, the worktree per task, the pull request, the pass, the merge, the retry and resume of a failed run, intake and triage; milestones M1, M2, F0. The end-to-end "je veux que la vague se livre seule pendant la nuit" (timer → tick → runs → PR → review → merge) is one use case |
| C     | Observation et ambitions       | `ledger` overview, wave, project, `ledger budgets`, `ledger compare`, `collect`, `collectors`, cost and budget follow-up, and every milestone not yet built: M3, M4, M5, M6, M8, ADD0 |

---

Goal: inventory the use cases of brigade in family <F>, "<TITLE>", as code-grounded sequence diagrams, plus the holes
and defects of that family, and write them as one JSON file. Done = `<OUT>/usecases-<F>.json` exists, is valid JSON
(`python3 -m json.tool`), every message's `from` and `to` is a declared participant, and the final message gives a
10-line summary (counts by status, the 3 most serious defects). Write the file with a script; temp files go in
`<TMP>`. Stop exploring once every intent of the scope has a use case: the file comes before completeness.

Context: the repository root, branch `main` at `<SHA>`. Read the corpus only through awawa commands (`awawa status`,
`awawa show @TASK.X .`, `awawa context @TASK.X --skip reasoning --skip provenance .`, `awawa refs`). Code: one module
per subcommand in `brigade/commands/`, the packages beside it. Triggers met: corpus_found, python_project. Run no
brigade command that writes state; `--help` and pure reads are fine, under a scratch `XDG_*` in `<TMP>`.

Family <F> covers: <SCOPE>. List the tasks of a milestone with `awawa status TASK --where MILESTONE==@MILESTONE.X .`.
The other families are covered by other runs: reference them, do not inventory them.

A use case starts from the user's intent in the user's words (French), for instance "je veux suivre le déroulement
d'un run", whose manual path is "j'exécute brigade runs list", "je recopie l'id du run", "j'exécute brigade runs show
<id> --follow". It is drawn as a sequence diagram grounded in code: participants are the operator or the timer, the
CLI entry points, the modules and functions, the stores (files, ledger, git, config), the external processes (git,
gh, awawa, the client). Include the use cases only planned (task todo or draft) and those nobody planned that the
product needs (status `unplanned`). Each message carries the status of the code behind it: `implemented` with the
`file:line` of the function, `todo` or `draft` with the task, `missing` when neither code nor task exists.

Shape of the file:

```
{"family":"<F>","title":"<TITLE>","use_cases":[
 {"id":"kebab-id","title":"short French title","intent":"je veux … (French, the user's words)","actor":"operator|timer|agent",
  "status":"implemented|partial|planned|unplanned","milestones":["M0"],"tasks":["@TASK.B12"],
  "participants":[{"id":"op","label":"Opérateur","kind":"actor|cli|module|store|external","code":"brigade/commands/x.py"}],
  "messages":[{"from":"op","to":"cli","label":"brigade project add <path>","status":"implemented|todo|draft|missing",
    "code":"brigade/commands/project_add.py:42","task":"@TASK.Bxx or null",
    "frame":"optional: 'loop: …' or 'alt: …', consecutive messages sharing a frame are boxed together",
    "note":"optional short French note","reply":false}],
  "outcome":"what the user gets, French",
  "steps_human":["j'exécute …","je recopie …"]}],
 "issues":[{"id":"<F>1","kind":"hole|defect","severity":"high|medium|low","title":"French title","detail":"French, 1-3 sentences",
   "evidence":"file:line or @ENTITY","use_cases":["kebab-id"],"addressed_by":"@DECISION.X / @TASK.X or null",
   "suggestion":"French, what would be better"}]}
```

Labels of at most 60 characters, code identifiers untranslated, 6 to 15 messages per use case.

A hole is an intent no code and no task answers, or a step where the user does by hand what the CLI should chain
(copying an id, running two commands, editing a file, polling). A defect is a design or code choice weaker than an
obvious alternative. The user's own example of a defect: "passer des commandes en chaîne de caractère, ce n'est pas
une bonne idée, il y avait mieux à faire: lancer les commandes en séquence". A defect already ruled names its
decision or task in `addressed_by` and says whether a task implements it yet. Every issue carries evidence.
