Answers where each part of brigade lives in its repository: the entry point, the package, the tests, the plugins, the corpus, the Artifact sources and the documentation.

- `bin/brigade` — the entry point of a clone; `brigade/` — the package; `build.py` — the zipapp build.
- `tests/cli/` — black-box tests that run brigade as a subprocess; `tests/unit/` — tests of single modules;
  `tests/integration/` — the git and awawa gateways against a real repository or corpus in a temporary directory;
  `tests/guards/` — the guards that parse every module of `brigade/`: no static import of `brigade.adapters`,
  `brigade.collectors`, `brigade.checks` or `brigade.outputs` from outside its package, no read of the environment
  outside `brigade/system/paths.py` and the process runner; and the guards of this wiki, the adapter matrix of
  [Client adapters](Client-adapters.md) and the links between its pages.
- `brigade/adapters/clients/` — the built-in client adapters, `claude_code.py`, reached by name only;
  `brigade/adapters/test_clients/` — the adapters of the test suite, `fake.py`, which the resolver searches after
  `brigade/adapters/clients/`; the recordings the test suite replays live in `tests/cli/fixtures/recordings/`.
- `brigade/roles/data/` — the nine built-in role files, one per slot.
- `brigade/adapters/schedulers/` — the scheduler plugins, `systemd.py`, `cron.py` and `loop.py`, reached by name only;
  the templates of the units and of the cron line live in its `data/` folder.
- `brigade/runs/` — the run machinery: the procedure resolution, the brief, the segments and their hand-over, the run
  directory read by `runs list` and `runs show`.
- `corpus/` — the project's own awawa corpus: the schema, the milestones, the tasks, the decisions of the plan.
  Read it with `awawa status .` from the root of the repository.
- `artifact/blueprint/` — the sources of the published Artifact "Brigade Blueprint" (overview, plan, mockups, task
  board, demo, brief); `index.html` is the page, `parts/` the fragments it fetches.
- `artifact/use-cases/` — the sources of the published Artifact "Brigade cas d'utilisation": one sequence diagram per
  use case, the holes and defects, and the briefs of the runs that redo the map.
- `brigade/corpus/data/schema.awawa.tpl` — the schema of the operational corpus `brigade init` installs in the config
  directory (kept as a template so it does not join this corpus); every file brigade ships lives in a `data/` folder
  of the package, so the clone and the zipapp read the same files.
- `wiki/` — the documentation, these pages, published to the GitHub wiki on each push to `main`, as
  [Develop](Develop.md) says; `README.md` keeps what brigade is, the minimal install and the link to the wiki.
- `HANDOFF.md` — the working notes of the planning run: what was asked, what was answered, what was decided, what remains.

The status of a task is its `STATUS` in `corpus/tasks.awawa`, and nowhere else; the task board of the Artifact
is a view of it, and a status changed on the board binds nothing
(@DECISION.TheCorpusIsTheHomeOfTaskStatusTheBoardItsView).
