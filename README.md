# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

The entry point exists with twenty-one commands so far, `brigade --version`, `brigade doctor`, `brigade init`,
`brigade adapter`, `brigade project`, `brigade request`, `brigade wave`, `brigade plan`, `brigade task`,
`brigade study`, `brigade collect`, `brigade collectors`, `brigade ledger`, `brigade roles`, `brigade tick`,
`brigade scheduler`, `brigade corpus`, `brigade run`, `brigade runs`, `brigade processes` and `brigade verify`;
every other one is a task of the corpus.

## Install

brigade needs Python 3.11.4 or later and nothing outside its standard library.

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

Below Python 3.11.4, brigade exits non-zero and names the version it needs and the version it found.

`brigade doctor` (or `brigade doctor --json`) tells whether brigade can run on the machine: Python 3.11.4 or later, git,
awawa 2.7 or later and the probe of the client adapter `config.toml` names are checked, a missing one is a finding and
the exit code is 1; a user systemd instance, gh
and the account it is logged in as, awawa-web and the instructions corpus `config.toml` names, `awawa lint --strict`
clean or not, are optional, each reported with its fallback, a missing one a warning; so is an installed
`_schema.awawa` that differs from the shipped one: brigade supports no operational corpus of an older schema,
throw it away and run `brigade init` again, then register the projects anew. A `POLICY` that sets `REVIEW approval`,
`verdict` by default, is a warning naming its project while the `build` and `review` slots of `[forge_accounts]` are not
bound to two distinct logins: GitHub refuses an approval by the author of a pull request. A `config.toml` that is not
TOML is reported with the error of its one read on every line that needs it, the client, gh, its logins, the review mode
and the instructions corpus, and gh is not run.

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

## Waves

A wave starts as a `REQUEST` entity of `requests.awawa` in the operational corpus: what the user wants for one
project, in their words. Every command below but `wave show`, `wave list` and `wave cancel`, which read the ledger
alone, exits 1 naming `brigade init` until the corpus exists, and each prints text or, with `--json`, a JSON
document.

```
brigade request new <project> <text>
brigade request show <request>
brigade request list [--project P]
brigade request cancel <request>
brigade plan record <request> --file <plan>
brigade wave start <project> [--task T ...]
brigade wave show <wave>
brigade wave list [--project P]
brigade wave cancel <wave>
brigade wave resume [<request>]
```

`request new` records the request as `<project>_r<n>`, `n` one above the highest its project holds, under the lock
of the corpus, with the UTC instant of its creation and the status `planning`, then launches the planner on it
detached, `brigade run wave-plan --slot plan --project <project> --detach request=<name>`, and prints the request and
the run, then the line `brigade runs show <run> --log`, the command that follows the planner. A project that is not
registered or is paused exits 1. `request show` prints a request, its status, its milestone, its pull request and the
instant of its creation, `-` for a field it does not hold yet; `request list` prints one row per request, those of one
project with `--project`. `request cancel` moves a `planning` or `planned` request to `cancelled`; a request of
another status exits 1 naming it. `plan record` takes the plan of a `planning` request, one `MILESTONE` and its
tasks, writes it in a detached worktree of the project's main branch, beside the entities of their types, runs
`awawa lint --strict` and commits it on `plan/<request>`; under the forge `none` it fast-forwards the main branch to
that commit at once, and under `github` it pushes the branch and opens a pull request to the main branch, titled
`docs(plan): <milestone title> (@REQUEST.<request>)`, as the login of the key `cli` of `[forge_accounts]`. Under
`PLAN_REVIEW auto`, the default, brigade merges that pull request itself, squash, as the same login, the login of the
key `review` approving it first when the forge requires an approving review; under `PLAN_REVIEW ask` the merge is
the user's. The request goes `planned` with its `MILESTONE` and, under `github`, its `PR`. A plan record replayed
once `plan/<request>` exists commits nothing again: it takes the pull request of that branch, pushes the branch and
opens it when the forge finds none, and marks the request planned. Every write to the operational corpus goes
through the lock, `awawa fmt`, `awawa lint --strict` and the commit of the registry's writes.

