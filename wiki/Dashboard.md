How `brigade serve` serves the local dashboard, which command each route runs, and how the dashboard is protected.

```
brigade serve [--port <port>]
```

`brigade serve` serves the dashboard on `127.0.0.1` alone, at the port of `--port`, else of the key `dashboard_port`
of `config.toml`, else 8470. It prints the URL and runs in the foreground until SIGINT or SIGTERM, then exits 0.

## Views

The page polls the view it shows every five seconds while its tab is visible.

- **Inbox** — the new signals by family and the proposed patterns, with their ratify and dismiss buttons.
- **Corpus** — choose a registered project, a ref, a type and a board field; it shows the tree of the type, the board
  and the dependencies of the entity clicked. It is read-only: its one form only changes the view shown, and
  awawa-web stays the editor.

`/views/<route>` serves the HTML fragment of the document `/api/<route>` serves.

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

> **Watch out:** a port already taken exits 1.

## Details and edge cases

<details><summary>Errors and protections</summary>

- A command that exits non-zero answers 404 for a wave, a project, a pattern or a signal its listing command does not
  list, 500 otherwise, with its standard error in the body.
- A request whose Host is not `127.0.0.1:<port>` answers 400.
- A POST without the token of the page in `X-Brigade-Token` and the Origin `http://127.0.0.1:<port>` answers 403.
- Every response carries `Content-Security-Policy: default-src 'self'`.

</details>
