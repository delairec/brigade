How `brigade serve` serves the local dashboard, which command each route runs, and how the dashboard is protected.

```
brigade serve [--port <port>]
```

`brigade serve` serves the dashboard on `127.0.0.1` alone, at the port of `--port`, else of the key `dashboard_port`
of `config.toml`, else 8470. It prints the URL and runs in the foreground until SIGINT or SIGTERM, then exits 0.

## The shell

The page is a left rail and a view; under 900px of width the rail becomes a top bar. The rail holds, from the top:

- **the brand mark**, linking Home.
- **the project selector** — *All projects*, with their count, or one registered project, applied as soon as it is
  chosen, with no button. The project chosen is carried in the address,
  `/?project=<name>#<view>`, and every view then keeps the rows of its document that name that project, at any depth,
  a row of `projects` naming it by its `name`; a row naming no project, or whose `project` is `null` as for a
  machine-wide study and its scans, is kept. The selector and the heartbeat, which
  stand on every page, keep every row.
- **Operate** — Home, Waves with the waves open, Runs with the runs live, and Inbox with the proposed patterns,
  marked when one waits: the views to act from.
- **Understand** — Ledger, and Reports with their count: the views to read what happened.
- **Addons** — the awawa tab of each project holding a corpus, listed for the project chosen alone when one is.
- **the heartbeat of the tick**, at its foot — *Tick alive* or *Tick stale* with a dot in its tone, the time of the
  last tick of `brigade scheduler status` and its age, its duration and the actions it applied, on every page.

The link of the view shown is marked as the current page. Every view opens on its head: its title, one line saying
what the page is for, and the time it was read.

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

- **Home**, the view shown first — it opens on one sentence saying whether brigade is stopped (the scheduler reports
  the tick stale), working (a run is live) or idle, in the tone of that state, and a second sentence saying how many
  things wait for the user; then four tiles: the open waves and how many are halted, the live runs, what waits for
  the user with the age of the oldest, and the quota tokens of the window, with thousands separators, with the waves
  it blocks. **Needs you** lists what waits for the user, one row each with a mark, a title, why, and one action, a
  link to the view to act in or the command to copy: a halted wave with its reason, the proposed patterns of the
  inbox as one row with their count, the scans holding new signals as one row, a pull request of a milestone waiting
  for the user's merge and a parked order, or says nothing needs the user; the stall signals whose task merged since
  close the list as one faint row. **At work** is a table of the open waves, each with its project, its state as a
  pill, a strip of its tasks by state with how many merged, and its live run; **Last 24 hours** counts the waves
  started and closed, the pull requests opened and merged, the milestones reported, the run segments finished and the
  failed tick actions; **Routine** is a table of the studies, their period, their last run, its outcome and what
  comes next; **Projects** is a table of the projects with their state, their forge and its remote, their open waves,
  the link to their corpus when they hold one and their pause or resume button; a parked order is a row of Needs you.
  **Next tick** shows the decisions of `brigade tick --dry-run --json` by action, read when the page loads, at each
  new tick and on its refresh button, never by the poll.
- **Waves** — the waves of `brigade wave list`, opening on one sentence counting the waves open, parked and blocked,
  and four tiles: the waves open now with the parked and the blocked, the waves started with their count by month
  from `brigade ledger`, the waves closed with the cancelled, and the tasks merged out of the tasks the last 12 waves
  served, with the waves that merged nothing. Each row, the newest wave first, shows the wave linking its page, its
  state as a pill (running, parked, blocked, closed or cancelled), its start as a short date, how long it lasted or
  open, a bar of its tasks by state, a task no event served yet counted queued, with how many merged, its review
  rounds and its cost, said as a floor. The tasks served by three waves or
  more are named with that count under a heading of their own. On its page,
  a wave opens on one sentence saying how it stands or how it ended, with a resume button while it is halted, its
  milestone and the report of that milestone once one is committed, and five tiles: the tasks merged out of its tasks
  with the parked, its wall time, its run time with its turns and its runs, its cost, marked a floor when a run
  records none, and the time it spent halted with the count and the reasons of its halts. Its tasks are a table: each
  with its state as a pill and a requeue button when parked, its pull request, linked on the forge when `brigade
  project show` names one, its rounds, flagged at three, its runs, each linking its page, and its share of the cost
  of the wave. How it went is a timeline of the states of each task over the time of the wave, its halts drawn as
  bands, followed by the failed tick actions by action, with their count and the event of the ledger that cleared
  them; the events of the ledger are folded under Events.
- **Inbox** — puts first what the user decides: one sentence and four tiles, then Decide first, each proposed pattern
  under its title with what ratifying it starts, how many of the signals it cites are still new, its ratify button
  before its dismiss button, a pattern becoming a constraint offering its kind as a selector before its one ratify
  button, and its repeats folded under it; then the new signals grouped by what recorded them,
  each opening its evidence, a stall whose task merged since marked stale; then the study answers, each opening the
  answer rendered from its entity.
- **awawa** — the corpus of a project at a ref, as the IntelliJ plugin awawa-ui shows it: a banner naming the
  project, the ref and the commit read, offering in a selector the local branches, the main one first, and
  `worktree:<branch>` for each linked worktree; the views Tree, Board, Dependencies and Health as tabs, the entity
  type as a selector, the field the Board is grouped by and the field the Dependencies follow as selectors over the
  fields of the type, each applied as soon as it is chosen, with no button; each entity with its code, its label,
  its facts and the dot of its status; the filters in force as chips with Clear all; and a detail panel, opened by a
  click on an entity, with its fields, the entities it refers to and those referring to it, and the links to the IDE and
  to awawa-web. The view, the type, the field, the filters, the search and the entity shown live in the address alone,
  `#awawa/<project>?view=board&type=TASK&field=STATUS&filter=ROLE=ada`, so an address can be shared; the colours and the
  order of the columns are the defaults. The tab is read-only: its forms only change the address, it offers no Clean,
  no Change Colour and no Arrange Columns, and awawa-web stays the editor. On a project holding no corpus it says so,
  and with the addon stopped it says that the addon stopped, with its error.