A wave is a batch of ratified tasks started together, recorded in the ledger alone. `wave start` composes it without a
model from the tasks `todo` of the project corpus at the main branch that hold a number in their name, belong to no
open wave and have no live blocker, admitting a task once every task of its `AFTER` is implemented or in the wave, in
the order of their number; `--task` takes exactly the tasks named and exits 1 on a task in an open wave, a task with no
number in its name, a task the corpus does not define or one whose `AFTER` is neither implemented nor named, and an
empty wave exits 1 naming the project. It names the wave `<project>_w<n>`, `n` one above the highest wave number of
the project in the ledger, records `wave.started` with the wave, the project, the branch and the tasks under the lock
of the ledger, then cuts `integration/<project>_w<n>` from the main branch and pushes it under the forge `github`; the
missing branch of an open wave is cut again, and a branch of the name that no `wave.started` names, local or remote,
exits 1. A wave is open until `wave.closed` or `wave.cancelled`. `wave show` prints a wave, its branch, the instant it
started and its last wave event, then each task with its last `task.state`, its pull request and its last run in the
wave, `-` when none; `wave list` prints one row per wave of the ledger, its project, branch, last wave event and task
count, the open waves first, those of one project with `--project`. `wave cancel` records `wave.cancelled`, stops the
live run of each task of the wave as `brigade runs stop` does and lists, per task, the run it stopped, the worktree of
its last run, and the branch and the pull request it opened, all left in place; a wave already closed or cancelled
exits 1 naming that event. The tasks of a cancelled wave are candidates of the next wave.

`wave resume` records `wave.resumed` for the wave of the request named, whatever the reason of its pause, or, without
one, for every wave paused on the forge account, the tick resuming by itself a wave paused on the quota; it prints each
wave it resumed, and a request whose wave is not paused exits 1 naming its state.

## Tasks

A build run works in the worktree of its task, on the branch `task/<slug>/<task>` the tick cut from the wave's branch
`integration/<slug>`. Every command below runs from that worktree, takes the task of the branch when `<task>` is left
out, exits 1 naming the cause when the branch or the task does not match, and prints text or, with `--json`, a JSON
document.

```
brigade task context [<task>]
brigade task check [<task>]
brigade task pr [<task>] --subject <subject>
brigade task promote [<task>] [--pr <n>]
```

`task context` prints the starting package of the run: the ancestry of the worktree and the output of its setup, the
task and its closure, the rules of the files it touches, the project's `AGENTS.md`, the acceptance commands, the task
number and the attribution reserved for it. `task check` refuses a worktree whose files differ from `HEAD`, naming them,
then runs each `ACCEPTANCE` line of the project as an argv, never through a shell, then `awawa fmt --check .` and `awawa
lint --strict .`, prints one line per command with its verdict and its duration, and the last 20 lines of each failing
one; it records the verdicts with the sha of `HEAD` in `$XDG_STATE_HOME/brigade/checks/<project>/<task>.json` and exits
1 when one fails. `task pr` refuses a task whose last check is not of `HEAD` or has a failing command, a task without
`TYPE` and a missing subject; it pushes the branch, creates the GitHub milestone named after the `TITLE` of the task's
`MILESTONE` when the repository has none, and opens the pull request on the wave's branch as the login of
`forge_accounts.build`, titled `TYPE(COMPONENT): <subject> (@TASK.<task>)`, its body the task, its criteria, the
verdicts of the check and the attribution. `task promote` sets `STATUS implemented` and `DELIVERED_BY` on the task, the
pull request of the last `task.pr_opened` unless `--pr` names another, formats and lints the corpus, commits with the
attribution lines and pushes, a second run replacing the `DELIVERED_BY` it wrote; it refuses a corpus whose `TASK`
schema does not declare them. The three record `task.pr_opened`, `milestone.created` and `task.promoted` in the ledger.

## Preflight

`brigade verify preflight <pr>` runs, from a checkout of a registered project, the deterministic checks of the pull
request a task opened, before any judgment: it reads the pull request as the login of `forge_accounts.cli`, fetches its
head and the wave's branch, and prints one entry per check, its verdict `pass`, `fail` or `info` and its findings, text
or, with `--json`, a JSON document; it exits 1 when a check fails.

