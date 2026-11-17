What the inbox holds, how a signal is recorded, folded, listed, shown and dismissed, how a pattern is ratified or
dismissed, and how a note or the answer of a study becomes a signal.

## Commands

```
brigade note <text> [--project P]   # record a note as a signal
brigade inbox list [--all]          # the new signals, --all adding the dismissed ones, the proposed patterns, the study answers
brigade inbox show <id>             # a signal with its evidence, or a study answer
brigade inbox dismiss <id>          # a signal, or a pattern with the signals it cites
brigade inbox ratify <pattern> [--kind rule|guard|lint|schema|skill|script]
```

Every command prints text or, with `--json`, a JSON document.

## Signals

The inbox holds the signals brigade records: facts seen by a connector, a note, the answer of a study, the items of a scan. A signal is
the fold of every recording of one fingerprint:

- its count of recordings, its age since the first, and the evidence of the last;
- `new` until a dismissal, `dismissed` after it; a later recording raises its count and leaves it dismissed.

Its id is the sha256 of its fingerprint: `inbox list` prints its first 7 characters, and `inbox show` and
`inbox dismiss` take any prefix of 4 characters or more matching one signal.

| Kind | Recorded by | Fingerprint |
|---|---|---|
| `note` | `brigade note` | `note:` and the first 12 hexadecimal characters of the sha256 of the project, a newline and the text |
| `study` | a study with a judging run whose output is `inbox` | `study:<study>:` and the first 12 hexadecimal characters of the sha256 of the Markdown rendered from the answer |
| `scan` | a study with `SLOT none` whose output is `inbox`, one signal per item its collectors print | `<study>:<project>:` and the `fingerprint` key of the item, the project empty for a study naming none |
| `check_run` | the tick, one signal per failing check run the collector `check-runs` lists | `cr:<project>:<pull request, or branch>:<check name>:<head>` |
| `review_thread` | the tick, one signal per review thread the collector `pr-threads` lists | `rt:` and the id of the thread |
| `stall` | the tick, for a task of an open wave that no run attends and no action touched for `stall_after` minutes of `config.toml`, 60 by default | `stall:<project>:<wave>:<task>` |
| `order_parked` | an order parked at one of its steps | `order_parked:<order>:<run>` |

> **Watch out:** a line the inbox cannot read stops every command, exit 1 naming its file and its number.

## Details and edge cases

<details><summary>Where signals are stored</summary>

A recording or a dismissal is one line appended under `$XDG_STATE_HOME/brigade/locks/inbox.lock` to
`$XDG_STATE_HOME/brigade/inbox/signals.jsonl`, and the ledger event `inbox.recorded` or `inbox.dismissed`, each with
the fingerprint, the kind and the project.

</details>

<details><summary>Notes, listings and dismissals</summary>

- `note` takes the project empty when none is given; a project that is not registered exits 1.
- A prefix that matches no signal, or several, exits 1 naming the candidates.
- `inbox list` prints each proposed pattern with its action and the signals it cites, then each study answer with its
  study and its project. With `--json`, its document also groups the listed signals into the families of the triage,
  by rule cited, file and check name.
- `inbox show` takes the id of a study answer as well, and prints the answer rendered from its entity.
- `inbox dismiss` leaves a dismissed signal as it is. Given the name of a `PATTERN`, it sets the pattern `dismissed` and
  dismisses every signal the pattern cites.
- `inbox ratify` ratifies a `new` pattern by its `ACTION`, for the registered project its `TARGET` names: `wave`
  records a request and launches its planner; `constraint` proposes a `CONSTRAINT` of the kind `--kind` names and
  records a request the same way; `order` records an `ORDER` of its `RECIPE`, active. A pattern whose action is
  `dismiss` exits 1 naming `brigade inbox dismiss`; a pattern that is not `new` exits 1 naming its status.
- The evidence of a study's signal is the study, the run and the Markdown rendered from the answer.

</details>
