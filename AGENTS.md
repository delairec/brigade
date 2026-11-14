# AGENTS.md — brigade

Project context for the AI agents working in this repository, in addition to the general instructions of
`<rootDir>`. This file holds what a session needs *before* its first command; everything else lives in the corpus
of `corpus/` and is read with the tool.

## What brigade is

brigade is a CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does every mechanical step; a model is called only to judge.

## The corpus

The specification is the awawa corpus of `corpus/`, written in English, entity names included. **The workspace root
is the repository root**: every command takes `.` as its last argument from there, never a single file.

```
awawa status .                                                            # where the project stands
awawa context @TASK.X --skip reasoning --skip provenance --with-schema .  # before implementing or specifying X
awawa lint --closure @TASK.X .                                            # what X rests on, and what blocks it
awawa fmt --check . && awawa lint --strict .                              # the checks of the corpus
```

- A new entity goes **at the end** of the file of its type (`decisions.awawa`, `tasks.awawa`, `milestones.awawa`).
- A task is implemented only once ratified, `draft → todo`, in a pull request of its own.

## Layout

- `corpus/` — the corpus.
- `artifact/blueprint/` — the sources of the published Artifact "Brigade Blueprint",
  <https://claude.ai/artifact/ENPmZkLZS85qhvVBakhXJe>; `index.html` is the page, `parts/` the fragments it fetches.
  A republish goes through the Artifact tool with `url` set to that address, after a read of it.
- `artifact/use-cases/` — the sources of the published Artifact "Brigade cas d'utilisation"; its `README.md` says how
  to redo the map and republish it.
- `wiki/` — the documentation, one page per subject, published to the GitHub wiki
  <https://github.com/delairec/brigade/wiki> on each push to `main` by `.github/workflows/wiki.yml`; `wiki/Home.md`
  names every page with what it answers. `README.md` keeps what brigade is, the minimal install, the basic command
  and the link to the wiki.
- `HANDOFF.md` — the record of the planning run, dated: it is never rewritten.

## Stack

Python 3.11.4 or later, standard library only; tests with `unittest`.

## Branches and GitHub

Every change reaches `main` through a pull request. GitHub operations run as the machine account `Clauche-bot`,
which already has write access to this repository: there is nothing to request.

## Bootstrap

From M2, brigade delivers its own milestones through its tick, as it does for any registered project: the timer
fires `brigade tick --once` every five minutes. For each active milestone, the tick cuts its integration branch,
`integration/<slug of its TITLE>`, and rebases it onto `main` once `main` has moved. A wave is a batch of the ratified
tasks read on that branch, recorded in the ledger, with no branch and no pull request of its own: each task runs on
`<prefix>/<id>-<slug>` (`feature/B46-<slug>`, `fix/B231-<slug>`), cut from the branch of its milestone, and the tick
merges its verified pull request into it. A wave closes once each of its tasks is merged or parked. Once no task of the
milestone is draft or todo at its branch, a parked task being todo, and no wave of it is open, the tick runs the report
of the milestone, commits it on the milestone branch, commits `STATUS reached` on the milestone there in a commit of
its own, and opens the pull request of that branch into `main`, the report as its body: the milestone is reached when
the user merges it, the code and the status at once. A reached milestone takes no task: the tick serves a task of it
never and names it on stderr at each tick.
A task naming no milestone is cut from `main` and its pull request goes into `main`, which the user merges; the tick
replaces its body with the report of the task once it is ready.
A session launches no wave and no task run by hand.

```
brigade scheduler install                   # writes the timer; again after every change to the unit templates
brigade wave show <wave>                    # the tasks of a wave, their state and their runs
brigade wave requeue <wave> <task>          # a parked task queued again for the next tick
brigade tick --dry-run                      # the snapshot and the plan the next tick would apply
```

The tick runs from the main checkout through `bin/brigade`: a fix to brigade reaches the tick once `main` is pulled
there, so a fix the tick itself needs reaches `main` by a pull request of its own, or by a milestone delivered alone.
`awawa status TASK --where MILESTONE==@MILESTONE.M2 .` lists the tasks of a milestone.

## Commands

From the repository root, with `python3` alone:

```
python3 -m unittest                                 # the tests; tests/cli runs brigade as a subprocess
python3 build.py                                    # builds dist/brigade.pyz with the zipapp module
ln -s "$PWD/bin/brigade" ~/.local/bin/brigade       # installs brigade from the clone, any directory on PATH
```

A role launched by hand on a task proves its branch as a run of the tick does, from the worktree of the task, with
`uv` on PATH and neither ruff nor coverage:

```
brigade task check                                  # the ACCEPTANCE commands, the corpus checks and the privacy check
brigade task push                                   # pushes the branch with a lease, once a check of HEAD passed
uvx ruff@0.17.2 check . && uvx ruff@0.17.2 format --check .
uvx --from coverage==7.17.0 coverage run -m unittest discover -s tests/unit -t . && uvx --from coverage==7.17.0 coverage report
```
