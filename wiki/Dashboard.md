Answers how `brigade serve` serves the local dashboard, which command each route runs, and how the dashboard is protected.

```
brigade serve [--port <port>]
```

`brigade serve` serves the dashboard on `127.0.0.1` alone, at the port of `--port`, else of the key `dashboard_port`
of `config.toml`, else 8470; it prints the URL and runs in the foreground until SIGINT or SIGTERM, then exits 0. A port
already taken exits 1. The page polls the view it shows every five seconds while its tab is visible.

## Routes

| Route                                 | Command run, with `--json`         |
|---------------------------------------|------------------------------------|
| `/api/waves`                          | `brigade wave list`                |
| `/api/waves/<id>`                     | `brigade wave show <id>`           |
| `/api/inbox`                          | `brigade inbox list`               |
| `/api/ledger`                         | `brigade ledger`                   |
| `/api/corpus`                         | `brigade project list`             |
| `/api/corpus/<project>?ref=<ref>`     | `brigade corpus <project> --ref <ref>`, and `--type`, `--field`, `--entity` of the parameters `type`, `field`, `entity` |

| POST route                            | Command run, with `--json`         |
|---------------------------------------|------------------------------------|
| `/api/inbox/ratify/<pattern>?kind=<kind>` | `brigade inbox ratify <pattern> --kind=<kind>`, the kind optional |
| `/api/inbox/dismiss/<id>`             | `brigade inbox dismiss <id>`       |

## Views and protections

`/views/<route>` serves the HTML fragment of the document `/api/<route>` serves; the Inbox view shows the new
signals by family and the proposed patterns, with their ratify and dismiss buttons. The Corpus view chooses a registered
project, a ref, a type and a board field, then shows the tree of the type, the board and the dependencies of the entity
clicked, read-only: its one form only changes the view shown; awawa-web stays the editor. A command that exits non-zero
answers 404 for a wave, a project, a pattern or a signal its listing command does not list, 500 otherwise, with its
standard error in the body. A request whose Host is not `127.0.0.1:<port>` answers 400; a POST without the token of
the page in `X-Brigade-Token` and the Origin `http://127.0.0.1:<port>` answers 403. Every response carries
`Content-Security-Policy: default-src 'self'`.
