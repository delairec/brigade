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
- `artifact/` — the sources of the published Artifact "Brigade Blueprint",
  <https://claude.ai/artifact/ENPmZkLZS85qhvVBakhXJe>; `index.html` is the page, `parts/` the fragments it fetches.
  A republish goes through the Artifact tool with `url` set to that address, after a read of it.
- `HANDOFF.md` — the record of the planning run, dated: it is never rewritten.

## Stack

Python 3.11 or later, standard library only; tests with `unittest`.

## Branches and GitHub

Every change reaches `main` through a pull request. GitHub operations run as the machine account `Clauche-bot`,
which already has write access to this repository: there is nothing to request.

## Bootstrap

Brigade delivers its own waves, one pull request per task: a wave launched by `/awawa-plan-wave-start` cuts one
worktree per task from the base, `git worktree add .claude/worktrees/<id> -b <branch> origin/<base>`, and starts
each task as a brigade run, never as an `Agent` call:

```
brigade run awawa-task --slot build --project brigade --cwd .claude/worktrees/<id> --brief <file> --detach task=@TASK.X base=<base>
```

`--brief` carries what the session established; `brigade runs list` follows the runs, `brigade runs show --log <run>`
one run live.
`awawa status TASK --where MILESTONE==@MILESTONE.F0 .` lists the tasks of a milestone.

## Commands

From the repository root, with `python3` alone:

```
python3 -m unittest                                 # the tests; tests/cli runs brigade as a subprocess
python3 build.py                                    # builds dist/brigade.pyz with the zipapp module
ln -s "$PWD/bin/brigade" ~/.local/bin/brigade       # installs brigade from the clone, any directory on PATH
```
