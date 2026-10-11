# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

The entry point exists with thirteen commands so far, `brigade --version`, `brigade doctor`, `brigade init`,
`brigade adapter`, `brigade project`, `brigade ledger`, `brigade roles`, `brigade tick`, `brigade scheduler`,
`brigade corpus`, `brigade run`, `brigade runs` and `brigade processes`; every other one is a task of the corpus.

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
`schema_version`, `ts`, `duration_ms` and `actions_applied`. `--dry-run` takes no lock and writes neither the heartbeat nor a tick trail, its records going to the trail of a command. `--loop`
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
each extraction the least recently read SHAs are removed until the cache is under that bound. The reuse of a cached
tree, the placing of an extracted one and the removals run under the lock `$XDG_STATE_HOME/brigade/locks/refs-cache.lock`;
the reading of a tree after brigade printed its root does not, so another `brigade corpus` that prunes the cache can
remove a tree still read through `-- <awawa args>` when the bound is too tight to hold both.

## Client adapters

brigade runs its agents through a client adapter, selected by the `client` key of `config.toml`: `claude-code` for
Claude Code, `fake` for the adapter that replays recorded result documents, or any name `<name>` for which an
executable `brigade-client-<name>` is on your `PATH`. The table `[clients.<name>]` of `config.toml` holds the settings
of that adapter; the fake reads `recordings`, the directory whose `<role>.json` it replays, `features`, the
comma-separated features its probe declares (`step_count`, `tool_grants`, `reset_hour`; none by default), and, for
tests of the clock and of the hand-over, `delay`, the seconds it waits before answering, `progress`, a line it
appends to the progress file of the run, and `interval`, the seconds it waits after each line of its recording;
`operations`, comma-separated, adds operations to its probe: with `actions`, a line of its recording that is a result
document is a result and any other line a text; with `transcripts`, it answers the document
`<session_id>.transcripts.json` of `recordings`.

`brigade adapter <operation>` (or with `--json`) answers one operation of the configured adapter, the request read as
a JSON document on stdin: `probe`, `launch-argv`, `parse-result`, `resume-argv`, `transcripts` and `actions`. An external adapter
answers the same operations as `brigade-client-<name> <operation>`, the request on stdin and its answer, a JSON
document, on stdout; brigade checks every answer against the shape of its operation and names the adapter, the
operation and the key of an answer that departs from it. The probe answers `models`, the model the adapter binds to
each reasoning level.

`brigade adapter matrix` prints one row per client adapter, built-in or `brigade-client-<name>` on your `PATH`, and one
column per capability, read from its probe with the settings of `config.toml`: `full` when the probe declares it,
`fallback` when brigade replaces it, `absent` for a launch or a result it cannot do; the legend names each fallback.
Every row carries its audience, a supported client or an adapter of the test suite, the modules of
`brigade/adapters/test_clients/`. An adapter whose probe fails gets a row naming the error, and the command exits 1.
`--json` prints the document, `--markdown` the two tables below, which are its output for the built-in adapters; a
test of `tests/guards/` fails when they drift.

<!-- adapter matrix: begin -->
| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude-code | full | full | full | full | full | full | full | full |

| Test-suite adapter | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fake | full | full | fallback | fallback | fallback | fallback | fallback | fallback |

Fallbacks:

- no resume: a fresh launch from the progress file
- no transcripts: brigade's journal of the run
- no actions: one raw record per line of the client's output
- no step count: steps null and the run held on the clock alone
- no tool grants: the client's unattended mode and a disposable worktree for a reading slot
- no reset hour: now plus thirty minutes
<!-- adapter matrix: end -->

An external adapter for Mistral Vibe, `brigade-client-vibe`, runs Vibe 2.26.0 unattended with `client = "vibe"`. It is
not shipped in this repository: it lives on the `PATH` of the machine that installed it, until a built-in `vibe`
adapter replaces it. With it on the `PATH`, `brigade adapter matrix --markdown` adds this row to the supported
clients:

| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vibe | full | full | full | fallback | fallback | full | full | fallback |

