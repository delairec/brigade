What each word of brigade means, in one line, and which page holds the whole of it: read this page first when a word
of another page is unknown.

Each word has one row and one sense. The kind of a row says what the word is: a `command` of `brigade --help`, an
`argument`, an `entity` or a `field` of the registry's schema, or a `concept`. The milestone and the task of a row name
the task of the corpus that delivers the word in that sense. `tests/guards/test_glossary.py` holds the table to the
code and the corpus: every command group and subcommand, every entity and every field of the schema has its row, and a
row names a word the code or the corpus carries.

<!-- glossary: begin -->
| Word | Kind | What it is | Page | Milestone | Task |
|---|---|---|---|---|---|
| registry | concept | the git repository `brigade init` creates in `$XDG_CONFIG_HOME/brigade/`, holding `_schema.awawa` and the entities brigade records, one file per type: projects, requests, studies and their answers, reports, patterns, constraints, orders and their results | [Install](Install.md) | M8 | B255 |
| config.toml | concept | the machine configuration, beside the registry and never committed | [Install](Install.md) | M0 | B03 |
| project | concept | a git repository brigade works on, recorded as a `PROJECT` entity of the registry | [Projects](Projects.md) | M0 | B04 |
| forge | concept | where a project's pull requests live: `github` for a remote on github.com, or `none` | [Projects](Projects.md) | M7 | B46 |
| forge_accounts | concept | the table of `config.toml` that binds a forge login to each slot, and to the key `cli` for the gh calls brigade makes itself | [Waves](Waves.md) | M7 | B108 |
| request | concept | what the user wants for one project, in their words, and the plan it receives | [Waves](Waves.md) | M1 | B187 |
| plan | concept | the `MILESTONE` and the tasks recorded for a request, on the branch `plan/<request>` | [Waves](Waves.md) | M8 | B255 |
| milestone | concept | a `MILESTONE` entity of the project corpus whose tasks merge into the branch `integration/<slug>`, reached when the user merges its pull request into the main branch | [Tick and scheduler](Tick-and-scheduler.md) | M1 | B187 |
| wave | concept | a batch of ratified tasks started together, recorded in the ledger alone, with no branch and no pull request of its own | [Waves](Waves.md) | M1 | B11 |
| task | concept | a `TASK` entity of the project corpus, delivered by a build run on the branch `<prefix>/<id>-<slug>` | [Tasks](Tasks.md) | M1 | B11 |
| corpus | concept | the awawa corpus of a project; the corpus brigade keeps for itself is the registry | [Project tree at a ref](Project-tree-at-a-ref.md) | M8 | B255 |
| command | concept | a command of the CLI, `brigade <group> <subcommand>` | [Command reference](Command-reference.md) | M8 | B255 |
| preflight | concept | a named set of collectors and checks run by `brigade preflight <name>`, before any judgment | [Preflight](Preflight.md) | M8 | B98 |
| check | concept | one deterministic judgment of a preflight, answering a result with its findings; a check run of the forge keeps the forge's sense | [Preflight](Preflight.md) | M8 | B255 |
| result | concept | `ok` or `fail`, what a check of a preflight answers | [Preflight](Preflight.md) | M8 | B255 |
| prerequisite | concept | one item `brigade doctor` inspects on the machine | [Install](Install.md) | M8 | B255 |
| review | concept | the judgment of the pull request of a task, by a review run of brigade or on the forge | [Review](Review.md) | M8 | B255 |
| verdict | concept | `pass` or `changes`, the judgment of a review run, recorded as `task.verdict` | [Review](Review.md) | M8 | B255 |
| finding | concept | one defect a review or a check names, which a remediation run answers | [Review answers](Review-answers.md) | M8 | B255 |
| round | concept | one repair round of a task: a review and the remediation that answers it | [Review answers](Review-answers.md) | M8 | B255 |
| cycle | concept | one pass of the tick over the facts it reads again until nothing changes | [Tick and scheduler](Tick-and-scheduler.md) | M8 | B255 |
| procedure | concept | a Markdown file whose front matter declares `capabilities`: what the agent is asked to do | [Runs](Runs.md) | M1 | B16 |
| slot | concept | what a procedure calls, never a role: `plan`, `build`, `review`, `remediate`, `rebase`, `report`, `triage`, `rules`, `explore` | [Roles](Roles.md) | M0 | B06 |
| role | concept | a Markdown file, a front matter then the system prompt, that a slot resolves to | [Roles](Roles.md) | M0 | B43 |
| client adapter | concept | what runs the agents: `claude-code`, `fake`, or an executable `brigade-client-<name>` | [Client adapters](Client-adapters.md) | M0 | B06 |
| probe | concept | the operation by which an adapter declares its operations, its features and the model of each reasoning level | [Client adapters](Client-adapters.md) | M0 | B49 |
| run | concept | a procedure run as a slot through the client adapter, kept in `$XDG_STATE_HOME/brigade/runs/<run id>/` | [Runs](Runs.md) | M0 | B06 |
| segment | concept | one launch of the client within a run; a run cut and resumed is one run of several segments | [Runs](Runs.md) | F0 | B84 |
| turn | concept | one answer of the agent within a run, what the budgets count | [Runs](Runs.md) | M8 | B255 |
| handover | concept | the passage of a run from one segment to the next through its progress file | [Runs](Runs.md) | M8 | B255 |
| progress file | concept | `progress.awawa` or `progress.md`, what a run hands from one segment to the next | [Runs](Runs.md) | F0 | B71 |
| progress_form | concept | the key of `config.toml` and the plugin kind that set the form of the progress file | [Runs](Runs.md) | M8 | B255 |
| brief | concept | the prompt a run is launched with | [Runs](Runs.md) | M10 | B218 |
| context | concept | what a context command prints for a run: its entity, its neighbours and the rules it falls under | [Tasks](Tasks.md) | M8 | B255 |
| log | concept | the record of what a run printed, kept with the run | [Runs](Runs.md) | M8 | B255 |
| tick | concept | one pass that builds a snapshot of the facts, decides the actions they call for and applies them | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B07 |
| scheduler | concept | what fires `brigade tick --once` every five minutes: `systemd`, `cron` or `loop` | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B07 |
| deferred | concept | an action the tick holds back until the facts it waits for change | [Tick and scheduler](Tick-and-scheduler.md) | M8 | B255 |
| paused | concept | suspended by the user, until the user resumes it | [Waves](Waves.md) | M8 | B255 |
| parked | concept | stopped by brigade on a question that awaits the user | [Waves](Waves.md) | M8 | B255 |
| blocked | concept | waiting on another fact, such as a task it comes after or the quota reset | [Waves](Waves.md) | M8 | B255 |
| stopped | concept | the end of a process or of a run | [Runs](Runs.md) | M8 | B255 |
| ledger | concept | every event brigade records, one JSON line in `$XDG_STATE_HOME/brigade/ledger/<YYYY-MM>.jsonl` | [Ledger](Ledger.md) | M0 | B05 |
| trail | concept | the JSON lines of the subprocesses one invocation started | [Trails](Trails.md) | M6 | B176 |
| trace | concept | one record of a trail: one subprocess, its argv, its exit code and its output | [Trails](Trails.md) | M6 | B176 |
| document | concept | the JSON document a command prints under `--json` | [Command reference](Command-reference.md) | M8 | B255 |
| inbox | concept | where brigade records its signals, listed and dismissed by `brigade inbox` | [Inbox](Inbox.md) | M2 | B22 |
| signal | concept | one fact of the inbox: a fact seen by a connector, a note, the answer of a study | [Inbox](Inbox.md) | M2 | B22 |
| pattern | concept | several signals that are one thing, with their evidence | [Inbox](Inbox.md) | M2 | B25 |
| ratify | concept | accept a pattern and carry out its action, an order among them | [Inbox](Inbox.md) | M8 | B53 |
| study | concept | deterministic collectors, then at most one judging run, then an output, a `STUDY` entity | [Studies](Studies.md) | M1 | B48 |
| collector | concept | a step that gathers items without a model: a collector name and its parameters, or `shell: <command line>` | [Studies](Studies.md) | M5 | B35 |
| collection | concept | the document a collector writes | [Studies](Studies.md) | M8 | B255 |
| recipe | concept | a reusable sequence of steps, its params, its gate, its judge and its output | [Recipes](Recipes.md) | M8 | B50 |
| step | concept | one step of a recipe | [Recipes](Recipes.md) | M8 | B255 |
| order | concept | one instance of a recipe, an `ORDER` entity, placed by the user or by the ratification of a pattern | [Recipes](Recipes.md) | M8 | B51 |
| report | concept | the report of a milestone, a task or a wave | [Studies](Studies.md) | M8 | B255 |
| setup | concept | the commands a worktree of a project runs before any verdict is drawn from it | [Projects](Projects.md) | M8 | B163 |
| dashboard | concept | the local page `brigade serve` serves on `127.0.0.1` | [Dashboard](Dashboard.md) | M3 | B27 |
| `brigade adapter actions` | command | answer actions, the request read on stdin | [Client adapters](Client-adapters.md) | F0 | B79 |
| `brigade adapter launch-argv` | command | answer launch-argv, the request read on stdin | [Client adapters](Client-adapters.md) | F0 | B82 |
| `brigade adapter matrix` | command | print the capabilities every client adapter declares | [Client adapters](Client-adapters.md) | M0 | B49 |
| `brigade adapter parse-result` | command | answer parse-result, the request read on stdin | [Client adapters](Client-adapters.md) | F0 | B82 |
| `brigade adapter probe` | command | answer probe, the request read on stdin | [Client adapters](Client-adapters.md) | F0 | B82 |
| `brigade adapter resume-argv` | command | answer resume-argv, the request read on stdin | [Client adapters](Client-adapters.md) | F0 | B82 |
| `brigade adapter transcripts` | command | answer transcripts, the request read on stdin | [Client adapters](Client-adapters.md) | F0 | B82 |
| `brigade build check` | command | run the acceptance commands and the checks of the corpus in the worktree of a task | [Tasks](Tasks.md) | M8 | B255 |
| `brigade build context` | command | print the starting context of a build run in the worktree of its task | [Tasks](Tasks.md) | M8 | B255 |
| `brigade build pr` | command | push the branch of a checked task and open its pull request on the branch of its wave | [Tasks](Tasks.md) | M8 | B255 |
| `brigade build promote` | command | set a task implemented and delivered by its pull request, then commit and push the promotion | [Tasks](Tasks.md) | M8 | B255 |
| `brigade build push` | command | push the branch of a task whose HEAD passed brigade build check, with a lease | [Tasks](Tasks.md) | M8 | B255 |
| `brigade check list` | command | list every check found, its name and its source | [Preflight](Preflight.md) | M8 | B98 |
| `brigade collector list` | command | list every collector found, its name and its source | [Studies](Studies.md) | M8 | B255 |
| `brigade collector run` | command | run a collector and print the summary and the path of its collection; key=value pairs are its parameters | [Studies](Studies.md) | M8 | B255 |
| `brigade corpus` | command | read a registered project's tree at a branch, a SHA or a worktree; -- <awawa args> runs awawa there | [Project tree at a ref](Project-tree-at-a-ref.md) | M0 | B08 |
| `brigade doctor` | command | inspect the prerequisites and report the optional items with their fallback | [Install](Install.md) | M0 | B02 |
| `brigade inbox dismiss` | command | dismiss a signal, or a pattern with the signals it cites | [Inbox](Inbox.md) | M2 | B22 |
| `brigade inbox list` | command | list the new signals of the inbox, their families, the proposed patterns and the study answers | [Inbox](Inbox.md) | M2 | B22 |
| `brigade inbox ratify` | command | ratify a pattern by its action | [Inbox](Inbox.md) | M8 | B53 |
| `brigade inbox show` | command | print a signal with its evidence, or a study answer rendered from its entity | [Inbox](Inbox.md) | M2 | B22 |
| `brigade init` | command | create the registry repository, its schema and config.toml | [Install](Install.md) | M0 | B03 |
| `brigade ledger` | command | read the event ledger: an overview, a task or a project | [Ledger](Ledger.md) | M0 | B05 |
| `brigade ledger budgets` | command | p50 and p90 turns per procedure over its last runs, and the turn cap of each role | [Ledger](Ledger.md) | M0 | B05 |
| `brigade ledger compare` | command | two ranges of days against each other, or one range against reference figures | [Ledger](Ledger.md) | M0 | B05 |
| `brigade note` | command | record a note in the inbox | [Inbox](Inbox.md) | M2 | B22 |
| `brigade order answer` | command | validate the answer of the judge step of a run of an order against the schema it names and record it | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order cancel` | command | cancel an order, archived and never due again | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order context` | command | print the documents of a run of an order and the schema of the answer its judge step writes | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order list` | command | list every order with its recipe, its project, its schedule and its status | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order new` | command | record an order of a recipe and run it once unless it has a schedule | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order pause` | command | pause an order, which the tick no longer runs | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order resume` | command | resume a paused order, which the tick runs again when due, and relaunch its parked run at its first undone step | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order run` | command | run an order: the steps of its recipe; resume it at its first undone step where it parked | [Recipes](Recipes.md) | M8 | B51 |
| `brigade order show` | command | print one order with its runs | [Recipes](Recipes.md) | M8 | B51 |
| `brigade plan context` | command | print the context a planner reads to plan a request | [Waves](Waves.md) | M1 | B10 |
| `brigade plan record` | command | record the plan of a request, one MILESTONE and its tasks, on plan/<request> and deliver it to the main branch | [Waves](Waves.md) | M1 | B139 |
| `brigade preflight` | command | run the collectors and the checks of a named preflight; key=value pairs are their parameters | [Preflight](Preflight.md) | M8 | B98 |
| `brigade preflight add` | command | add a collector or a check, key=value pairs its parameters, to a custom preflight of the project | [Preflight](Preflight.md) | M8 | B252 |
| `brigade process list` | command | list every run, tick and command that left processes, newest first, with its count of failed ones | [Trails](Trails.md) | M8 | B255 |
| `brigade process show` | command | print the subprocesses a run, a tick or a command started, one line per process | [Trails](Trails.md) | M8 | B255 |
| `brigade project add` | command | register a git repository in the registry | [Projects](Projects.md) | M0 | B04 |
| `brigade project list` | command | list every registered project | [Projects](Projects.md) | M0 | B04 |
| `brigade project pause` | command | pause a project | [Projects](Projects.md) | F0 | B82 |
| `brigade project resume` | command | resume a paused project | [Projects](Projects.md) | F0 | B82 |
| `brigade project show` | command | print the fields of a project | [Projects](Projects.md) | M0 | B04 |
| `brigade rebase context` | command | print in one read the branch of a task, a wave or a milestone, its base and the files in conflict, or the red head a run repairs and the commands that failed on it | [Rebase on the base](Rebase-on-the-base.md) | M1 | B143 |
| `brigade rebase done` | command | check that the branch of the pull request of a task descends from the head of its base, pushing nothing | [Rebase on the base](Rebase-on-the-base.md) | M1 | B143 |
| `brigade rebase pr` | command | push the branch repairing a red main branch and open its pull request into that main branch, as the login of the rebase slot | [Rebase on the base](Rebase-on-the-base.md) | M7 | B238 |
| `brigade recipe lint` | command | check the recipe named against the schema, its names and its params; exits 1 on a finding | [Recipes](Recipes.md) | M8 | B50 |
| `brigade recipe list` | command | list every recipe found, its name and its source, in the order they resolve | [Recipes](Recipes.md) | M8 | B50 |
| `brigade recipe show` | command | print the recipe named, as it resolves, and its source | [Recipes](Recipes.md) | M8 | B50 |
| `brigade remediate context` | command | print in one read the findings the remediation of the pull request of a task answers | [Review answers](Review-answers.md) | M8 | B255 |
| `brigade remediate reply` | command | validate the answers to the findings of the review of the pull request of a task and record them | [Review answers](Review-answers.md) | M8 | B255 |
| `brigade report list` | command | print one row per wave, task and milestone report and per order result | [Studies](Studies.md) | M8 | B255 |
| `brigade report show` | command | print a wave, task or milestone report or an order result, rendered from its entity | [Studies](Studies.md) | M8 | B255 |
| `brigade request cancel` | command | cancel a request planning or planned | [Waves](Waves.md) | M1 | B187 |
| `brigade request list` | command | print one row per request | [Waves](Waves.md) | M1 | B187 |
| `brigade request new` | command | record a request and launch its planning | [Waves](Waves.md) | M1 | B187 |
| `brigade request replan` | command | relaunch the planner of a planning request whose planner run is no longer live | [Waves](Waves.md) | M1 | B169 |
| `brigade request show` | command | print a request, its status, its plan and its pull request | [Waves](Waves.md) | M1 | B187 |
| `brigade review context` | command | print in one read what the review of the pull request of a task judges | [Review](Review.md) | M8 | B255 |
| `brigade review verdict` | command | validate the verdict of the review of the pull request of a task and record it | [Review](Review.md) | M8 | B255 |
| `brigade role lint` | command | check the built-in and the machine role files | [Roles](Roles.md) | M8 | B255 |
| `brigade role list` | command | list the role, the source and the model of each slot | [Roles](Roles.md) | M8 | B255 |
| `brigade role show` | command | print the role file a slot resolves to | [Roles](Roles.md) | M8 | B255 |
| `brigade run list` | command | list every run with its state and outcome | [Runs](Runs.md) | M8 | B255 |
| `brigade run note` | command | hand a note to a run: the brief of its next segment carries it | [Runs](Runs.md) | M13 | B91 |
| `brigade run prune` | command | remove the finished and dead runs beyond the bound, or older than a day; a running run stays | [Runs](Runs.md) | M8 | B255 |
| `brigade run show` | command | print the summary of a run, its segments, its notes and its progress, and with --log its log | [Runs](Runs.md) | M8 | B255 |
| `brigade run start` | command | run a procedure as a slot through the client adapter | [Runs](Runs.md) | M8 | B255 |
| `brigade run stop` | command | stop a run: its client's group gets SIGTERM, then SIGKILL after the grace | [Runs](Runs.md) | M8 | B255 |
| `brigade run stop-hook` | command | print the document that stops a client session once the soft limit of its run has passed | [Runs](Runs.md) | M8 | B255 |
| `brigade scheduler install` | command | install the scheduler config.toml names, or the default | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B07 |
| `brigade scheduler status` | command | report the scheduler installed, whether its tick is stale, the parked and blocked waves and the parked tasks | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B07 |
| `brigade serve` | command | serve the dashboard on the loopback address until SIGINT or SIGTERM | [Dashboard](Dashboard.md) | M3 | B27 |
| `brigade status` | command | print the Home document: the projects, the open waves, the inbox and the scans holding new signals, the quota, the last tick and the studies | [Dashboard](Dashboard.md) | M3 | B28 |
| `brigade study answer` | command | validate the answer of a judging run against the schema of its type and record it | [Studies](Studies.md) | M1 | B48 |
| `brigade study context` | command | print the context a judging run answers from, and write it to the run directory | [Studies](Studies.md) | M1 | B48 |
| `brigade study list` | command | list every study with its schedule, its last run and its outcome | [Studies](Studies.md) | M1 | B147 |
| `brigade study new` | command | record a study and run it once unless it has a schedule | [Studies](Studies.md) | M1 | B48 |
| `brigade study pause` | command | pause a study, which the tick no longer runs | [Studies](Studies.md) | M1 | B147 |
| `brigade study resume` | command | resume a paused study | [Studies](Studies.md) | M1 | B147 |
| `brigade study run` | command | run a study: its collectors, its judging run, its output; resume it where it parked | [Studies](Studies.md) | M1 | B48 |
| `brigade study show` | command | print the fields of a study, its last run and its outcome | [Studies](Studies.md) | M1 | B147 |
| `brigade tick` | command | decide and apply what the facts call for, once or in a loop | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B07 |
| `brigade wave cancel` | command | cancel an open wave: stop the live runs of its tasks and list what stays in place | [Waves](Waves.md) | M1 | B187 |
| `brigade wave list` | command | print one row per wave of the ledger, the open waves first | [Waves](Waves.md) | M1 | B11 |
| `brigade wave requeue` | command | queue again a parked task of the wave named, for the next tick to launch it | [Waves](Waves.md) | M1 | B168 |
| `brigade wave resume` | command | resume the wave named, or every wave parked on the forge account | [Waves](Waves.md) | M1 | B19 |
| `brigade wave show` | command | print a wave and each of its tasks with its state, its pull request and its run | [Waves](Waves.md) | M1 | B11 |
| `brigade wave start` | command | compose a wave of the project's startable tasks per milestone and start each on the branch of its milestone | [Waves](Waves.md) | M1 | B11 |
| `DESC` | field | a line of prose describing an entity, legal on every entity of the registry | [Install](Install.md) | M0 | B03 |
| `RATIONALE` | field | why an entity is as it is, legal on every entity of the registry | [Install](Install.md) | M0 | B03 |
| `PROJECT` | entity | a registered repository on this machine | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.PATH` | field | the path of the repository on this machine | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.REMOTE` | field | the URL of its origin | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.MAIN` | field | its main branch | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.CORPUS` | field | the corpus folder, relative to PATH, the anchors resolve from: corpus/ when brigade creates it, else the root project add discovered | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.MODE` | field | how brigade uses the corpus of the repository: control, every file of it; area, the folder CORPUS names alone, read as the awawa workspace; none, not delivered yet | [Projects](Projects.md) | M7 | B140 |
| `PROJECT.SLOTS` | field | the build runs the project holds at once, 4 by default | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.MERGE` | field | how a pull request of the project is merged: squash, rebase or merge | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.CLIENT` | field | the client adapter of this project's runs; config.toml's default when absent | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.ROLESET` | field | builtin, corpus, or a directory of role files; the resolution order when absent | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.ROLE` | field | slot=role, an override of the binding, e.g. remediate=builder | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.PRIVATE` | field | a regular expression the privacy scan and the scrubber refuse, e.g. stn_[0-9a-f]{12} | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.PUBLIC` | field | a regular expression the privacy scan lets through where it matches the whole of what a pattern found, e.g. alice@example\\.org for an example value a test uses | [Projects](Projects.md) | M1 | B15 |
| `PROJECT.FORGE` | field | github or none | [Projects](Projects.md) | M0 | B03 |
| `PROJECT.CHECK_RUNS` | field | whether the tick waits for a first check run of a pull request before its preflight; none for a project without continuous integration | [Projects](Projects.md) | M1 | B15 |
| `PROJECT.STATUS` | field | active, or paused by `brigade project pause` | [Projects](Projects.md) | M0 | B03 |
| `POLICY` | entity | how far a project's waves run on their own | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B03 |
| `POLICY.PROJECT` | field | the project the policy governs | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B03 |
| `POLICY.PLAN_REVIEW` | field | whether the plan of a request waits for the user, `ask`, or is ratified by brigade, `auto` | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B03 |
| `POLICY.WAVE_START` | field | whether a wave waits for `brigade wave start`, `ask`, or starts on its own, `auto` | [Tick and scheduler](Tick-and-scheduler.md) | M1 | B187 |
| `POLICY.REVIEW` | field | what a pull request needs before its merge: the approval of the forge, `approval`, or the verdict `pass` of a review run, `verdict` | [Tick and scheduler](Tick-and-scheduler.md) | M1 | B99 |
| `POLICY.REPAIR_ROUNDS` | field | the repair rounds a task gets before it is parked, 2 by default | [Tick and scheduler](Tick-and-scheduler.md) | M8 | B255 |
| `POLICY.HANDOVERS` | field | the handovers a run gets before its task is parked, 2 by default | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B03 |
| `POLICY.AUTO_MERGE` | field | whether the tick merges a verified pull request into the branch of its milestone, `integration`, or leaves it to the user, `none` | [Tick and scheduler](Tick-and-scheduler.md) | M0 | B03 |
| `STUDY` | entity | a question answered by evidence: collectors, then at most one judging run; with no slot, a scan | [Studies](Studies.md) | M0 | B03 |
| `STUDY.TITLE` | field | the study in one line | [Studies](Studies.md) | M0 | B03 |
| `STUDY.QUESTION` | field | the user's words, verbatim; absent for a scan | [Studies](Studies.md) | M0 | B03 |
| `STUDY.PROJECT` | field | absent for a machine-wide study | [Studies](Studies.md) | M0 | B03 |
| `STUDY.COLLECTOR` | field | a collector name with its parameters, e.g. git-log since=30d, or shell: <command>, one argv split by shlex.split and run without a shell | [Studies](Studies.md) | M0 | B03 |
| `STUDY.SLOT` | field | the judging slot; none makes the study a scan | [Studies](Studies.md) | M0 | B03 |
| `STUDY.EVERY` | field | a brigade schedule evaluated by the tick: 5m, 1h, daily@09:00, mon@09:00; absent means on demand | [Studies](Studies.md) | M0 | B03 |
| `STUDY.OUTPUT` | field | file:<path pattern>, entity:<TYPE>, issue, inbox, or an output on PATH | [Studies](Studies.md) | M0 | B03 |
| `STUDY.ANSWER` | field | the entity type of this schema the answer is written as | [Studies](Studies.md) | M1 | B48 |
| `STUDY.STATUS` | field | active, paused or archived | [Studies](Studies.md) | M0 | B03 |
| `ANSWER` | entity | the answer of one run of a study: the CLI fills what the collectors gave, the judging slot the prose | [Studies](Studies.md) | M1 | B48 |
| `ANSWER.STUDY` | field | the name of the STUDY answered | [Studies](Studies.md) | M1 | B48 |
| `ANSWER.RUN` | field | the run of the study | [Studies](Studies.md) | M1 | B48 |
| `ANSWER.COLLECTED` | field | one per collector, its name, filled by the CLI | [Studies](Studies.md) | M1 | B48 |
| `ANSWER.COLLECTED.SUMMARY` | field | the summary of its collection, as JSON | [Studies](Studies.md) | M1 | B48 |
| `ANSWER.COLLECTED.COLLECTION` | field | the path of its collection | [Studies](Studies.md) | M8 | B255 |
| `ANSWER.NARRATIVE` | field | the prose of the answer, filled by the judging slot | [Studies](Studies.md) | M1 | B48 |
| `ANSWER.FINDING` | field | one finding with its evidence, filled by the judging slot | [Studies](Studies.md) | M1 | B48 |
| `REPORT` | entity | the answer of the built-in studies milestone-report and task-report: the CLI fills what the collectors gave, the report slot the prose; a report written before them names a wave | [Studies](Studies.md) | M1 | B20 |
| `REPORT.MILESTONE` | field | the milestone reported, M<n> | [Studies](Studies.md) | M6 | B232 |
| `REPORT.TASK` | field | the task reported, naming no milestone | [Studies](Studies.md) | M6 | B232 |
| `REPORT.WAVE` | field | the wave reported, <project>_w<n>, by a report written before the report of a milestone | [Studies](Studies.md) | M1 | B20 |
| `REPORT.PROJECT` | field | the project reported | [Studies](Studies.md) | M1 | B20 |
| `REPORT.TASK_ROW` | field | one task reported, its last state and its pull request, filled by the CLI | [Studies](Studies.md) | M1 | B20 |
| `REPORT.STATISTIC` | field | one figure of the wave, its name then its value, filled by the CLI | [Studies](Studies.md) | M1 | B20 |
| `REPORT.GRAPH` | field | one dependency between two tasks of the wave, filled by the CLI | [Studies](Studies.md) | M1 | B20 |
| `REPORT.MANUAL_TEST` | field | one SPEC line of a merged task, to test by hand, filled by the CLI | [Studies](Studies.md) | M1 | B20 |
| `REPORT.INSTRUCTIONS_CHANGE` | field | one file of the project's corpus the wave changed, filled by the CLI | [Studies](Studies.md) | M1 | B20 |
| `REPORT.PARKED_QUESTION` | field | one parked task and what it waits for, filled by the CLI | [Studies](Studies.md) | M1 | B20 |
| `REPORT.PATTERN_TASK` | field | one task whose request comes from a pattern, its constraint and its reason, filled by the CLI | [Studies](Studies.md) | M2 | B25 |
| `REPORT.NARRATIVE` | field | the prose of the report, filled by the report slot | [Studies](Studies.md) | M1 | B20 |
| `REPORT.REASON` | field | why a task was parked or failed, filled by the report slot | [Studies](Studies.md) | M1 | B20 |
| `REPORT.TESTER_STEP` | field | one manual test in a tester's words, filled by the report slot | [Studies](Studies.md) | M1 | B20 |
| `REPORT.SAMPLING` | field | one change worth reading by sampling, filled by the report slot | [Studies](Studies.md) | M1 | B20 |
| `ORDER` | entity | one instance of a recipe: its parameters, its project, its schedule | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.RECIPE` | field | the recipe the order is an instance of | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.PROJECT` | field | absent for a machine-wide order | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.TEXT` | field | the user's words, verbatim, when the recipe takes them | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.PARAM` | field | key=value | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.EVERY` | field | a brigade schedule evaluated by the tick; absent means on demand | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.OUTPUT` | field | an override of the recipe's output | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.STATUS` | field | active, paused or archived | [Recipes](Recipes.md) | M0 | B03 |
| `ORDER.FROM` | field | the pattern whose ratification placed the order | [Recipes](Recipes.md) | M8 | B53 |
| `RESULT` | entity | the answer of one run of an order: the CLI fills what the collectors gave, the judging slot the prose | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.ORDER` | field | the name of the ORDER answered | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.RUN` | field | the run of the order | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.COLLECTED` | field | one per collector, its name, filled by the CLI | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.COLLECTED.SUMMARY` | field | the summary of its collection, as JSON | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.COLLECTED.COLLECTION` | field | the path of its collection | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.NARRATIVE` | field | the prose of the result, filled by the judging slot | [Recipes](Recipes.md) | M8 | B51 |
| `RESULT.FINDING` | field | one finding with its evidence, filled by the judging slot | [Recipes](Recipes.md) | M8 | B51 |
| `REQUEST` | entity | what the user wants for one project, in their words, and the plan it receives | [Waves](Waves.md) | M0 | B03 |
| `REQUEST.PROJECT` | field | the project the request is for | [Waves](Waves.md) | M0 | B03 |
| `REQUEST.TEXT` | field | the user's words, verbatim | [Waves](Waves.md) | M0 | B03 |
| `REQUEST.CREATED_AT` | field | the UTC instant the request was recorded, YYYY-MM-DDTHH:MM:SSZ | [Waves](Waves.md) | M1 | B11 |
| `REQUEST.STATUS` | field | planning, planned or cancelled | [Waves](Waves.md) | M0 | B03 |
| `REQUEST.MILESTONE` | field | the milestone of the plan the request received | [Waves](Waves.md) | M1 | B139 |
| `REQUEST.PR` | field | the pull request of its plan | [Waves](Waves.md) | M1 | B187 |
| `REQUEST.FROM` | field | the pattern whose ratification placed the request | [Waves](Waves.md) | M0 | B03 |
| `PATTERN` | entity | several signals that are one thing, with their evidence | [Inbox](Inbox.md) | M0 | B03 |
| `PATTERN.TITLE` | field | what the signals of the pattern have in common, in one line | [Inbox](Inbox.md) | M0 | B03 |
| `PATTERN.STATUS` | field | new, ratified, dismissed or delivered | [Inbox](Inbox.md) | M0 | B03 |
| `PATTERN.EVIDENCE` | field | one signal of the pattern, by its fingerprint | [Inbox](Inbox.md) | M0 | B03 |
| `PATTERN.ACTION` | field | what its ratification does: a wave, a constraint, an order, or dismiss | [Inbox](Inbox.md) | M0 | B03 |
| `PATTERN.RECIPE` | field | the recipe an order action places | [Inbox](Inbox.md) | M0 | B03 |
| `PATTERN.TARGET` | field | where the action of the pattern lands | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT` | entity | what a ratified pattern becomes: a rule, a guard, a lint, a schema change, a skill or a script | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT.TITLE` | field | the constraint in one line | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT.KIND` | field | rule, guard, lint, schema, skill or script | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT.FROM` | field | the pattern the constraint comes from | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT.TARGET` | field | the file the constraint is delivered into | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT.STATUS` | field | proposed, delivered or rejected | [Inbox](Inbox.md) | M0 | B03 |
| `CONSTRAINT.DELIVERED_BY` | field | the pull request that delivers it | [Inbox](Inbox.md) | M0 | B03 |
<!-- glossary: end -->