| Check             | Fails when                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------------|
| `ancestry`        | the head does not descend from the head of the wave's branch                                    |
| `checks`          | a check run is not completed and successful                                                     |
| `corpus`          | `awawa fmt --check .` or `awawa lint --strict .` fails on the head, read from the tree cache    |
| `promotion`       | the task is not `implemented`, its `DELIVERED_BY` is not the pull request, a `SPEC` has no `IMPL` resolving |
| `untouched_files` | a `.awawa` file of the diff changes while none of its entities does                             |
| `privacy`         | an added line matches a `PRIVATE` pattern of the project, an e-mail address or a home path, where no `PUBLIC` pattern of the project matches the whole of it |
| `body`            | the body keeps a placeholder of its template                                                    |
| `size`            | never: it reports the files, lines, packages and layers the diff touches                        |

## Verification

```
brigade verify context <pr>
brigade verify verdict <pr> --file <verdict.json>
```

Both run from the worktree of the task whose pull request they judge. `verify context` prints in one read the head
it judges, the task with its `awawa context` and its closure, the diff of the pull request against its base, the
findings of the preflight, the rules of the path triggers of the files the diff touches when `config.toml` names an
instructions corpus, and the grades of a finding: `critical`, `high`, `medium` and `low`.

`verify verdict` reads `{"head", "verdict": "pass" | "changes", "findings": [{"grade", "file", "line", "broken"}]}`,
where `head` is the commit `verify context` printed and `broken` names the `SPEC` or the rule the finding breaks; it
refuses a document of another shape, a grade outside the four, `changes` without a finding, and a `head` that is no
longer the head of the pull request, exit 1 naming what to correct, and records nothing. It records the ledger event
`task.verdict` at that head. Under `REVIEW approval` of the project's `POLICY` it also posts the verdict as a GitHub
review of that commit, approving or requesting changes, as the login of the key `review` of `[forge_accounts]`, and
the event carries that login; under `REVIEW verdict`, the default, the event alone is the verdict and its login is
null.

## Studies

A study is a `STUDY` entity of `studies.awawa` in the operational corpus: deterministic collectors, then at most one
judging run, then an output. Every command prints text or, with `--json`, a JSON document.

```
brigade study new <name> --title T --output O [--question Q] [--project P] [--collector LINE ...] [--slot S] [--every E] [--answer TYPE]
brigade study run <name>
brigade study context <run>
brigade study answer <run> --file <answer.awawa>
brigade study list
brigade study show <name>
brigade study pause <name>
brigade study resume <name>
```

`study new` records the study through `awawa fmt`, `awawa lint --strict` and a commit, the question verbatim, and
runs it once unless `--every` is given. `study run` runs the steps `collect`, `judge` and `output`, each writing its
result under `runs/<id>/steps/` and the ledger events `order.started`, `step.done`, `step.failed`, `order.parked` and
`order.done` with the kind `study`; a failed step parks the study, and its next `study run` resumes that run at its
first undone step. `--slot none` makes a scan: no judging run, the answer holds the fields brigade filled.

`--every` takes minutes or hours, `<n>m` or `<n>h` such as `5m` or `1h`, `daily@HH:MM`, or a day of the week at an
hour, `mon@HH:MM` to `sun@HH:MM`, in the machine's timezone; `study new` refuses another form, exit 1 naming the value. A study is due when it never ran or when
its schedule has passed since its last `order.started`; a paused or archived study, or one parked at a step, is never
due, its next `study run` resuming it. Each tick runs every due study through `study run`, detached: a judging study
only while fewer than `study_runs` of `config.toml`, 2 by default, judging runs of studies are live on the machine, a
scan beyond that cap, and never a study while a run of it is live. `study_runs` below 1 is an error naming the key and
the file.

`study list` prints every study with its status, its schedule, its last run and the outcome of that run, `started`,
`done` or `parked`; `study show` prints the fields of one study, its last run and its outcome. `study pause` and
`study resume` move its `STATUS` between `active` and `paused` through `awawa fmt`, `awawa lint --strict` and a commit,
leave a study already in that status as it is, and exit 1 for an archived study.

A collector line is a collector name and its `key=value` parameters, or `shell: <command line>`, whose items are the
lines the command prints. `study name=<study>` collects the answer of the last run of that study. `pr-list
state=<state>` collects the pull requests of the project, read on the forge as the login of the key `cli` of
`[forge_accounts]`, `open` by default, or `merged`, `closed` or `all`, each with its number, title, head and base
branches, state, author, draft state, review decision, the verdict of its check runs and the task its head branch
`task/<slug>/<task>` names; it reads every one of them, page after page, is collected afresh on every call, and is
absent under `FORGE none`: `brigade collect pr-list` exits 1 naming it and `brigade collectors list` prints it in its
`absent` column.

