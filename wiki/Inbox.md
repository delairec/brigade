What the inbox holds, how a signal is recorded, folded, listed, shown and dismissed, and how a note or the answer of a
study becomes a signal.

## Commands

```
brigade note <text> [--project P]   # record a note as a signal
brigade inbox list [--all]          # the new signals, --all adding the dismissed ones, then the proposed patterns
brigade inbox show <id>
brigade inbox dismiss <id>
```

Every command prints text or, with `--json`, a JSON document.

## Signals

The inbox holds the signals brigade records: facts seen by a connector, a note, the answer of a study. A signal is
the fold of every recording of one fingerprint:

- its count of recordings, its age since the first, and the evidence of the last;
- `new` until a dismissal, `dismissed` after it; a later recording raises its count and leaves it dismissed.

Its id is the sha256 of its fingerprint: `inbox list` prints its first 7 characters, and `inbox show` and
`inbox dismiss` take any prefix of 4 characters or more matching one signal.

| Kind | Recorded by | Fingerprint |
|---|---|---|
| `note` | `brigade note` | `note:` and the first 12 hexadecimal characters of the sha256 of the project, a newline and the text |
| `study` | a study whose output is `inbox` | `study:<study>:` and the first 12 hexadecimal characters of the sha256 of the Markdown rendered from the answer |

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
- `inbox list` prints each proposed pattern with its action and the signals it cites. With `--json`, its document also
  groups the listed signals into the families of the triage, by rule cited, file and check name.
- `inbox dismiss` leaves a dismissed signal as it is.
- The evidence of a study's signal is the study, the run and the Markdown rendered from the answer.

</details>
