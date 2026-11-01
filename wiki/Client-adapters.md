Answers which AI clients brigade runs its agents through, how a client is chosen per machine, project and slot, which operations an adapter answers, what each supported client can do, and the fallbacks brigade puts in place of what it cannot.

## Choosing the client

brigade runs its agents through a client adapter, selected by the `client` key of `config.toml`: `claude-code` for
Claude Code, `fake` for the adapter that replays recorded result documents, or any name `<name>` for which an
executable `brigade-client-<name>` is on your `PATH`. The table `[clients.<name>]` of `config.toml` holds the settings
of that adapter; the fake reads `recordings`, the directory whose `<role>.json` it replays, or `<role>.resumed.json`
when that file exists and its brief opens on the `Progress so far` section, `features`, the
comma-separated features its probe declares (`step_count`, `tool_grants`, `reset_hour`, `graceful_stop`; none by
default), and, for
tests of the clock and of the hand-over, `hold`, a file whose presence it waits out before answering, `progress`, a text it
appends as it is to the progress file of the run, in either form, and `interval`, the seconds it waits after each line of its recording;
`operations`, comma-separated, adds operations to its probe: with `actions`, a line of its recording that is a result
document is a result and any other line a text; with `transcripts`, it answers the document
`<session_id>.transcripts.json` of `recordings`.

## A client per slot

The table `[slot_clients]` of `config.toml` binds a slot to another client adapter, `review = "vibe"`, one key per
slot among the nine; a slot it binds runs on that client, any other on the `CLIENT` of its project, else on the
`client` key. `brigade roles list`, `brigade doctor` and `brigade adapter <operation>` answer for the `client` key and
name every slot the table binds to another client, `slot <slot> runs on <client>`. `brigade roles list` and `brigade
adapter` state that key as `answers for <client>`, `brigade adapter` on stderr, its stdout holding the adapter's answer
alone; `brigade doctor` names it on its `client` line. `brigade roles list` probes the client of each such slot too,
its model column showing the model that client binds, and exits 1 naming an adapter it finds nowhere.

## Operations

`brigade adapter <operation>` (or with `--json`) answers one operation of the configured adapter, the request read as
a JSON document on stdin: `probe`, `launch-argv`, `parse-result`, `resume-argv`, `transcripts` and `actions`. An external adapter
answers the same operations as `brigade-client-<name> <operation>`, the request on stdin and its answer, a JSON
document, on stdout; brigade checks every answer against the shape of its operation and names the adapter, the
operation and the key of an answer that departs from it. The probe answers `models`, the model the adapter binds to
each reasoning level.

## The outcome of a run

The `outcome` of a `parse-result` answer is `done`, `handed_over` or `blocked` as the run declares it on the last line
of its final message, `brigade-end: <outcome>`, which the brief of every segment asks for; `undeclared` when that line
is missing or names another value; `failed` on an error of the client; `soft_limit` when the client ended the session
itself once the `stop_at` of its request had passed.

## The adapter matrix

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

## The external vibe adapter

An external adapter for Mistral Vibe, `brigade-client-vibe`, runs Vibe 2.26.0 unattended with `client = "vibe"`. It is
not shipped in this repository: it lives on the `PATH` of the machine that installed it, until a built-in `vibe`
adapter replaces it. With it on the `PATH`, `brigade adapter matrix --markdown` adds this row to the supported
clients:

| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour | Graceful stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vibe | full | full | full | fallback | fallback | full | full | fallback | fallback |

Its probe binds `mistral-large` to the levels deepest, deep and standard, and `mistral-medium-3.5` to light; it reads
the usage of a session from Vibe's session store, `~/.vibe/logs/session/unified`.