The answer is an entity of the type `--answer` names, `ANSWER` by default: brigade fills `STUDY`, `RUN` and one
`COLLECTED` per collector, its summary and the path of its full document; the judging run fills `NARRATIVE` and
`FINDING`. The judging run reads `study context <run>` and hands its answer to `study answer`, which validates it by
`awawa lint` against the schema of its type and refuses one that changed a field brigade filled. The output step
writes it:

| `--output`        | where the answer goes                                                                          |
|-------------------|------------------------------------------------------------------------------------------------|
| `entity:<TYPE>`   | appended to the operational corpus through `awawa fmt`, `awawa lint --strict` and a commit     |
| `file:<pattern>`  | committed on the branch `brigade/study-<study>-<run>` of the project, pushed with a pull request where the project has a forge; `{run}` in the pattern is the run |
| `inbox`           | refused by `study new` and `study run` until task B22 gives the inbox a store                  |
| `issue`           | a forge issue of the project                                                                   |
| any other name    | `brigade-output-<name>` on `PATH`, given `{"schema_version", "study", "run", "markdown"}` on stdin |

Every output but `entity:` hands a person the Markdown rendered from the answer entity.

## Tick and scheduler

A tick builds a snapshot of the facts, plans the actions they call for and applies them, round after round until the
plan is empty or ten rounds have passed. Among those actions, it runs the due studies, as Studies says, and launches
each startable task of a running wave as a detached build run, in the worktree it cuts for the task, of `build-task`,
the procedure brigade ships, or of the one the key `build` of the table `[procedures]` of `config.toml` names in its
place, resolved as the argument of `brigade run` is, with the wave and the task as `--wave` and `--task`. It follows the pull request of each task past its launch,
read as the login of the key `cli` of `[forge_accounts]`: the task is recorded `pr_open` when its pull request opens,
`merged` when it merges, `parked` with the reason `pull request closed` when it closes unmerged, and the task's
worktree is removed once its pull request is merged or closed, never while a run holds it. On the pull request a task
in `pr_open` opened, once every check run completed, at least one unless the project declares `CHECK_RUNS none`, and
for each head once, it runs `brigade verify preflight`,
records its findings in `task.preflighted` and moves the task to `verifying` when no check fails. On a task in
`verifying` whose pull request is open, it starts a fresh detached run of the slot `review` in the task's worktree, of
`verify-pr`, the procedure brigade ships, or of the one the key `review` of `[procedures]` names, with `pr` and `task`
as its arguments, unless a run holds the worktree or a review run of the task already ended at that head other than on
a rate limit; once a `task.verdict` is recorded at the head of the pull request, it moves the task to `verified` on
`pass` and to `changes_requested` on `changes`. A task in `verifying` whose pull request head is no longer the head of
its last `task.preflighted` moves back to `pr_open`, where the preflight of the new head opens the next verification.
A running REQUEST that no
`wave.started` names, or whose pull requests the forge fails to read, is skipped, named on stderr, and the tick serves
the waves of the others.

Any run that finished on the `error_class` `rate_limit`, until its `reset` has passed, pauses every running wave of the
machine: `wave.paused` with the reason `quota` and `resume_at` the first instant after the tick's clock at the hour and
in the timezone of the result's `reset`, or that clock plus 30 minutes when `reset` is null, and the task of a build
run moves to `paused:quota`. A wave started during a quota pause is paused until the same `resume_at`. A
`forge_account.unavailable` of the ledger pauses every running wave, those started after it included, with the reason
`forge_account` and no `resume_at`, until `brigade wave resume`. The tick launches no run of a paused wave. The first tick past
`resume_at` records `wave.resumed` for the wave and resumes the run of each `paused:quota` task as its next segment,
through `resume-argv` with the session of its last segment, or as a fresh launch from its progress file when the
client adapter declares no resume, and moves the task back to `running`.

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
of that adapter; the fake reads `recordings`, the directory whose `<role>.json` it replays, or `<role>.resumed.json`
when that file exists and its brief opens on the `Progress so far` section, `features`, the
comma-separated features its probe declares (`step_count`, `tool_grants`, `reset_hour`, `graceful_stop`; none by
default), and, for
tests of the clock and of the hand-over, `delay`, the seconds it waits before answering, `progress`, a text it
appends as it is to the progress file of the run, in either form, and `interval`, the seconds it waits after each line of its recording;
`operations`, comma-separated, adds operations to its probe: with `actions`, a line of its recording that is a result
document is a result and any other line a text; with `transcripts`, it answers the document
`<session_id>.transcripts.json` of `recordings`.

