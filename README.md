# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

The entry point exists; `brigade --version` is its only command so far, every other one is a task of the corpus.

## Install

brigade needs Python 3.11 or later and nothing outside its standard library.

From a clone, link the entry point into a directory on your `PATH`; brigade then runs from any working directory:

```
git clone https://github.com/delairec/brigade.git
mkdir -p ~/.local/bin
ln -s "$PWD/brigade/bin/brigade" ~/.local/bin/brigade
brigade --version
```

Or build the single-file zipapp, which needs `python3` alone, and run or copy `dist/brigade.pyz`:

```
python3 build.py
python3 dist/brigade.pyz --version
```

Below Python 3.11, brigade exits non-zero and names the version it needs and the version it found.

## Develop

```
python3 -m unittest                            # the tests: tests/cli runs brigade as a subprocess
awawa fmt --check . && awawa lint --strict .   # the checks of the corpus
```

The CI runs the tests and the zipapp build on Python 3.11 and on the latest Python release, on every pull request.

## Layout

- `bin/brigade` — the entry point of a clone; `brigade/` — the package; `build.py` — the zipapp build.
- `tests/cli/` — black-box tests that run brigade as a subprocess; `tests/unit/` — tests of single modules.
- `corpus/` — the project's own awawa corpus: the schema, the milestones, the tasks, the decisions of the plan.
  Read it with `awawa status .` from this directory.
- `artifact/` — the sources of the published Artifact "Brigade Blueprint" (overview, plan, mockups, task board,
  demo, brief); `index.html` is the page, `parts/` the fragments it fetches.
- `schema/_schema.awawa.tpl` — the schema of the operational corpus `brigade init` installs in the config directory
  (kept as a template so it does not join this corpus).
- `HANDOFF.md` — the working notes of the planning run: what was asked, what was answered, what was decided, what remains.

The status of a task is its `STATUS` in `corpus/tasks.awawa`, and nowhere else; the task board of the Artifact
is a view of it, and a status changed on the board binds nothing
(@DECISION.TheCorpusIsTheHomeOfTaskStatusTheBoardItsView).