Its probe binds `mistral-large` to the levels deepest, deep and standard, and `mistral-medium-3.5` to light; it reads
the usage of a session from Vibe's session store, `~/.vibe/logs/session/unified`.

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
brigade roles list [--json]                  # the slot, the role, its source and the model of each slot
brigade roles show <slot> [--json]           # the role file the slot resolves to
brigade roles show <slot> --short [--json]   # its front matter and the size of its body, in lines and bytes
brigade roles lint [--json]                  # the built-in and the machine role files; exit 1 on a finding
```

## Runs

```
brigade run <procedure> --slot <slot> [--project <name>] [--cwd <dir>] [--brief <file>] [--detach] [key=value ...]
brigade runs list [--json]                       # every run: id, procedure, slot, role, project, state, outcome
brigade runs show <id> [--log] [--json]          # the summary of a run and its segments; --log adds its journal
brigade runs show <id> --follow                  # the same with --log, then each record as it is written
```

`brigade run` runs a procedure as a slot through the client adapter. A procedure is a Markdown file whose front matter
declares `capabilities` (`read`, `write`, `shell`, `net`, comma-separated) and `budget`, its steps; the body is what
the agent is asked to do. An argument holding a `/` or ending in `.md` is the path of that file; any other is a name,
sought among the procedures brigade ships, then in `procedures/<name>.md` of the instructions corpus `config.toml`
names. The ledger records the name, the file name without `.md`. A procedure found nowhere, or lacking either key,
exits 1 naming it.

The slot resolves to its role as `brigade roles` shows, unless the project given by `--project` binds it otherwise:
`ROLE "slot=name"` binds the slot to the role of that name, sought in the order of resolution; `ROLESET builtin` keeps
the built-in roles only, `ROLESET corpus` the AGENT entity the table `[slots]` binds then the built-in role, and any
other `ROLESET` is a directory of role files, relative to the project's `PATH`, whose file declaring the slot comes
before the built-in role; the machine's `roles/` is skipped whenever a `ROLESET` is given. The project's `CLIENT`
replaces the client of `config.toml`. The client receives the role, the capabilities the procedure declares that the
role allows, and a brief made of the procedure, the `key=value` arguments, the text of `--brief` and the path of the
progress file, exported to it as `BRIGADE_PROGRESS_FILE`. It runs in `--cwd`, else the project's `PATH`, else the
current directory.

Each run keeps its directory, `$XDG_STATE_HOME/brigade/runs/<run id>/`: `run.json` (what was resolved), `pid`,
`role.md` (the role file passed), `progress.md`, `processes.jsonl` (its trail), `segments/<n>/` (`brief.md`, `stdout.log`, `stderr.log`,
`result.json`, the normalised result of the segment), `journal.jsonl` and, written last, `result.json`, the normalised
result of the last segment. Each segment appends one `run.finished` to the
ledger, every null field named in `nulls` with its reason. The command prints the run, text or `--json`, and exits 1
when its outcome is not `done`. `--detach` prints the run id (or `{"schema_version": 1, "run": ..., "pid": ...}`) and
exits 0, while brigade itself, started again in a new session with its output in `brigade.log`, runs the procedure to
its end, writing the result and the ledger as the foreground command does. `runs list` reports a run `finished` once it
has a result, `running` while its process lives, `dead` when the process is gone without one.

During each segment brigade reads the new complete lines of `stdout.log` every `journal_poll_s` seconds of
`config.toml`, 2 by default, and the rest once the segment ends, and appends to `journal.jsonl` one JSON record per
action of the client: `schema_version`, `at` (the UTC instant brigade read it), `segment`, `kind` and `summary`, cut to
200 characters with `cut` true. The adapter's `actions` operation turns the output into actions, `tool` (the tool and
the path, command or pattern it acts on), `text` (its first line) and `result` (`done` or `failed`); a client whose
probe declares no `actions` has one record of kind `raw` per line. A `journal_poll_s` that is no positive number keeps
2 s, and `brigade doctor` names it. `runs show` prints the summary of a run and the outcome of each segment, and with
`--log` one line per record: its time, segment, kind and summary. `--follow` prints the same, then each record once
its line is whole, read every `journal_poll_s` seconds, until the run is `finished` or `dead`; it then prints the
state and the outcome of the run and exits as `brigade run` does, 0 when the outcome is `done`, 1 otherwise. SIGINT
or SIGTERM ends the follow alone, exit 0, the run going on; `--follow` with `--json` exits 2.

Every run is held on the clock: at `ceil(budget × 1.25) × seconds_per_step` seconds, `seconds_per_step` a key of
`config.toml` defaulting to 30, brigade sends SIGTERM to the client's process group, SIGKILL 30 s later, and the
segment ends with the outcome `wall_limit`. A segment that ends on the client's step cap records a `signal.recorded`
`budget_reached` naming the procedure, the run and the budget; one cut on the clock records a `wall_limit_reached`
naming the same and `wall_limit_s`, the limit in seconds it was held to. In either case, when its progress file holds
something, it is launched again as a fresh segment whose brief opens on that file, up to the `HANDOVERS` of the
project's `POLICY`, 2 without one.

Two fallbacks follow the probe of the adapter. A client that counts no steps records null steps, the clock is the
run's only bound, and `brigade run` and `brigade doctor` warn that the budget is held on the clock. A client that grants
no tool one by one runs in its unattended mode, and a slot whose capabilities lack `write` then runs in a disposable
git worktree of the directory's `HEAD`, `runs/<run id>/worktree`, removed after the run.

## Trails

Every subprocess brigade starts appends one JSON line to the trail of the invocation that started it, whatever its
exit code: `schema_version`, `argv`, `cwd`, `exit` (null when there is none), `duration_ms` (null for a spawned run),
`outcome` (`exited`, `timed_out`, `not_found`, `no_working_directory` for a command whose working directory does not
exist, `cut` for a client segment stopped by its wall limit, `spawned` for a detached run) and, for a spawned run
alone, `pid`. A record carries no instant: the name of its trail and the order of the lines one process wrote date it.
The `spawned` line of a detached run and the lines of the process it re-executes carry no order between them.

| Invocation          | Trail                                                       |
|---------------------|-------------------------------------------------------------|
| `brigade run`       | `$XDG_STATE_HOME/brigade/runs/<run id>/processes.jsonl`     |
| a tick, each round of `tick --loop` included | `$XDG_STATE_HOME/brigade/ticks/<instant>.jsonl` |
| any other command   | `$XDG_STATE_HOME/brigade/commands/<instant>-<command>.jsonl` |

`<instant>` is the UTC compact form, `20261007T120000Z`, of the instant the command or the tick read. At each tick and
each command, the trails of `ticks/` and `commands/` older than `trail_days` of `config.toml`, 7 by default, are
removed; a `trail_days` that is no integer of 1 or more keeps every trail, and `brigade doctor` names it. The trail of
a run goes with its run. A detached run's records are written by the process it re-executes.

The trails are read through `brigade processes`, never searched by hand:

```
brigade processes list [--json]                  # every run, tick and command: kind, id, instant, processes, failed
brigade processes show <id> [--failed] [--json]  # the records of one run, tick or command, as written
```

`list` prints one entry per trail, newest first, `failed` counting the records not exited with code 0. `show` takes a
run id or the id `list` prints for a tick or a command; `--failed` keeps the records not exited with code 0, and an id
no trail holds exits 1, naming it. Its text prints one line per record, `<outcome>  <exit code, else duration, else
->  <argv>`:

```
exited  128  git fetch origin
cut  600000 ms  claude -p 'deliver the task'
```

`--verbose`, accepted by every command, before its name as after it, prints on stderr one line per record the command
writes, stdout keeping the document alone:

```
brigade run: ran claude --print --output-format stream-json --verbose, exit 0 in 41250 ms
brigade run: ran /usr/bin/python3 /opt/brigade/bin/brigade run deliver --run-id 20261007T120000Z-48201, spawned pid 48213
brigade scheduler status: ran crontab -l, not on PATH
```

## Ledger

Every event brigade records is one JSON line appended to `$XDG_STATE_HOME/brigade/ledger/<YYYY-MM>.jsonl`, the month
of its instant in UTC, under the lock `$XDG_STATE_HOME/brigade/locks/ledger.lock`; a file is never rewritten. Each line
carries `schema_version`, `ts` (ISO 8601 UTC with `Z`), `event` and the fields that event declares in
`brigade/ledger/declared_events.py`, which refuses any other name.

```
brigade ledger                                        # events by name, first and last instant, runs and segments by outcome
brigade ledger --wave <id>                            # tasks, pull requests, steps per slot and role, pauses
brigade ledger --project <name> [--since <n>d|<YYYY-MM-DD>]
brigade ledger budgets [--last N]                     # p50 and p90 steps per procedure, 20 runs by default
brigade ledger compare --before <YYYY-MM-DD>          # the runs before that day against the runs from it on
```

Every view prints text or, with `--json`, a JSON document. A line that is not JSON, lacks its envelope or carries an
unknown `schema_version` is skipped, named with its file and line on stderr and in the document, and the command still
exits 0. A run cut and resumed is one run of several segments, one `run.finished` event each: it counts once, by the
outcome and the error class of its last segment, and is dated by it. Every summary of steps gives the runs and the
segments side by side: a run is measured by the sum of its measured segments, partial when one of them is not
measured, and kept in the percentiles; a run with no measured segment is unmeasured. The steps to the first edit of a
run add the steps of the segments before the one that edited, and are partial only when one of those is not
measured. Percentiles are taken by nearest rank, and a procedure with fewer than five measured runs is marked as an
estimate. `compare` exits 1 when one of its two periods holds no finished run.

## Develop

```
python3 -m unittest                            # the tests: tests/cli runs brigade as a subprocess, tests/guards
                                               # checks the import graph and the environment reads
