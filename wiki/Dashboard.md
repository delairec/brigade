How `brigade serve` serves the local dashboard, which command each route runs, and how the dashboard is protected.

```
brigade serve [--port <port>]
```

`brigade serve` serves the dashboard on `127.0.0.1` alone, at the port of `--port`, else of the key `dashboard_port`
of `config.toml`, else 8470. It prints the URL and runs in the foreground until SIGINT or SIGTERM, then exits 0.

## The shell

The page is a left rail and a view; under 900px of width the rail becomes a top bar. The rail holds, from the top:

- **the project selector** — *All projects* or one registered project. The project chosen is carried in the address,
  `/?project=<name>#<view>`, and every view then keeps the rows of its document that name that project, at any depth,
  a row of `projects` naming it by its `name`; a row naming no project is kept. The selector and the heartbeat, which
  stand on every page, keep every row.
- **the heartbeat of the tick** — the last tick of `brigade scheduler status`, its age, and *stale* when the scheduler
  reports it, on every page.
- **Operate** — Home, Waves, Runs and Inbox, the views to act from.
- **Understand** — Ledger and Reports, the views to read what happened.
- **Addons** — the Corpus view, until the awawa tab replaces it.

The page polls the view and each region of the rail every five seconds while its tab is visible, and swaps a fragment
only when it changed, keeping the open `<details>` and the focus. A refused POST is shown in the notice above the view.

## Tones

Colour means state, and nothing else. Each state takes one tone, shown with its word and a shape, so that the tone is
never the only sign:

| Tone       | Shape | Means                    | States                                                         |
|------------|-------|--------------------------|----------------------------------------------------------------|
| `--you`    | ▲     | waits for you            | `parked`, `blocked` (a run stopped on a question), `paused`    |
| `--work`   | ●     | an agent works on it     | `running`, `fixing`                                            |
| `--review` | ◆     | under review             | `pr_open`, `verifying`, `changes_requested`                    |
| `--done`   | ✓     | delivered                | `merged`, `verified`, `done`, `closed`, `reached`              |
| `--limit`  | ■     | stopped on a limit       | `blocked:quota`, `wall_limit`, `turn_limit`, `soft_limit`      |
| `--failed` | ✕     | failed                   | `dead`, `failed`, a failed tick action                         |
| `--off`    | ○     | stopped on purpose       | `cancelled`, `stopped`, `dismissed`                            |
| `--faint`  | ·     | nothing to look at yet   | `queued`, `handed_over`, and any state not listed              |

`brigade/dashboard/data/dashboard.css` declares each tone in light and dark, the dark values following
`prefers-color-scheme`, beside the neutrals of the chrome; no rule of a view writes a colour as a literal.

## Three rules

Every view of the dashboard keeps three rules:

1. **Colour means state only**: the chrome — rail, borders, links, buttons — stays neutral.
2. **A page opens on one sentence and on what needs the user**, before any table.
3. **A figure says what it covers**: a cost is a floor when a run records none, and the lines skipped are said.

## Views

Its seven views:

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

`/views/<route>` serves the HTML fragment of the document `/api/<route>` serves. Two fragments serve the rail:
`/views/heartbeat` renders `brigade scheduler status --json`, answering 200 when the scheduler exits 1 on a stale tick,
and `/views/selector` renders the projects of `brigade project list --json`.

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