- **Ledger** — whether brigade is well tuned. It opens on a callout saying what its measures cover: the runs finished,
  the range of the ledger they were read from and the lines of the ledger skipped. *Do the turn caps fit* sets the
  segment p90 of each role against its applied cap, the role overshooting most first, with a bar marking the cap and
  `estimate` under five measured segments; the table *Turn cap by role* follows it. *What a run takes* gives the p50
  and p90 turns of each procedure, `estimate` under five runs; *What keeps failing* the failed tick actions by day,
  against the 288 ticks of a day, and by action with its most frequent error; *Volume* the counts of the overview as
  tiles, with the waves started by month. A wave opens its turns by role and its halts, and *Compare two periods*
  sets two ranges of days side by side with `brigade ledger compare`, saying when a range under five runs is too
  small to compare.
- **Reports** — the reports of `brigade report list`. The page of a report is ordered by use: its verdict, the
  narrative line opening on Verdict, with its date and its pull request; the tiles of the waves it names, tasks merged,
  runs and turns, cost, wall time with run time and files changed, a cost being a floor when a run records none and a
  statistic the ledger contradicts marked as questioned; Went wrong, Went well and For the next wave, the narrative
  lines opening on those words, case aside, the others following as one list; the tasks and their dependencies as
  tables; Test it by hand and Worth reading in the code, grouped by the task they name; Why a task was held; then
  every other field folded under The full account. A task, a pull request and a run met in a value link their page.
  The list opens on a sentence counting them by kind, a tile each for the
  milestone, task and wave reports, the last saying how many record a wave that merged nothing, and an explainer
  closed on its line saying what a report is. The milestone reports, the task reports and the wave reports,
  folded, follow in three blocks, then the results of the orders when one exists; each row names the subject, the
  project, the verdict, the first narrative of the report or no verdict recorded, the tasks merged out of its
  tasks and the date of the ledger event that recorded it.
- **Runs** — the runs of `brigade run list`: a sentence and an explainer saying what a run and a segment are, tiles
  counting the live runs, the finished ones by outcome and the dead ones, and how many run directories the list
  skipped; the filters, carried by the address, `#runs?state=dead&wave=<wave>` and passed to `--state`, `--wave` and
  `--task`, are chips for the state and selectors for the wave and the task, applied as soon as one is chosen; each row shows the run, its procedure, its task and its wave, linked, its state
  as a pill and its start, the dead runs and the runs a limit cut under headings of their own. The page of a run,
  `#runs/<id>`, opens on where it stands and the last `NEXT` entry of an awawa progress, then five tiles: its
  outcome, its segments with the handovers, its turns against the cap of its role read from
  `brigade ledger budgets --json`, its run time, and its cost with its share of the cost of its wave read from
  `brigade wave show --json --events`; then each segment with its outcome, its turns as a bar against that cap, its
  start, its duration and its cost, the progress cut by segment at each `HANDOVER`, a Markdown progress shown as
  text, the notes handed to the run, the other runs of its task read from `brigade ledger --task --json`, and its
  arguments.

`/views/<route>` serves the HTML fragment of the document `/api/<route>` serves. Three fragments serve the rail:
`/views/heartbeat` renders `brigade scheduler status --json`, answering 200 when the scheduler exits 1 on a stale tick,
`/views/selector` renders the projects of `brigade project list --json`, and `/views/rail` renders the views of
Operate and Understand with their counts from `brigade status --json`, `brigade inbox list --json` and
`brigade report list --json`.

## The awawa addon

`brigade serve` starts the awawa addon, one child process `brigade awawa-addon`, when at least one registered project
holds a corpus: `awawa status --json` of its `PATH` counts files, and a project whose status fails holds none. Where
no project holds one, or no registry exists, it starts none. Stopping `brigade serve` stops it.

- **Its route** — `GET /api/awawa/<project>?ref=<ref>&view=<view>`, with `type`, `field`, `search`, `entity` and
  `filter`, repeatable, answers the document `brigade corpus <project> --ref <ref> --view <view> ... --json` prints. It
  is the one way to the addon, under the Host check of every route: the addon listens on no port and opens no socket
  file; `brigade serve` writes each request as one JSON line on its standard input and reads its answer as one JSON
  line on its standard output.
- **What it caches** — what it read of the corpus of a project at a ref, until a `.awawa` file of the tree read
  changes or the ref names another commit: a second request on an unchanged corpus runs awawa no more. It reads the
  registry once, when it starts.
- **When it stopped** — a project holding no corpus answers 404, `@PROJECT.<project> holds no awawa corpus`, and the
  addon is not asked. An addon that died, that answered nothing within 120 s or that answered no document answers
  503, `the awawa addon stopped; the next request starts it again`; the other views keep being served, and the next
  request of the tab starts it again, the tab waiting while the cache fills. A start that fails, awawa absent for
  one, whether it fails listing the projects holding a corpus or starting the addon, answers 503 with its error,
  `the awawa addon did not start: ...`, and each later request tries one start and no more. An error of the view itself, an unknown ref for one, answers 500 with its message.

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
| `/api/runs?state=<state>`             | `brigade run list`, and `--state`, `--wave`, `--task` of the parameters `state`, `wave`, `task` |
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