The table `[slot_clients]` of `config.toml` binds a slot to another client adapter, `review = "vibe"`, one key per
slot among the nine; a slot it binds runs on that client, any other on the `CLIENT` of its project, else on the
`client` key. `brigade roles list`, `brigade doctor` and `brigade adapter <operation>` answer for the `client` key and
name every slot the table binds to another client, `slot <slot> runs on <client>`. `brigade roles list` and `brigade
adapter` state that key as `answers for <client>`, `brigade adapter` on stderr, its stdout holding the adapter's answer
alone; `brigade doctor` names it on its `client` line. `brigade roles list` probes the client of each such slot too,
its model column showing the model that client binds, and exits 1 naming an adapter it finds nowhere.

`brigade adapter <operation>` (or with `--json`) answers one operation of the configured adapter, the request read as
a JSON document on stdin: `probe`, `launch-argv`, `parse-result`, `resume-argv`, `transcripts` and `actions`. An external adapter
answers the same operations as `brigade-client-<name> <operation>`, the request on stdin and its answer, a JSON
document, on stdout; brigade checks every answer against the shape of its operation and names the adapter, the
operation and the key of an answer that departs from it. The probe answers `models`, the model the adapter binds to
each reasoning level.

The `outcome` of a `parse-result` answer is `done`, `handed_over` or `blocked` as the run declares it on the last line
of its final message, `brigade-end: <outcome>`, which the brief of every segment asks for; `undeclared` when that line
is missing or names another value; `failed` on an error of the client; `soft_limit` when the client ended the session
itself once the `stop_at` of its request had passed.

`brigade adapter matrix` prints one row per client adapter, built-in or `brigade-client-<name>` on your `PATH`, and one
column per capability, read from its probe with the settings of `config.toml`: `full` when the probe declares it,
`fallback` when brigade replaces it, `absent` for a launch or a result it cannot do; the legend names each fallback.
Every row carries its audience, a supported client or an adapter of the test suite, the modules of
`brigade/adapters/test_clients/`. An adapter whose probe fails gets a row naming the error, and the command exits 1.
`--json` prints the document, `--markdown` the two tables below, which are its output for the built-in adapters; a
test of `tests/guards/` fails when they drift.

<!-- adapter matrix: begin -->
| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour | Graceful stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude-code | full | full | full | full | full | full | full | full | full |

| Test-suite adapter | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour | Graceful stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fake | full | full | fallback | fallback | fallback | fallback | fallback | fallback | fallback |

Fallbacks:

- no resume: a fresh launch from the progress file
- no transcripts: brigade's journal of the run
- no actions: one raw record per line of the client's output
- no step count: steps null and the run held on the clock alone
- no tool grants: the client's unattended mode and a disposable worktree for a reading slot
- no reset hour: now plus thirty minutes
- no graceful stop: the hard cut at the wall-time limit
<!-- adapter matrix: end -->

An external adapter for Mistral Vibe, `brigade-client-vibe`, runs Vibe 2.26.0 unattended with `client = "vibe"`. It is
not shipped in this repository: it lives on the `PATH` of the machine that installed it, until a built-in `vibe`
adapter replaces it. With it on the `PATH`, `brigade adapter matrix --markdown` adds this row to the supported
clients:

| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour | Graceful stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vibe | full | full | full | fallback | fallback | full | full | fallback | fallback |

Its probe binds `mistral-large` to the levels deepest, deep and standard, and `mistral-medium-3.5` to light; it reads
the usage of a session from Vibe's session store, `~/.vibe/logs/session/unified`.

## Roles

