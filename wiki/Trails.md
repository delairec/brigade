Where the record of every subprocess brigade starts is kept, how long, and how to read it with `brigade processes` or
`--verbose`.

## Reading the trails

The trails are read through `brigade processes`, never searched by hand:

```
brigade processes list [--json]                  # every run, tick and command: kind, id, instant, processes, failed
brigade processes show <id> [--failed] [--json]  # the records of one run, tick or command, as written
```

`show` prints one line per record, `<outcome>  <exit code, else duration, else ->  <argv>`:

```
exited  128  git fetch origin
cut  600000 ms  claude -p 'deliver the task'
```

`--verbose`, accepted by every command before its name as after it, prints the same records on stderr as the command
writes them, stdout keeping the document alone:

```
brigade run: ran claude --print --output-format stream-json --verbose, exit 0 in 41250 ms
brigade run: ran /usr/bin/python3 /opt/brigade/bin/brigade run deliver --run-id 20261007T120000Z-48201, spawned pid 48213
brigade scheduler status: ran crontab -l, not on PATH
```

## Where the trails live

Every subprocess brigade starts appends one JSON line to the trail of the invocation that started it, whatever its
exit code.

| Invocation          | Trail                                                       |
|---------------------|-------------------------------------------------------------|
| `brigade run`       | `$XDG_STATE_HOME/brigade/runs/<run id>/processes.jsonl`     |
| a tick, each round of `tick --loop` included | `$XDG_STATE_HOME/brigade/ticks/<instant>.jsonl` |
| any other command   | `$XDG_STATE_HOME/brigade/commands/<instant>-<command>.jsonl` |

`<instant>` is the UTC compact form, `20261007T120000Z`, of the instant the command or the tick read.

> **Watch out:** the trails of `ticks/` and `commands/` are removed after `trail_days` of `config.toml`, 7 by default;
> the trail of a run goes with its run, removed beyond `runs_kept` as [Runs](Runs.md) says.

## Details and edge cases

<details><summary>The fields of a record</summary>

| Field | Holds |
|---|---|
| `schema_version` | |
| `argv` | |
| `cwd` | |
| `exit` | null when there is none |
| `duration_ms` | null for a spawned run |
| `outcome` | `exited`, `timed_out`, `not_found`, `no_working_directory` for a command whose working directory does not exist, `cut` for a client segment stopped by its wall limit, `spawned` for a detached run |
| `pid` | for a spawned run alone |

A record carries no instant: the name of its trail and the order of the lines one process wrote date it. The `spawned`
line of a detached run and the lines of the process it re-executes carry no order between them; a detached run's
records are written by the process it re-executes.

</details>

<details><summary>Retention in detail</summary>

The removal runs at each tick and each command. A `trail_days` that is no integer of 1 or more keeps every trail, and
`brigade doctor` names it.

</details>

<details><summary><code>list</code> and <code>show</code> in detail</summary>

`list` prints one entry per trail, newest first, `failed` counting the records not exited with code 0. `show` takes a
run id or the id `list` prints for a tick or a command; `--failed` keeps the records not exited with code 0, and an id
no trail holds exits 1, naming it.

</details>
