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
- `HANDOFF.md` — the record of the planning run, dated: it is never rewritten.

## Stack

Python 3.11.4 or later, standard library only; tests with `unittest`.

## Branches and GitHub

Every change reaches `main` through a pull request. GitHub operations run as the machine account `Clauche-bot`,
which already has write access to this repository: there is nothing to request.

## Bootstrap

From M2, brigade delivers its own milestones through its tick, as it does for any registered project: the timer
fires `brigade tick --once` every five minutes, the tick rebases `integration/<slug of the milestone TITLE>` onto
`main` once `main` has moved, and the open wave branches of the milestone onto it; then
the tick starts, for each active milestone, a wave of the ratified tasks read on the milestone branch, on
`integration/<wave>` cut from it, merges each verified task pull request into the wave branch, then opens the pull
request of the wave into the milestone branch and merges it once ready;
once every wave of the milestone is merged and no task of it is left todo, the tick opens the pull request of the
milestone branch into `main`, which the user alone merges. A session launches no wave and no task run by hand.

```
brigade scheduler install                   # writes the timer; again after every change to the unit templates
brigade wave show <wave>                    # the tasks of a wave, their state and their runs
brigade wave requeue <wave> <task>          # a parked task queued again for the next tick
brigade tick --dry-run                      # the snapshot and the plan the next tick would apply
```

The tick runs from the main checkout through `bin/brigade`: a fix to brigade reaches the tick once `main` is pulled
there. `awawa status TASK --where MILESTONE==@MILESTONE.M2 .` lists the tasks of a milestone.

## Commands

From the repository root, with `python3` alone:

```
python3 -m unittest                                 # the tests; tests/cli runs brigade as a subprocess
python3 build.py                                    # builds dist/brigade.pyz with the zipapp module
ln -s "$PWD/bin/brigade" ~/.local/bin/brigade       # installs brigade from the clone, any directory on PATH
```
