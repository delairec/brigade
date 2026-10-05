# AGENTS.md — brigade

Project context for the AI agents working in this repository, in addition to the general instructions of
`<rootDir>`. This file holds what a session needs *before* its first command; everything else lives in the corpus
of `corpus/` and is read with the tool.

## What brigade is

brigade is a CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does every mechanical step; a model is called only to judge — the first principle,
@DECISION.CliDoesTheMechanicalWorkAgentsOnlyJudge, read before any design choice.

## The corpus

The specification is the awawa corpus of `corpus/`, written in English, entity names included. **The workspace root
is the repository root**: every command takes `.` as its last argument from there, never a single file.

```
awawa status .                                                            # where the project stands
awawa context @TASK.X --skip reasoning --skip provenance --with-schema .  # before implementing or specifying X
awawa lint --closure @TASK.X .                                            # what X rests on, and what blocks it
awawa fmt --check . && awawa lint --strict .                              # the only checks of the repository today
```

- A new entity goes **at the end** of the file of its type (`decisions.awawa`, `tasks.awawa`, `milestones.awawa`).
- A task's status lives in the corpus alone; the task board of the Artifact is a view of it
  (@DECISION.TheCorpusIsTheHomeOfTaskStatusTheBoardItsView).
- A task is implemented only once ratified, `draft → todo`, in a pull request of its own.

## Layout

- `corpus/` — the corpus: the schema, the milestones, the tasks, the decisions of the plan
  (@DECISION.TheCorpusFolderIsDeclaredByTheProjectAndDefaultsToCorpus).
- `artifact/` — the sources of the published Artifact "Brigade Blueprint",
  <https://claude.ai/artifact/ENPmZkLZS85qhvVBakhXJe>; `index.html` is the page, `parts/` the fragments it fetches.
  A republish goes through the Artifact tool with `url` set to that address, after a read of it.
- `schema/_schema.awawa.tpl` — the schema `brigade init` installs in the operational corpus; a template, not part
  of this corpus.
- `HANDOFF.md` — the record of the planning run, dated: it is never rewritten.

## Stack

Python 3.11 or later, standard library only, POSIX sh only in the optional scheduler files, no third-party
dependency (@DECISION.PythonStandardLibraryOnly); tests with `unittest`. The AI client, the scheduler and the forge
are adapters, the collectors, checks and outputs are plugins, a kind of work is a recipe
(@DECISION.BrigadeNamesNoAiClientOutsideItsAdapters, @DECISION.AStudyIsDeterministicCollectorsThenOneJudgingRun,
@DECISION.AKindOfWorkIsARecipeAnInstanceAnOrder).

## Branches and GitHub

Every change reaches `main` through a pull request. GitHub operations run as the machine account `Clauche-bot`,
which already has write access to this repository: there is nothing to request.

## Bootstrap

Milestones M0 and M1 are delivered by the existing machinery: the roles of the instructions corpus, one pull
request per task. From M2, brigade delivers its own waves. `awawa status TASK --where MILESTONE==@MILESTONE.M0 .`
lists the tasks of a milestone.

## Commands

No command exists yet beyond awawa's. B01 delivers the entry point and fills this section.
