Every command of brigade, what it does in one line, and the page that documents it. The lines come from
`brigade --help` and `brigade <command> --help`, with the departures listed at the end of the page.

- Every command accepts `--json`, which prints the output as a JSON document, and `--verbose`, which prints every
  subprocess the command runs on stderr ([Trails](Trails.md)).
- `brigade --version` prints the version of brigade.
- A command this page does not list is a task of the corpus, not delivered yet.

## Setting up

| Command | What it does | Page |
|---|---|---|
| `brigade doctor` | check the prerequisites and report the optional items with their fallback | [Install](Install.md) |
| `brigade init` | create the operational corpus repository, its schema and `config.toml` | [Install](Install.md) |
| `brigade project add\|list\|show\|pause\|resume` | register the projects brigade works on, list and show them | [Projects](Projects.md) |
| `brigade adapter <operation>` | answer one operation of the configured client adapter: `probe`, `launch-argv`, `parse-result`, `resume-argv`, `transcripts`, `actions` | [Client adapters](Client-adapters.md) |
| `brigade adapter matrix` | print the capabilities every client adapter declares | [Client adapters](Client-adapters.md) |
| `brigade roles list\|show\|lint` | list, show and lint the roles each slot resolves to | [Roles](Roles.md) |
| `brigade scheduler install\|status` | install what fires the tick, and report it | [Tick and scheduler](Tick-and-scheduler.md) |

## Running work

| Command | What it does | Page |
|---|---|---|
| `brigade request new\|show\|list\|cancel` | record the requests of the projects, list, show and cancel them | [Waves](Waves.md) |
| `brigade request replan` | relaunch the planner of a planning request whose planner run is no longer live | — |
| `brigade plan record` | record the plan of a request, one `MILESTONE` and its tasks, on `plan/<request>` and deliver it to the main branch | [Waves](Waves.md) |
| `brigade plan context` | print the package a planner reads to cut a request into a wave | — |
| `brigade wave start\|show\|list\|cancel\|resume\|requeue` | start the waves of the projects, list, show and cancel them | [Waves](Waves.md) |
| `brigade task context\|check\|pr\|promote` | work on a task of a wave from its worktree | [Tasks](Tasks.md) |
| `brigade verify preflight` | run the deterministic checks of a pull request of a task before any judgment | [Preflight](Preflight.md) |
| `brigade verify context\|verdict` | print what the verification of the pull request of a task judges, and record its verdict | [Verification](Verification.md) |
| `brigade review context\|reply` | answer the review of the pull request of a task | [Review answers](Review-answers.md) |
| `brigade rebase context\|done` | put the pull request of a task back on its base | [Rebase on the base](Rebase-on-the-base.md) |
| `brigade run <procedure>` | run a procedure as a slot through the client adapter | [Runs](Runs.md) |
| `brigade runs list\|show\|stop\|prune` | list the runs, show one, stop one and prune them | [Runs](Runs.md) |
| `brigade tick --once\|--dry-run\|--loop` | plan and apply what the facts call for, once or in a loop | [Tick and scheduler](Tick-and-scheduler.md) |
| `brigade study new\|run\|context\|answer\|list\|show\|pause\|resume` | record the studies, run them, print their context and take their answers | [Studies](Studies.md) |
| `brigade collect <name>` | run a collector and print the summary and the path of its document; `key=value` pairs are its parameters | [Studies](Studies.md) |
| `brigade collectors list` | list every collector found, its name and its source | [Studies](Studies.md) |

## Observing

| Command | What it does | Page |
|---|---|---|
| `brigade status` | print the Home document: the projects, the open waves, the inbox, the quota, the last tick and the studies | — |
| `brigade note <text>` | record a note in the inbox | [Inbox](Inbox.md) |
| `brigade inbox list\|show\|dismiss` | list, show and dismiss the signals of the inbox | [Inbox](Inbox.md) |
| `brigade inbox ratify` | ratify a pattern by its action | [Dashboard](Dashboard.md) |
| `brigade reports list\|show` | print one row per wave report and study answer, or one of them rendered from its entity | — |
| `brigade ledger [budgets\|compare]` | read the event journal: an overview, a wave or a project | [Ledger](Ledger.md) |
| `brigade processes list\|show` | list the subprocesses brigade started and show those of one run, tick or command | [Trails](Trails.md) |
| `brigade corpus <project>` | read a registered project's tree at a branch, a SHA or a worktree; `-- <awawa args>` runs awawa there | [Project tree at a ref](Project-tree-at-a-ref.md) |
| `brigade serve` | serve the dashboard on the loopback address until SIGINT or SIGTERM | [Dashboard](Dashboard.md) |

<details><summary>Lines that depart from the help</summary>

- `brigade adapter <operation>`: the line names the six operations in place of the help line of `brigade adapter`,
  which covers `matrix` too.
- `brigade verify context|verdict` and `brigade reports list|show`: each line joins the help lines of its two
  subcommands, `verify context` and `verify verdict`, `reports list` and `reports show`.
- `brigade reports`: `brigade --help` prints an empty line for it; its line comes from its two subcommands.

</details>
