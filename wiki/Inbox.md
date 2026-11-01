Answers what the inbox holds, how a signal is recorded, folded, listed, shown and dismissed, and how a note or the answer of a study becomes a signal.

The inbox holds the signals brigade records: facts seen by a connector, a note, the answer of a study. Every command
prints text or, with `--json`, a JSON document.

## Commands

```
brigade note <text> [--project P]
brigade inbox list [--all]
brigade inbox show <id>
brigade inbox dismiss <id>
```

## Signals

A recording or a dismissal is one line appended under `$XDG_STATE_HOME/brigade/locks/inbox.lock` to
`$XDG_STATE_HOME/brigade/inbox/signals.jsonl`, and the ledger event `inbox.recorded` or `inbox.dismissed`, each with
the fingerprint, the kind and the project. A signal is the fold of the lines of one fingerprint: its count of
recordings, its age since the first, the evidence of the last, `new` until a dismissal and `dismissed` after it, a later
recording raising its count and leaving it dismissed. Its id is the sha256 of its fingerprint: `inbox list` prints
its first 7 characters, and `inbox show` and `inbox dismiss` take any prefix of 4 characters or more matching one
signal, exit 1 naming the candidates otherwise. A line the inbox cannot read stops every command, exit 1 naming its
file and its number.

## Notes, listings and dismissals

`note` records a signal of kind `note`, fingerprint `note:` and the first 12 hexadecimal characters of the sha256 of
the project, a newline and the text, the project empty when none is given; a project that is not registered exits 1.
`inbox list` prints the new signals, `--all` adding the dismissed ones, then the proposed patterns, each with its
action and the signals it cites; with `--json`, its document also groups the listed signals into the families of the
triage, by rule cited, file and check name. `inbox dismiss` leaves a dismissed signal as it is. A study whose output
is `inbox` records its answer as a signal of kind `study`, fingerprint `study:<study>:` and the first 12 hexadecimal
characters of the sha256 of the Markdown rendered from the answer, evidence the study, the run and that Markdown.