A procedure calls a slot, never a role: `plan`, `build`, `review`, `remediate`, `rebase`, `report`, `triage`,
`rules` and `explore`. A role is a Markdown file, a front matter between two `---` lines declaring `name`, `slot`,
`work`, `reasoning` (`deepest`, `deep`, `standard`, `light`), `capabilities` (`read`, `write`, `shell`, `net`,
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
brigade run <procedure> --slot <slot> [--project <name>] [--cwd <dir>] [--brief <file>] [--wave <wave>] [--task <task>]
            [--detach] [key=value ...]
brigade runs list [--wave <wave>] [--task <task>] [--json]  # every run: id, procedure, slot, role, project, state, outcome
brigade runs show <id> [--log] [--json]          # the summary of a run and its segments; --log adds its journal
brigade runs show <id> --follow                  # the same with --log, then each record as it is written
brigade runs stop <id>                           # stop a running run; exit 0 once it finished on stopped
brigade runs prune [--keep <n>] [--before <YYYY-MM-DD>] [--resumable] [--dry-run] [--json]
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
before the built-in role; the machine's `roles/` is skipped whenever a `ROLESET` is given. The client of the run is the
one `[slot_clients]` binds to its slot, else the project's `CLIENT`, else the `client` key of `config.toml`. The client receives the role, the capabilities the procedure declares that the
role allows, and a brief made of the procedure, the `key=value` arguments, the text of `--brief` and the progress
of the run, its path exported to it as `BRIGADE_PROGRESS_FILE`. It runs in `--cwd`, else the project's `PATH`, else the
current directory.

The progress of a run is one file, in the form the key `document` of `config.toml` chooses for what brigade creates:
`awawa` by default, `progress.awawa`, an awawa corpus holding the STEP and HANDOVER schema brigade ships, then one
`STEP` per step completed and one `HANDOVER` per hand-over, named `s1`, `s2`, `h1` in order of writing; `markdown`,
`progress.md`, created empty. The extension of a file brigade reads back routes it to its plugin, `.md` to markdown and
`.awawa` to awawa; awawa stays a prerequisite whichever form is chosen. Every request to the document plugin carries
`schema_version` 1, and brigade checks every answer it reads against the shape of its operation, naming the plugin and
the operation when one breaks it. The brief of every segment names the path and the form of the progress and its frame: one entry per major step, what it did in one line, the facts it established,
one line each and five at most, a fact being what the next segment needs and no command gives back, and the next step
as the procedure names it, `complete` at the end; never command output, a diff, the course of the step, a restatement of
the brief or a fact an earlier entry holds. A run whose capabilities carry `shell` is also asked to run `awawa fmt` then
`awawa lint --strict` on the file after each append. Between two segments brigade formats then lints `progress.awawa`,
naming the file, and the next brief opens on `awawa status STEP`, `awawa status HANDOVER` and `awawa show` of the last
entity; when the lint fails, it opens on the lint output, the instruction to rewrite the file and the file whole, and
the run goes on with the same count of relaunches. In the markdown form the next brief opens on the file as it is.

Each run keeps its directory, `$XDG_STATE_HOME/brigade/runs/<run id>/`: `run.json` (what was resolved), `pid`,
`role.md` (the role file passed), `progress.awawa` or `progress.md`, `processes.jsonl` (its trail), `segments/<n>/` (`brief.md`, `stdout.log`, `stderr.log`,
`result.json`, the normalised result of the segment), `journal.jsonl` and, written last, `result.json`, the normalised
result of the last segment. Each segment appends one `run.finished` to the
ledger, every null field named in `nulls` with its reason. `--wave`, the name of the wave, and `--task`, the task it
delivers, both optional and independent, are written in `run.json` and in every `run.finished` of the run as `wave`
and `task`; an absent `wave` is null with the reason `not launched by a wave`, an absent `task` with the reason
`not launched for a task`. A `run.json` without the keys `wave` and `task` is refused,
naming the file and the key, and never upgraded: `runs list` leaves the run out, names it and the refusal on stderr and
under `skipped` with `--json`, and exits 0; `runs show` of that run fails on the refusal. `runs list --wave` and
`--task` keep the runs of that wave or that task. The command prints the run, text or `--json`, and exits
with the code of its outcome, that of its last segment: 0 `done`, 1 `failed`, 3 `undeclared`, 10 `blocked`, 11
`wall_limit`, 12 `turn_limit` (the last segment reached the client's step cap), 13 `soft_limit`, 20 `handed_over`, 21
`stopped`. `--detach` prints the run id (or `{"schema_version": 1, "run": ..., "pid": ...}`) and
exits 0, while brigade itself, started again in a new session with its output in `brigade.log`, runs the procedure to
its end, writing the result and the ledger as the foreground command does. `runs list` reports a run `finished` once it
has a result, `running` while its process lives, `dead` when the process is gone without one.

During each segment brigade reads the new complete lines of `stdout.log` every `journal_poll_s` seconds of
`config.toml`, 2 by default, and the rest once the segment ends, and appends to `journal.jsonl` one JSON record per
action of the client: `schema_version`, `at` (the UTC instant brigade read it), `segment`, `kind` and `summary`, cut to
200 characters with `cut` true. The adapter's `actions` operation turns the output into actions, `tool` (the tool and
the path, command or pattern it acts on), `text` (its first line) and `result` (the outcome of the segment); a client whose
probe declares no `actions` has one record of kind `raw` per line. A `journal_poll_s` that is no positive number keeps
2 s, and `brigade doctor` names it. `runs show` prints the summary of a run and the outcome of each segment, and with
`--log` one line per record: its time, segment, kind and summary. `--follow` prints the same, then each record once
its line is whole, read every `journal_poll_s` seconds, until the run is `finished` or `dead`; it then prints the
state and the outcome of the run and exits with the code `brigade run` gives that outcome, 1 for a dead run. SIGINT
or SIGTERM ends the follow alone, exit 0, the run going on; `--follow` with `--json` exits 2.

Every run is held on the clock: at `ceil(budget × 1.25) × seconds_per_step` seconds, `seconds_per_step` a key of
`config.toml` defaulting to 30, brigade sends SIGTERM to the client's process group, SIGKILL 30 s later, and the
segment ends with the outcome `wall_limit`, whether its soft limit has passed or not. The soft limit of a segment is
its wall-time limit minus `soft_limit_margin_s` of `config.toml`, a positive number defaulting to 120, none when the
limit is not above it: the `launch-argv` and `resume-argv` requests carry it as `stop_at`, the UTC instant to the
second computed at launch, null without one. A client whose probe declares `graceful_stop` ends its session between two
steps once `stop_at` has passed and answers the outcome `soft_limit`; brigade records that segment as one ended `done`,
its session, steps, usage and `cost_usd` included, and the run goes on as after a cut on the clock. The Claude Code
adapter passes a `PostToolUse` hook in `--settings` that stops the main session and its sub-agents after the tool call
that passes `stop_at`; a client declaring no `graceful_stop` keeps the hard cut. A segment that ends on the client's
step cap records a `signal.recorded`
`budget_reached` naming the procedure, the run and the budget; one cut on the clock or ended on `soft_limit` records a
`wall_limit_reached`
naming the same and `wall_limit_s`, the limit in seconds it was held to. A segment ending on `handed_over` or
`undeclared` records a `signal.recorded` of that name, naming the procedure, the run and the segment. In each of these
cases, when the document plugin answers that its progress holds an entry, it is launched again as a fresh segment whose
brief opens on what the plugin reads of it,
up to the `HANDOVERS` of the project's `POLICY`, 2 without one; a segment ending on `blocked` is never launched again.
A segment whose main steps, as `run.finished` counts them, exceed the budget of its procedure records a
`signal.recorded` `budget_exceeded` naming the procedure, the run, the segment, the budget and `steps`, the steps it
took, whatever its outcome and beside its `budget_reached` when it also reached the step cap; a segment whose steps
are null records none, and the signal launches nothing again.

A run is stopped by SIGTERM or SIGINT sent to brigade, the pid in `runs/<run id>/pid`, which is the process
`--detach` starts again. While a segment runs, brigade sends SIGTERM to the client's process group, SIGKILL 30 s
later if it still lives, and waits for it: no process of the group outlives brigade. The segment ends on `stopped`,
its `run.finished` with a null exit and its `nulls` naming the stop, its record in `processes.jsonl` on `stopped`, and
no segment is launched again, whatever the progress file holds; a signal received before the client starts or between
two segments ends the run the same way. `brigade run` exits 21, and `runs list` shows the run `finished` on
`stopped`. `brigade runs stop <id>` sends that SIGTERM and exits 0 once the run has finished on `stopped`; a run
already finished, holding no pid file, unknown, or whose pid no process holds, and a run the signal leaves on any
other end than `stopped`, exit 1 naming the run and why.

Two fallbacks follow the probe of the adapter. A client that counts no steps records null steps, the clock is the
run's only bound, and `brigade run` and `brigade doctor` warn that the budget is held on the clock. A client that grants
no tool one by one runs in its unattended mode, and a slot whose capabilities lack `write` then runs in a disposable
git worktree of the directory's `HEAD`, `runs/<run id>/worktree`, removed after the run.

After `brigade run` writes its result, the finished and dead runs beyond `runs_kept` of `config.toml`, 100 by default,
are removed, oldest first; a running run and a run the resume after a rate limit takes up are neither removed nor
counted, and a `runs_kept` that is no integer of 1 or more exits 1 naming the key and the file. `brigade runs prune`
runs the same removal on demand and prints each run removed: `--keep` replaces `runs_kept` for the call, `--before`
removes as well every run settled before that day in UTC, `--resumable` removes the runs to resume too, and
`--dry-run` prints what would go and removes nothing. A removal holds `locks/runs.lock`, first empties
`runs-removed/` of what an interrupted removal left there, and renames a run out of `runs/` before deleting it, so
`runs list` meets a whole run or none. A run whose `run.json` or `result.json` cannot be read is skipped, neither
removed nor counted, and named on stderr; `brigade run` keeps its exit code.

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
a run goes with its run, removed beyond `runs_kept` as the Runs section says. A detached run's records are written by the process it re-executes.

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

The CI runs the tests in parallel under pytest-xdist, then the zipapp build, on Python 3.11 and on the latest Python
release, lints and checks the format with ruff, configured by `ruff.toml`,
scans the repository with semgrep under its Python and security-audit rule packs,
reports the dead code of `brigade/` and `tests/` with vulture, run in the CI only, measures the line and branch coverage
of `brigade/` by the unit tests of `tests/unit` alone with coverage.py, in a job of its own on Python 3.11,
configured by `.coveragerc`, a report read in the job log only, the job failing below the
`fail_under` threshold of `.coveragerc`, never lowered,
and audits its workflows with zizmor, on every pull request; pytest, pytest-xdist, ruff, semgrep, vulture, coverage and
zizmor are pinned in `requirements-ci.txt`, which dependabot keeps current, and the pinned ruff gives the verdict that
counts. pytest runs the `unittest` cases as they are, and `python3 -m unittest` stays the local command.

The tests that need awawa run against the real awawa where it is on PATH, and otherwise against a fake that replays
the recordings of `tests/awawa/recordings/`: what the real awawa printed, its exit code and the files it rewrote, for
the same arguments on the same input files, each recording naming the awawa version it was made with and the order
its run ids sorted in, which the replay keeps for two runs of the same second. A call with no
recording fails its test, naming its arguments. The CI installs no awawa, so its tests run on the recordings and none
is skipped. Where awawa is on PATH, `tests/awawa/test_recordings.py` replays every recording against it and fails on a
difference, naming the recording, its version and the version `awawa --version` prints. A recording is made, or
renewed after a bump of awawa or a change of a call, from the real binary:

```
rm -r tests/awawa/recordings && AWAWA_RECORD=1 python3 -m unittest   # awawa on PATH
```

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
- `artifact/blueprint/` — the sources of the published Artifact "Brigade Blueprint" (overview, plan, mockups, task
  board, demo, brief); `index.html` is the page, `parts/` the fragments it fetches.
- `artifact/use-cases/` — the sources of the published Artifact "Brigade cas d'utilisation": one sequence diagram per
  use case, the holes and defects, and the briefs of the runs that redo the map.
- `brigade/corpus/data/schema.awawa.tpl` — the schema of the operational corpus `brigade init` installs in the config
  directory (kept as a template so it does not join this corpus); every file brigade ships lives in a `data/` folder
  of the package, so the clone and the zipapp read the same files.
- `HANDOFF.md` — the working notes of the planning run: what was asked, what was answered, what was decided, what remains.

The status of a task is its `STATUS` in `corpus/tasks.awawa`, and nowhere else; the task board of the Artifact
is a view of it, and a status changed on the board binds nothing
(@DECISION.TheCorpusIsTheHomeOfTaskStatusTheBoardItsView).
