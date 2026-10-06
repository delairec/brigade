# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

The entry point exists with five commands so far, `brigade --version`, `brigade doctor`, `brigade init`,
`brigade adapter` and `brigade project`; every other one is a task of the corpus.

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

`brigade doctor` (or `brigade doctor --json`) tells whether brigade can run on the machine: Python 3.11 or later, git,
awawa 2.7 or later and the probe of the client adapter `config.toml` names are checked, a missing one is a finding and
the exit code is 1; a user systemd instance, gh
and the account it is logged in as, and awawa-web are optional, each reported with its fallback, a missing one a
warning.

`brigade init` (or `brigade init --json`) creates the operational corpus in `$XDG_CONFIG_HOME/brigade/`,
`~/.config/brigade/` by default: a git repository holding `_schema.awawa` and a `.gitignore`, committed with your git
identity, and `config.toml`, the machine configuration, every key commented out and never committed. It needs
`user.name` and `user.email` set in git. Run again, it rewrites nothing: a file that differs from the shipped one is
left as it is and reported as a warning.

## Projects

The projects brigade works on are `PROJECT` entities of `projects.awawa` in the operational corpus, the registry.
Every command below exits 1 naming `brigade init` until the corpus exists, and prints text or, with `--json`, a
JSON document.

```
brigade project add <path> [--name N] [--acceptance CMD]... [--heavy CMD]... [--setup CMD]... [--force]
brigade project list
brigade project show <name>
brigade project pause <name>
brigade project resume <name>
```

`project add` registers a git repository under the basename of its path, every character outside letters, digits and
`_` turned into `_`, or under `--name`. It discovers the absolute path, the `owner/name` of the `origin` remote, the
main branch (`origin/HEAD`, else the branch checked out), the folder holding the tracked `.awawa` files and the forge,
`github` for a remote on github.com. The acceptance commands and the per-worktree setup commands not given by flags are
guessed from a `package.json`, a Python project or a `Cargo.toml` at the root, and marked as guessed; the heavy suites
left to continuous integration are never guessed. A path or a name already registered is refused unless `--force`
replaces it. `pause` and `resume` set the status of a project.

Every write takes the lock of the corpus repository in `$XDG_STATE_HOME/brigade/locks/`, runs `awawa fmt` on
`projects.awawa` and `awawa lint --strict` on the corpus, then commits; a failing lint restores the file and exits 1.
These commands need awawa on `PATH`.

## Client adapters

brigade runs its agents through a client adapter, selected by the `client` key of `config.toml`: `claude-code` for
Claude Code, `fake` for the adapter that replays recorded result documents, or any name `<name>` for which an
executable `brigade-client-<name>` is on your `PATH`. The table `[clients.<name>]` of `config.toml` holds the settings
of that adapter; the fake reads `recordings`, the directory whose `<role>.json` it replays.

`brigade adapter <operation>` (or with `--json`) answers one operation of the configured adapter, the request read as
a JSON document on stdin: `probe`, `launch-argv`, `parse-result`, `resume-argv` and `transcripts`. An external adapter
answers the same operations as `brigade-client-<name> <operation>`, the request on stdin and its answer, a JSON
document, on stdout; brigade checks every answer against the shape of its operation and names the adapter, the
operation and the key of an answer that departs from it.

## Develop

```
python3 -m unittest                            # the tests: tests/cli runs brigade as a subprocess, tests/guards
                                               # checks the import graph and the environment reads
awawa fmt --check . && awawa lint --strict .   # the checks of the corpus
```

The CI runs the tests and the zipapp build on Python 3.11 and on the latest Python release, on every pull request.

## Layout

- `bin/brigade` — the entry point of a clone; `brigade/` — the package; `build.py` — the zipapp build.
- `tests/cli/` — black-box tests that run brigade as a subprocess; `tests/unit/` — tests of single modules;
  `tests/integration/` — the git and awawa gateways against a real repository or corpus in a temporary directory;
  `tests/guards/` — the guards that parse every module of `brigade/`: no static import of `brigade.adapters`,
  `brigade.collectors`, `brigade.checks` or `brigade.outputs` from outside its package, no read of the environment
  outside `brigade/system/paths.py` and the process runner.
- `brigade/adapters/clients/` — the built-in client adapters, `claude_code.py` and `fake.py`, reached by name only;
  the recordings the test suite replays live in `tests/cli/fixtures/recordings/`.
- `corpus/` — the project's own awawa corpus: the schema, the milestones, the tasks, the decisions of the plan.
  Read it with `awawa status .` from this directory.
- `artifact/` — the sources of the published Artifact "Brigade Blueprint" (overview, plan, mockups, task board,
  demo, brief); `index.html` is the page, `parts/` the fragments it fetches.
- `brigade/corpus/data/schema.awawa.tpl` — the schema of the operational corpus `brigade init` installs in the config
  directory (kept as a template so it does not join this corpus); every file brigade ships lives in a `data/` folder
  of the package, so the clone and the zipapp read the same files.
- `HANDOFF.md` — the working notes of the planning run: what was asked, what was answered, what was decided, what remains.

The status of a task is its `STATUS` in `corpus/tasks.awawa`, and nowhere else; the task board of the Artifact
is a view of it, and a status changed on the board binds nothing
(@DECISION.TheCorpusIsTheHomeOfTaskStatusTheBoardItsView).