awawa fmt --check . && awawa lint --strict .   # the checks of the corpus
ruff check . && ruff format --check .          # the lint and the format, where ruff is installed
```

The CI runs the tests and the zipapp build on Python 3.11 and on the latest Python release, lints and checks the format
with ruff, configured by `ruff.toml`, scans the repository with semgrep under its Python and security-audit rule packs,
reports the dead code of `brigade/` and `tests/` with vulture, run in the CI only, measures the line and branch
coverage of `brigade/` by the whole suite with coverage.py, configured by `.coveragerc`, the brigade subprocesses
`tests/cli` launches and their own children included, a report read in the job log only, the job failing below the
`fail_under` threshold of `.coveragerc`, never lowered, and audits its workflows with zizmor, on every pull request;
ruff, semgrep, vulture, coverage and zizmor are pinned in `requirements-ci.txt`, which dependabot keeps current, and the
pinned ruff gives the verdict that counts.

## Layout

- `bin/brigade` — the entry point of a clone; `brigade/` — the package; `build.py` — the zipapp build.
- `tests/cli/` — black-box tests that run brigade as a subprocess; `tests/unit/` — tests of single modules;
  `tests/integration/` — the git and awawa gateways against a real repository or corpus in a temporary directory;
  `tests/guards/` — the guards that parse every module of `brigade/`: no static import of `brigade.adapters`,
  `brigade.collectors`, `brigade.checks` or `brigade.outputs` from outside its package, no read of the environment
  outside `brigade/system/paths.py` and the process runner.
- `brigade/adapters/clients/` — the built-in client adapters, `claude_code.py`, reached by name only;
  `brigade/adapters/test_clients/` — the adapters of the test suite, `fake.py`, which the resolver searches after
  `brigade/adapters/clients/`; the recordings the test suite replays live in `tests/cli/fixtures/recordings/`.
- `brigade/roles/data/` — the nine built-in role files, one per slot.
- `brigade/adapters/schedulers/` — the scheduler plugins, `systemd.py`, `cron.py` and `loop.py`, reached by name only;
  the templates of the units and of the cron line live in its `data/` folder.
- `brigade/runs/` — the run machinery: the procedure resolution, the brief, the segments and their hand-over, the run
  directory read by `runs list` and `runs show`.
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
