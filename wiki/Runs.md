Answers how `brigade run` runs a procedure as a slot, what a run keeps on disk, how its progress carries it across segments, how it is held on the clock, stopped and pruned, and how `brigade runs` lists, shows and follows it.

## Commands

```
brigade run <procedure> --slot <slot> [--project <name>] [--cwd <dir>] [--brief <file>] [--wave <wave>] [--task <task>]
            [--detach] [key=value ...]
brigade runs list [--wave <wave>] [--task <task>] [--json]  # every run: id, procedure, slot, role, project, state, outcome
brigade runs show <id> [--log] [--json]          # the summary of a run, its segments and its progress; --log adds its journal
brigade runs show <id> --follow                  # the same with --log, then each record as it is written
brigade runs stop <id>                           # stop a running run; exit 0 once it finished on stopped
brigade runs prune [--keep <n>] [--before <YYYY-MM-DD>] [--resumable] [--dry-run] [--json]
```

## Procedures

`brigade run` runs a procedure as a slot through the client adapter. A procedure is a Markdown file whose front matter
declares `capabilities` (`read`, `write`, `shell`, `net`, comma-separated) and `budget`, its steps; the body is what
the agent is asked to do. An argument holding a `/` or ending in `.md` is the path of that file; any other is a name,
sought among the procedures brigade ships, then in `procedures/<name>.md` of the instructions corpus `config.toml`
names. The ledger records the name, the file name without `.md`. A procedure found nowhere, or lacking either key,
exits 1 naming it.

## Slot, role and client

The slot resolves to its role as [`brigade roles`](Roles.md) shows, unless the project given by `--project` binds it otherwise:
`ROLE "slot=name"` binds the slot to the role of that name, sought in the order of resolution; `ROLESET builtin` keeps
the built-in roles only, `ROLESET corpus` the AGENT entity the table `[slots]` binds then the built-in role, and any
other `ROLESET` is a directory of role files, relative to the project's `PATH`, whose file declaring the slot comes
before the built-in role; the machine's `roles/` is skipped whenever a `ROLESET` is given. The client of the run is the
one `[slot_clients]` binds to its slot, else the project's `CLIENT`, else the `client` key of `config.toml`. The client receives the role, the capabilities the procedure declares that the
role allows, and a brief made of the procedure, the `key=value` arguments, the text of `--brief` and the progress
of the run, its path exported to it as `BRIGADE_PROGRESS_FILE`. It runs in `--cwd`, else the project's `PATH`, else the
current directory.

## The progress file

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

## The run directory and the exit codes

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

## The journal

During each segment brigade reads the new complete lines of `stdout.log` every `journal_poll_s` seconds of
`config.toml`, 2 by default, and the rest once the segment ends, and appends to `journal.jsonl` one JSON record per
action of the client: `schema_version`, `at` (the UTC instant brigade read it), `segment`, `kind` and `summary`, cut to
200 characters with `cut` true. The adapter's `actions` operation turns the output into actions, `tool` (the tool and
the path, command or pattern it acts on), `text` (its first line) and `result` (the outcome of the segment); a client whose
probe declares no `actions` has one record of kind `raw` per line. A `journal_poll_s` that is no positive number keeps
2 s, and `brigade doctor` names it. `runs show` prints the summary of a run and the outcome of each segment, then its
progress, rendered by the document plugin of the file the run wrote, `progress.md` or `progress.awawa`, and with
`--log` one line per record: its time, segment, kind and summary. With `--json` the document carries `progress`, its
`text` and its `entities`, `null` for a Markdown progress; a progress absent or holding no entry is `null` and prints
nothing, and a `progress.awawa` that `awawa lint --strict` refuses, a file caught in the middle of a write, is printed
as its raw text with `entities` `null`. `--follow` prints the summary and the segments, then each record once
its line is whole, read every `journal_poll_s` seconds, until the run is `finished` or `dead`; it then prints the
state and the outcome of the run and exits with the code `brigade run` gives that outcome, 1 for a dead run. SIGINT
or SIGTERM ends the follow alone, exit 0, the run going on; `--follow` with `--json` exits 2.

## The clock and the hand-over

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

## Stopping a run

A run is stopped by SIGTERM or SIGINT sent to brigade, the pid in `runs/<run id>/pid`, which is the process
`--detach` starts again. While a segment runs, brigade sends SIGTERM to the client's process group, SIGKILL 30 s
later if it still lives, and waits for it: no process of the group outlives brigade. The segment ends on `stopped`,
its `run.finished` with a null exit and its `nulls` naming the stop, its record in `processes.jsonl` on `stopped`, and
no segment is launched again, whatever the progress file holds; a signal received before the client starts or between
two segments ends the run the same way. `brigade run` exits 21, and `runs list` shows the run `finished` on
`stopped`. `brigade runs stop <id>` sends that SIGTERM and exits 0 once the run has finished on `stopped`; a run
already finished, holding no pid file, unknown, or whose pid no process holds, and a run the signal leaves on any
other end than `stopped`, exit 1 naming the run and why.

## Fallbacks

Two fallbacks follow the probe of the adapter. A client that counts no steps records null steps, the clock is the
run's only bound, and `brigade run` and `brigade doctor` warn that the budget is held on the clock. A client that grants
no tool one by one runs in its unattended mode, and a slot whose capabilities lack `write` then runs in a disposable
git worktree of the directory's `HEAD`, `runs/<run id>/worktree`, removed after the run.

## Pruning

After `brigade run` writes its result, the finished and dead runs beyond `runs_kept` of `config.toml`, 100 by default,
are removed, oldest first; a running run and a run the resume after a rate limit takes up are neither removed nor
counted, and a `runs_kept` that is no integer of 1 or more exits 1 naming the key and the file. `brigade runs prune`
runs the same removal on demand and prints each run removed: `--keep` replaces `runs_kept` for the call, `--before`
removes as well every run settled before that day in UTC, `--resumable` removes the runs to resume too, and
`--dry-run` prints what would go and removes nothing. A removal holds `locks/runs.lock`, first empties
`runs-removed/` of what an interrupted removal left there, and renames a run out of `runs/` before deleting it, so
`runs list` meets a whole run or none. A run whose `run.json` or `result.json` cannot be read is skipped, neither
removed nor counted, and named on stderr; `brigade run` keeps its exit code.
