# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

The entry point exists with ten commands so far, `brigade --version`, `brigade doctor`, `brigade init`,
`brigade adapter`, `brigade project`, `brigade ledger`, `brigade roles`, `brigade tick`, `brigade scheduler` and
`brigade corpus`; every other one is a task of the corpus.

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
and the account it is logged in as, awawa-web and the instructions corpus `config.toml` names, `awawa lint --strict`
clean or not, are optional, each reported with its fallback, a missing one a warning.

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

## Tick and scheduler

A tick builds a snapshot of the facts, plans the actions they call for and applies them, round after round until the
plan is empty or ten rounds have passed. The planner plans no action yet.

```
brigade tick --once       # one tick, under the lock $XDG_STATE_HOME/brigade/locks/tick.lock
brigade tick --dry-run    # the snapshot and the plan, applied to nothing
brigade tick --loop       # a tick at once, then one every five minutes, until SIGTERM or SIGINT
brigade scheduler install
brigade scheduler status
```

`tick --once` takes the lock without waiting: when another tick holds it, it writes one line naming the lock on stderr,
writes nothing and exits 0. Otherwise it writes the heartbeat `$XDG_STATE_HOME/brigade/tick.json` atomically:
`schema_version`, `ts`, `duration_ms` and `actions_applied`. `--dry-run` takes no lock and writes nothing. `--loop`
reports each tick on stderr; a signal lets the tick under way finish, then the loop exits 0 with the number of ticks
attempted, stand-downs included. Every mode prints text or, with `--json`, a JSON document.

`scheduler install` installs what fires `brigade tick --once` every five minutes, chosen by the `scheduler` key of
`config.toml`, else, without the key or without `config.toml`, by a probe: `systemd` where `systemctl --user
is-system-running` answers `running` or `degraded`, `cron` otherwise. `systemd` writes `brigade.service` and
`brigade.timer` in `$XDG_CONFIG_HOME/systemd/user/`, then reloads the user manager and enables the timer now; `cron`
replaces the crontab line marked `# brigade scheduler install`, keeping every other line, appends the stderr of each
tick to `$XDG_STATE_HOME/brigade/tick.log` and discards its stdout, the heartbeat keeping the last tick; `loop` installs
nothing and names the `brigade tick --loop` command to keep running. The unit and the cron line run the brigade that
installed them with the `PATH`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME` and `XDG_CACHE_HOME` of the install, escaped for
systemd or quoted for the shell and cron. Run again, it leaves one pair of units or one line. `scheduler status` reports
the scheduler installed or `none`, its unit files or cron line, the next activation of the timer and the last tick read
from the heartbeat, and exits 0.

## A project's tree at a ref

```
brigade corpus <project> --ref <branch|sha> [--json] [-- <awawa args>]
brigade corpus <project> --ref worktree:<branch> [--json] [-- <awawa args>]
brigade corpus <project> --worktree <path> [--json] [-- <awawa args>]
```

`--ref <branch|sha>` resolves the ref to a commit of the project's repository and extracts `git archive` of that
commit, the whole tree, into `$XDG_CACHE_HOME/brigade/refs/<project>/<sha>/`, once: a SHA already there is read from
the cache. `--ref worktree:<branch>` reads in place the worktree where that branch is checked out, `--worktree <path>`
the worktree at that path, a detached HEAD included; uncommitted edits are visible. The command prints the project,
the ref, the SHA, the kind (`archive` or `worktree`) and the root of the tree, as text or, with `--json`, a JSON
document; an unknown project, a ref that resolves to no commit, and a branch or a path no worktree holds exit 1.

Given `-- <awawa args>`, it runs awawa with those arguments at the root of the tree instead, and passes its stdout,
its stderr and its exit code through unchanged, after one stderr line naming the SHA it read.

The cache holds at most `refs_cache_mb` of `config.toml`, 1024 by default: each read marks its SHA used, and after
each extraction the least recently read SHAs are removed until the cache is under that bound.

## Client adapters

brigade runs its agents through a client adapter, selected by the `client` key of `config.toml`: `claude-code` for
Claude Code, `fake` for the adapter that replays recorded result documents, or any name `<name>` for which an
executable `brigade-client-<name>` is on your `PATH`. The table `[clients.<name>]` of `config.toml` holds the settings
of that adapter; the fake reads `recordings`, the directory whose `<role>.json` it replays.

`brigade adapter <operation>` (or with `--json`) answers one operation of the configured adapter, the request read as
a JSON document on stdin: `probe`, `launch-argv`, `parse-result`, `resume-argv` and `transcripts`. An external adapter
answers the same operations as `brigade-client-<name> <operation>`, the request on stdin and its answer, a JSON
document, on stdout; brigade checks every answer against the shape of its operation and names the adapter, the
operation and the key of an answer that departs from it. The probe answers `models`, the model the adapter binds to
each reasoning level.

## Roles

A procedure calls a slot, never a role: `plan`, `build`, `verify`, `review`, `rebase`, `report`, `triage`, `rules`
and `explore`. A role is a Markdown file, a front matter between two `---` lines declaring `name`, `slot`, `work`,
`reasoning` (`deepest`, `deep`, `standard`, `light`), `capabilities` (`read`, `write`, `shell`, `net`,
comma-separated), `budget` and `returns`, then the system prompt; it never names a model, the client adapter binds
one to its reasoning level. A slot resolves to the first of:

1. the file of `$XDG_CONFIG_HOME/brigade/roles/` whose front matter declares that slot;
2. the AGENT entity of the instructions corpus (the `instructions` key of `config.toml`) that the table `[slots]`
   binds to it, `plan = "<agent name>"`, read through awawa at each resolution: its fields fill the front matter
   and its `awawa context` package is the body;
3. brigade's built-in role, under `brigade/roles/data/`.

```
brigade roles list [--json]          # the slot, the role, its source and the model of each slot
brigade roles show <slot> [--json]   # the role file the slot resolves to
brigade roles lint [--json]          # the built-in and the machine role files; exit 1 on a finding
```

## Ledger

Every event brigade records is one JSON line appended to `$XDG_STATE_HOME/brigade/ledger/<YYYY-MM>.jsonl`, the month
of its instant in UTC, under the lock `$XDG_STATE_HOME/brigade/locks/ledger.lock`; a file is never rewritten. Each line
carries `schema_version`, `ts` (ISO 8601 UTC with `Z`), `event` and the fields that event declares in
`brigade/ledger/declared_events.py`, which refuses any other name.

```
brigade ledger                                        # events by name, first and last instant, runs by outcome
brigade ledger --wave <id>                            # tasks, pull requests, steps per slot and role, pauses
brigade ledger --project <name> [--since <n>d|<YYYY-MM-DD>]
brigade ledger budgets [--last N]                     # p50 and p90 steps per procedure, 20 runs by default
brigade ledger compare --before <YYYY-MM-DD>          # the runs before that day against the runs from it on
```

Every view prints text or, with `--json`, a JSON document. A line that is not JSON, lacks its envelope or carries an
unknown `schema_version` is skipped, named with its file and line on stderr and in the document, and the command still
exits 0. Percentiles are taken by nearest rank over the runs that report a step count; the others are counted as
unmeasured, and a procedure with fewer than five measured runs is marked as an estimate. `compare` exits 1 when one
of its two periods holds no finished run.

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
- `brigade/roles/data/` — the nine built-in role files, one per slot.
- `brigade/adapters/schedulers/` — the scheduler plugins, `systemd.py`, `cron.py` and `loop.py`, reached by name only;
  the templates of the units and of the cron line live in its `data/` folder.
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
