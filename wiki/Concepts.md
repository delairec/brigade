Answers what each word of brigade means, in one line, and which page holds the whole of it: read this page first
when a word of another page is unknown.

| Word | What it is | Page |
|---|---|---|
| operational corpus | the git repository `brigade init` creates in `$XDG_CONFIG_HOME/brigade/`, holding `_schema.awawa` and the entities brigade records: projects, requests, studies | [Install](Install.md) |
| `config.toml` | the machine configuration, beside the operational corpus and never committed | [Install](Install.md) |
| project | a git repository brigade works on, a `PROJECT` entity of `projects.awawa` in the operational corpus, the registry | [Projects](Projects.md) |
| forge | where a project's pull requests live: `github` for a remote on github.com, or `none` | [Projects](Projects.md) |
| `POLICY` | the entity that sets, per project, how brigade acts on it: `WAVE_START`, `SLOTS`, `REVIEW`, `VERIFY_ROUNDS`, `HANDOVERS` | [Tick and scheduler](Tick-and-scheduler.md) |
| `[forge_accounts]` | the table of `config.toml` that binds a forge login to each key: `cli`, `build`, `review`, `remediate` | [Waves](Waves.md) |
| request | what the user wants for one project, in their words, and the plan it receives, a `REQUEST` entity | [Waves](Waves.md) |
| plan | one `MILESTONE` and its tasks, recorded for a request on the branch `plan/<request>` | [Waves](Waves.md) |
| wave | a batch of ratified tasks started together, recorded in the ledger alone, on the branch `integration/<project>_w<n>` | [Waves](Waves.md) |
| task | a `TASK` entity of the project corpus, delivered by a build run on the branch `task/<slug>/<task>` | [Tasks](Tasks.md) |
| preflight | the deterministic checks of the pull request of a task, before any judgment | [Preflight](Preflight.md) |
| verdict | `pass` or `changes`, the judgment of a review run on the pull request of a task, recorded as `task.verdict` | [Verification](Verification.md) |
| finding | one defect a verdict names, graded `critical`, `high`, `medium` or `low`, which a remediation run answers | [Review answers](Review-answers.md) |
| procedure | a Markdown file whose front matter declares `capabilities` and `budget`: what the agent is asked to do | [Runs](Runs.md) |
| slot | what a procedure calls, never a role: `plan`, `build`, `review`, `remediate`, `rebase`, `report`, `triage`, `rules`, `explore` | [Roles](Roles.md) |
| role | a Markdown file, a front matter then the system prompt, that a slot resolves to | [Roles](Roles.md) |
| client adapter | what runs the agents: `claude-code`, `fake`, or an executable `brigade-client-<name>` | [Client adapters](Client-adapters.md) |
| probe | the operation by which an adapter declares its operations, its features and the model of each reasoning level | [Client adapters](Client-adapters.md) |
| run | a procedure run as a slot through the client adapter, kept in `$XDG_STATE_HOME/brigade/runs/<run id>/` | [Runs](Runs.md) |
| segment | one launch of the client within a run; a run cut and resumed is one run of several segments | [Runs](Runs.md) |
| progress file | `progress.awawa` or `progress.md`, what a run hands from one segment to the next | [Runs](Runs.md) |
| tick | one pass that builds a snapshot of the facts, plans the actions they call for and applies them | [Tick and scheduler](Tick-and-scheduler.md) |
| scheduler | what fires `brigade tick --once` every five minutes: `systemd`, `cron` or `loop` | [Tick and scheduler](Tick-and-scheduler.md) |
| ledger | every event brigade records, one JSON line in `$XDG_STATE_HOME/brigade/ledger/<YYYY-MM>.jsonl` | [Ledger](Ledger.md) |
| trail | the JSON lines of the subprocesses one invocation started | [Trails](Trails.md) |
| inbox, signal | the signals brigade records: facts seen by a connector, a note, the answer of a study | [Inbox](Inbox.md) |
| study | deterministic collectors, then at most one judging run, then an output, a `STUDY` entity | [Studies](Studies.md) |
| collector | a step of a study that gathers items without a model: a collector name and its parameters, or `shell: <command line>` | [Studies](Studies.md) |
| dashboard | the local page `brigade serve` serves on `127.0.0.1` | [Dashboard](Dashboard.md) |
