How `brigade serve` serves the local dashboard, which command each route runs, and how the dashboard is protected.

```
brigade serve [--port <port>]
```

`brigade serve` serves the dashboard on `127.0.0.1` alone, at the port of `--port`, else of the key `dashboard_port`
of `config.toml`, else 8470. It prints the URL and runs in the foreground until SIGINT or SIGTERM, then exits 0.

## Views

The page polls the view it shows every five seconds while its tab is visible. Its seven views:

- **Home**, the view shown first — the document of `brigade status`: the projects with their pause or resume button,
  the open waves with a resume button on a paused one, the inbox and its scans, the quota, the last tick, the studies
  and the parked orders.
- **Waves** — the waves of `brigade wave list`; a wave opens its tasks grouped by state, a requeue button on each
  parked task, and the timeline of its events.
- **Inbox** — the new signals by family, the proposed patterns with their ratify and dismiss buttons, and the study
  answers, each opening the answer rendered from its entity.
- **Corpus** — choose a registered project, a ref, a type and a board field; it shows the tree of the type, the board
  and the dependencies of the entity clicked. It is read-only: its one form only changes the view shown, and
  awawa-web stays the editor.
- **Ledger** — the overview of `brigade ledger` and the turn budgets of `brigade ledger budgets`; a wave opens its
  events, and two ranges of days are compared by `brigade ledger compare`.
- **Reports** — the reports of `brigade report list`, each opening as `brigade report show` renders it.
- **Runs** — the runs of `brigade run list`, each opening its segments and its progress.

`/views/<route>` serves the HTML fragment of the document `/api/<route>` serves.

## Routes

| Route                                 | Command run, with `--json`         |
|---------------------------------------|------------------------------------|
| `/api/status`                         | `brigade status`                   |
| `/api/waves`                          | `brigade wave list`                |
| `/api/waves/<id>`                     | `brigade wave show <id>`           |
| `/api/inbox`                          | `brigade inbox list`               |
| `/api/inbox/<id>`                     | `brigade inbox show <id>`, a signal or a study answer |
| `/api/ledger`                         | `brigade ledger`                   |
| `/api/reports`                        | `brigade report list`              |
| `/api/reports/<id>`                   | `brigade report show <id>`         |
| `/api/runs`                           | `brigade run list`                 |
| `/api/runs/<id>`                      | `brigade run show <id>`            |
| `/api/corpus`                         | `brigade project list`             |
| `/api/corpus/<project>?ref=<ref>`     | `brigade corpus <project> --ref <ref>`, and `--type`, `--field`, `--entity` of the parameters `type`, `field`, `entity`; without `ref`, `brigade corpus <project>`, the document of the project's `MAIN` branch |

| POST route                            | Command run, with `--json`         |
|---------------------------------------|------------------------------------|
| `/api/inbox/ratify/<pattern>?kind=<kind>` | `brigade inbox ratify <pattern> --kind=<kind>`, the kind optional |
| `/api/inbox/dismiss/<id>`             | `brigade inbox dismiss <id>`, a signal or a pattern |
| `/api/projects/<project>/pause`       | `brigade project pause <project>`  |
| `/api/projects/<project>/resume`      | `brigade project resume <project>` |
| `/api/waves/<id>/resume`              | `brigade wave resume <id>`         |
| `/api/waves/<id>/tasks/<task>/requeue` | `brigade wave requeue <id> <task>` |

> **Watch out:** a port already taken exits 1.

## Details and edge cases

<details><summary>Errors and protections</summary>

- A command that exits non-zero answers 404 for a wave, a project, a pattern, a signal, a study answer, a report or a
  run its listing command does not list, 500 otherwise, with its standard error in the body.
- A request whose Host is not `127.0.0.1:<port>` answers 400.
- A POST without the token of the page in `X-Brigade-Token` and the Origin `http://127.0.0.1:<port>` answers 403.
- Every response carries `Content-Security-Policy: default-src 'self'`.

</details>
