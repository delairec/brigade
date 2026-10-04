# HANDOFF — agent-factory plan (Max, phase 1 done: 2026-10-04)

A successor run continues from this file alone. Work directory (the only writable place):
`/tmp/claude-1000/-home-chillie-Web-planet-crafter-save-tools/3ea43d20-be60-4532-a87e-b0c6822f8f69/scratchpad/agent-factory-plan/`

## 1. The brief and its confirmed scope

- Deliverable: one published Artifact (multi-page allowed), in English, holding (a) a spec-like detailed plan for a
  CLI/environment that "industrialises" the user's use of AI agents, inspired by the podcast transcript (software
  factory, trust ladder); (b) visual mockups (terminal output, tool screens) and diagrams (inline SVG); (c) a task page
  whose statuses can be changed and persist — `db` capability of the Artifact runtime (load `artifact-capabilities`
  skill), never localStorage; (d) optionally a light demo page.
- Confirmed by the coordinator (relaying the user) on 2026-10-04: **the factory is a NEW, standalone project, applying
  machine-wide across all the user's projects; planet-crafter-save-tools is only an example of current practice.
  Artifact language: English.** Do not ask about either point.
- The user wants questions before any design (phase 1, done: see §6). Phase 2 = design, write, publish, after the
  answers arrive by SendMessage from the coordinator.
- Constraints on this run: change nothing outside the work directory; no repository edit, no commit; `.awawa` files are
  read only through `awawa` commands; publishing the Artifact is allowed.
- Context discipline: rewrite this file at each phase end or when context grows heavy.

## 2. Inputs in the work directory

- `transcript-plain.txt` (67 872 bytes, 621 timestamped lines): podcast, host + guest "potato" (ex-Meta React, now
  Cursor/"SpaceX AI"; skill library "PAC"/"Pstack"; 2 500 PRs/month). Read in full by phase 1.
- `chatgpt-summary-raw.txt` (36 660 bytes): a React Router loader JSON stream. The useful markdown was extracted by
  phase 1 into **`chatgpt-summary.md`** (11 824 chars) — read that instead.
- `HANDOFF.md`: this file.

### Key ideas of the transcript, with timestamps (for citations in the Artifact)

| Idea | Where |
|---|---|
| Trust ladder: micromanaging one agent → environment + verification → many agents → agents merge their own code | 1:36–2:00, 26:14–27:55, 39:35–39:51 |
| Verification is the single most important skill: "hands and eyes", the loop exists only because of it; hill climbing | 15:54–18:49 |
| Deterministic parts extracted into a CLI inside the skill; agents keep only judgment; agents "rebuilt the world each time" | 19:35–23:35 |
| Codemods / AST transforms for migrations | 24:19–24:50 |
| Mistakes → lint rules / structure that makes them impossible; "Dune" framework, feature directories, god files | 25:00–32:56 |
| Inner loop (agents on code) vs outer loop (Slack, Linear, X, email, bug reports); the human as proxy; connect the two | 34:56–37:49, 40:52–44:11 |
| Coordinator ("chief of staff", Cursor "projects"): delegates, chooses topology, keeps the thread between related bugs | 39:10–39:35, 42:47–45:28 |
| Routines: an agent appends findings to a document instead of fixing; the buffer forces seeing the pattern | 47:03–49:04 |
| Sampling instead of blocking review; fix the environment, not the agent; "step away" | 49:15–51:19 |
| Dark factory: review after landing from the commit history; verifier agents fuzz the app; token-intensive, tunable | 51:43–54:44 |
| One-way vs two-way doors; verifiability of the domain decides the autonomy | 55:40–59:26 |
| Skills = processes in language; mine your own transcripts for interventions → skills → lint rules; "recall" skill | 1:00:35–1:04:44 |

## 3. What exists on the machine (verified by command in phase 1)

Machine: Debian 13, kernel 6.12, zsh, Bun 1.4.2, Node 24.19, Python 3.13.5, gh 2.100, jq, fzf; **no** tmux, zellij,
docker, podman, gum. Claude Code 2.1.289 (`claude --version`). IntelliJ MCP (`mcp__idea__*`) and Claude Docs MCP
present. Only one machine seen; the worktree-cleanup timer unit says "the machine is off on a Monday morning".

### `~/.ai` — the instructions corpus (awawa 2.7)
- `awawa status ~/.ai`: 268 entities — RULE 171, TRIGGER 27, AREA 21, PROCEDURE 15, SCHEMA 10, AGENT 7, SHAPE 7,
  PACKAGE_KIND 6, CHECKLIST 2, SESSION 1, OPEN_QUESTION 1; 655 references, 0 unresolved; 0 diagnostics.
- Roles (`awawa status AGENT ~/.ai`): bastien (builds), dora (explores), lex (writes rules), manu (manual ops),
  max (analysis/arbitration, REASONING deepest, launch needs user permission), prudence (verifies), remi (review
  answers). Bound by `~/.ai/adapters/claude/agents/<name>.md` (front matter: model, effort, maxTurns = BUDGET + 25 %).
  `charlie.md` = main session agent, no body, carries the hooks.
- Hooks (`~/.ai/adapters/claude/hooks/`): `build_context_part.py` (SessionStart/SubagentStart → `awawa context`
  package cut into ≤9 000-char parts injected as `additionalContext`), `decide_launch_permission.py` (PreToolUse on
  Agent → `ask` for a deepest-reasoning role), `run_awawa.py`; each has a `_spec.py` (16 tests).
- Unattended runner: `~/.ai/bin/ai-run <procedure.md> [args]` → `adapters/claude.sh` → `claude -p "<prompt>"
  --output-format text --allowedTools <from capabilities> --add-dir <state dir>`. Procedures declare
  `capabilities:` (read, write, shell, net) and `budget:` in front matter. Progress file
  `${XDG_STATE_HOME:-~/.local/state}/ai/<procedure>-<args>.md` (≈200 files exist there today: wave starts, PR reviews,
  task refinements, tasks, usage reports, worktree cleanups).
- `~/.ai/bin/ai-turns`: steps per procedure run from transcripts, via `adapters/claude-steps.py` (the only
  transcript reader).
- Procedures (portable, `~/.ai/procedures/`): awawa-task.md (budget 75), awawa-pr-review-round.md, rebase-on-base.md,
  worktree-cleanup.md. Claude-only commands (`~/.ai/adapters/claude/commands/`): awawa-plan-wave-start (budget 90,
  launches `bastien` runs with `isolation: "worktree"`, one PR per task, monitors, relays rulings), awawa-pr-review,
  awawa-refine-task, awawa-usage-report, gh-bot-access, update-check, worktree-*.
- Scheduler: `~/.config/systemd/user/worktree-cleanup.timer` (Mon 09:00, Persistent=true) → service running
  `ai-run worktree-cleanup.md` per repo found under `$HOME` (maxdepth 3). Log: `~/.local/state/ai/worktree-cleanup.log`.
- Rules that constrain any factory design (read with `awawa show @RULE.<name> ~/.ai`):
  `work_handed_to_role_of_its_nature` (what a session keeps vs hands over; 4 parallel runs default; a role of deepest
  reasoning needs permission; delivered work never verified by its producer), `brief_carries_what_the_role_lacks`,
  `long_run_hands_over` (50 steps), `session_hands_over_at_fifty_answers`, `procedure_step_budget` (p90, never
  median), `unattended_procedure_never_assumes`, `instructions_are_agent_agnostic` (nothing CLI-specific in rules;
  adapters hold it), `procedure_names_capabilities`, `tool_introduction_is_the_users_call` (a new build system,
  linter, framework needs the user's agreement), `worktrees_cleaned_unattended`, `heavy_tests_not_run_locally`
  (browser suites and whole-repo analyses run in CI only), `decisions_recorded`, `repository_facts_proven_by_command`,
  `main_worktree`. `RULE.ENFORCED_BY` names the mechanism enforcing a rule (hook, guard, script) — a measurable
  "rules with teeth" ratio.
- Open question of the corpus: `@OPEN_QUESTION.decision_shape_belongs_where`.
- `~/.ai/README.md`: fresh-install steps (clone, awawa ≥ 2.7 on PATH, symlinks `~/.claude/CLAUDE.md`, `commands`,
  `agents`, `"agent": "charlie"` in settings). Skills under `~/.claude/skills/` are not versioned.

### awawa
- `awawa --help` prints the session loop (status → context/lint --closure → show/refs → record → fmt/lint → verify).
  Commands: status (--where), fmt (--check, --rename), lint (--strict, --closure, --rule, --summary), show, refs,
  context (--depth, --skip, --with-schema), new, diff, infer; `--json` everywhere; `--overlay FILE -`.
- **`awawa-web` is installed** (`~/.local/bin/awawa-web`): local structured viewer/editor of a corpus on 127.0.0.1,
  backed only by `awawa --json`; writes are block edits + fmt + lint, 409 on stale (manual §12,
  `~/Web/awawa/manual.md:1695`). `~/Web/awawa/agent-protocol.md` (25 KB) and `manual.md` (102 KB) are the docs.
- awawa computes nothing: "the format describes; where a value seems to need logic, the answer is prose plus an
  anchor into the code". No write command but fmt.

### planet-crafter-save-tools (the example of current practice)
- Corpus in `docs/` (433 entities): TASK 60 (21 draft, 4 todo, 35 implemented), DECISION 181, RULE 37, PROCESS 16,
  WAVE 5, USAGE_REPORT 7, OPEN_QUESTION 1. TASK schema: TITLE, STATUS draft|todo|implemented|archived, SPEC+IMPL
  anchors, AFTER/BEFORE, WAVE, DELIVERED_BY (PR number), PRIORITY.
- Guards: `bun run guards` runs 20 `check:*` scripts (architecture, tests, repository) + `validate:tables`; CI
  requires 100 % line coverage per module; fallow audit/health in CI; `bun run audit`.
- 14 linked worktrees under `.claude/worktrees/` (agent-*, feat-189, refine-refactor194), many locked.
- GitHub: `delairec/planet-crafter-save-tools`, public, issues enabled but 1 issue ever (closed, 2026-03); PRs:
  #266 integration → master, #285 open. Last 8 merged PRs: reviews by `delairec` (6 of 8) and `Clauche-bot`;
  comments by `claude` (GitHub app) and `Clauche-bot`. gh accounts: Clauche-bot (bot, active via wrapper), delairec.
- Memory notes (`~/.claude/projects/-home-chillie-Web-planet-crafter-save-tools/memory/`): isolation guard blocks
  worktree reuse from an isolated session; subagents denied corpus edits (parent amends by script); scratchpad shared
  between parallel agents; `bun install` per worktree; never `cd` into the satellite; cherry-pick/patch integration
  from an isolated session; screenshot flow for UI review; machete stack: rebase never merge.
- `docs/NOTES-roles-agents.md` (untracked, 2026-10-03): the roles' rationale and measurements — 119 sessions, 217
  agent launches (26/09–03/10); 46/86 task agents loaded a trigger before hooks; 146 steps spent re-reading oversized
  command outputs; **959 $/week at public rates (44 % cache writes, 38 % cache reads, 18 % output)**; alternatives
  rejected (bare awawa command as hook: 10 000-char cap; slash command: 30 000-char Bash cap; generated agent files:
  merge conflicts).
- Transcripts on the machine (`~/.claude/projects/`): planet-crafter 420 sessions / 735 MB; `~/.ai` 12 + 13
  (migration worktree); awawa IntelliJ UI 12; home 24; many worktree-scoped dirs.
- Local tools: `~/.claude/tools/context-web/` (Python stdlib HTTP server + one HTML template, loopback, polls the
  clone every 5 s, writes files, commits/pushes — precedent for a local dashboard), `~/.claude/tools/awawa-usage-report/
  collect.py` + `measure.py` (collects transcripts, PR review threads via GraphQL, corpus diffs).
- `~/Web/claude-snapshot-reports`: empty repo (one commit). Other repos under `~/Web`: hearthstone-assistant, awawa,
  awawa-firefox, awawa-intellij-plugin.

### Claude Code 2.1.289 capabilities relevant to the design (`claude --help`)
`-p/--print` with `--output-format json|stream-json`, `--json-schema`, `--max-budget-usd`, `--max-turns` (via
agents), `--permission-mode acceptEdits|auto|bypassPermissions|manual|dontAsk|plan`, `--permission-prompts host|none`,
`--allowedTools/--disallowedTools/--tools`, `--agent <name>`, `--agents <json>`, `--append-system-prompt`,
`--add-dir`, `--mcp-config`, `--worktree/-w`, `--bg` background sessions + `claude agents --json`, `attach`, `logs`,
`stop`, `rm`, `respawn`; `--resume`, `--session-id`, `--fork-session`; `--cloud`; `--bare`, `--restricted`;
`ultrareview`; `--include-hook-events`. Hooks: SessionStart, SubagentStart, PreToolUse, (PostToolUse, Stop,
SubagentStop, Notification, UserPromptSubmit, PreCompact exist in the harness). Skills `schedule` (cloud routines on
cron) and `loop` (local recurring prompt) are available in the session.

## 4. Gap analysis: the video vs the machine (phase 1 conclusion)

| Video mechanism | On the machine today | Gap |
|---|---|---|
| Verification: agents with hands and eyes | unit tests, 20 guards, CI (coverage, Playwright, fallow), prudence role, UI screenshot flow | no reusable "verify this PR" procedure with a deterministic CLI; UI runs are CI-only (laptop) |
| Deterministic parts extracted into CLIs | awawa (context/rules), guards, `ai-run`, hooks, `rebase-on-base` procedure (run by a model) | no codemods; several mechanical ops still run by models (rebase, corpus promotion edits, PR body, worktree setup) |
| Mistake → constraint | awawa lint/schema; guards; `RULE.ENFORCED_BY` | no systematic mining of transcripts/review threads into rule/guard proposals; usage reports are per PR, manual |
| Codebase as prompt | layered packages, `check:dependencies`, triggers per layer | n/a for the factory itself; the factory must carry its own constraints |
| Outer loop → inner loop | none: the user relays issues, review comments, CI failures, audit results | intake connectors absent |
| Coordinator | `/awawa-plan-wave-start` (Claude command, per wave, launched by hand), charlie as main session | no unattended coordinator, no cross-project view, no topology choice |
| Buffer / triage with pattern analysis | OPEN_QUESTION, draft TASK, memory notes | no inbox, no grouping, no "17 problems are one pattern" step |
| Sampling review | user reviews 6/8 merged PRs | no PR classes, no sampling policy, no after-landing digest |
| Dark factory / own merges | every change via PR merged by the user; one weekly unattended timer | by design; the rung must be chosen (question 1) |
| Skills mined from history | `ai-turns`, usage reports, NOTES | no "recall"/miner routine |
| Global view | progress files in `~/.local/state/ai`, per-repo worktrees | no registry of projects, no ledger of runs/costs |

## 5. Draft architecture (to refine with the answers; keep what the answers do not contradict)

Working name of the project: to be chosen (the CLI name is asked in Q8). Components:
1. **Registry** — projects on the machine (path, remote, default branch, corpus root or none, acceptance commands,
   per-worktree setup, bot account). Discovered, then ratified.
2. **Intake** (outer loop) — connectors polled by a tick: GitHub (review threads, CI check runs, issues, Dependabot,
   `bun audit`), scheduled gardening scans, local notes. Each produces a **signal** with evidence.
3. **Buffer / triage** — signals land in an inbox; a triage run groups them into **patterns**, proposes an action
   (task draft, constraint candidate, dismiss) and never executes directly; the user ratifies through the dashboard
   or CLI.
4. **Coordinator tick** — unattended procedure: reads ratified work, chooses topology (one run per task, a wave, a
   fix-forward), launches role runs (`claude -p` or `claude --bg`, `--agent <role>`, worktree per run), monitors,
   enforces budgets, writes the ledger.
5. **Runners** — the existing roles (bastien, remi, manu, prudence, lex, dora); briefs per
   `@RULE.brief_carries_what_the_role_lacks`.
6. **Verification** — acceptance commands from the registry, prudence verdict, CI; a `verify` CLI with deterministic
   checks (branch ancestry, lint, guards, coverage, PR body shape) before any model judgment.
7. **Review sampling** — PR classes (two-way doors) and a sampling rate; after-landing digest.
8. **Miner** — transcripts (`adapters/claude-steps.py` as reader), review threads, usage reports → patterns →
   constraint proposals (RULE via lex for `~/.ai`, guard/lint for a project), with the anonymisation filter
   (real names, `76561198…` Steam ids never leave the machine).
9. **Ledger + dashboard** — append-only JSONL events (run, cost, signal, decision); dashboard = awawa-web for the
   factory corpus + one loopback page for queue/runs/costs (precedent: context-web).
10. **CLI** — one entry point with `status`, `inbox`, `triage`, `run`, `wave`, `verify`, `review`, `mine`, `ledger`,
    `doctor`; text + `--json`; fzf pickers.
Trust-ladder mapping: rung 0 (today, human relays) → rung 1 (intake + buffer + dashboard) → rung 2 (coordinator runs
tasks to PRs unattended, full review) → rung 3 (sampling review, auto-merge of two-way-door classes) → rung 4 (dark
hours). POC target = rung 2 (recommended), with rung 3 designed but switched off.
Deterministic-first list for the POC: branch/ancestry checks, worktree setup, corpus promotion edits (script, as the
parent session already does), PR body assembly, rebase-on-base (script before model), signal collection, cost ledger.

## 6. Questions returned to the user (phase 1 output) and the ANSWERS (received 2026-10-04 via the coordinator)

1. Autonomy rung — **beyond option B.** Verbatim (French): « Je pense qu'on doit aller jusqu'à ce niveau pour
   l'instant: je dis à l'agent ce que je veux faire, l'agent doit ensuite être autonome pour: créer une wave (avec
   branche d'intégration) qui découpe le travail en tâches. Confier les tâches aux agents. Les agents ouvrent des PR qui
   sont vérifiée par un autre agent spécialisé. Une fois la PR conforme, elle est mergée dans la branche d'inté. Les
   tâches suivantes démarrent au fûr et à mesure, de sorte que la wave entière est réalisée. Un agent se charge de
   générer un rapport, mettre à jour le graph de dépendances, un tableau des tests manuels que je peux faire si je veux
   vérifier le travail fourni... Si besoin de mettre à jour le corpus des instructions globales, ils peuvent le faire,
   mais ça doit figurer dans le rapport avec la raison du changement. Rien n'est irréversible car tout est versionné. La
   seule étape où j'interviens sera donc lors de la fusion de la branche d'intégration sur master (ou la branche
   principale du projet sur lequel on travaille). » → One request = one wave on an integration branch; tasks dispatched
   in dependency order; every PR verified by a specialised agent and auto-merged into the integration branch once
   compliant; a reporting agent writes the report, the updated dependency graph and a manual-test table; `~/.ai`
   changes allowed but listed in the report with their reason; the only human gate is integration → main.
2. Control plane — **A: hybrid**, factory awawa corpus + append-only JSONL ledger.
3. Intake — **all four** (GitHub review threads + CI failures, scheduled gardening scans, local notes inbox,
   transcript corrections), phased sensibly in the POC.
4. Execution — **A: local only**: user systemd timer, `ai-run`/`claude -p`, `claude --bg` for long runs.
5. Budget — **no cost cap.** Verbatim: « J'ai un abonnement max x5. Habituellement, réaliser une wave ne suffit pas
   à tout consommer donc j'imagine qu'on n'a pas besoin d'établir une limite pour le moment. Ce sera plutôt à moi
   d'ajuster mes demandes pour qu'une wave soit calibrée à peu près correctement. Sinon, le quota bloquera, il n'y a
   pas de risque de dépenser plus que prévu. Je ne pense pas qu'on ira jusqu'à 1000 PRs par jour, ce sera par wave de
   10 à 20 PRs environs j'imagine. » → Max x5 subscription; handle the rate-limit window gracefully (pause and resume
   the wave); usage stats come from the CLI's own result data, not from spend; scale = waves of 10–20 PRs.
6. Miner — **« Comme une wave »**: constraints mined from transcripts are produced and auto-merged like any wave
   work, listed in the report with their reason; the anonymisation filter stays mandatory.
7. Review policy — not asked; implied by 1: a verifier agent checks every PR; the user reviews only at the
   integration → main merge, from the report and the manual-test table; sampling may be a suggestion in the report.
8. Stack and UI — **open, recommendation wanted.** Verbatim: « je veux avoir le choix soit d'utiliser awawa-web, soit
   d'utiliser un plugin intellij comme je fais actuellement, avec peut être juste la possibilité de choisir une branche
   locale à afficher pour éviter que je doive ouvrir ou checkout les worktrees... On aurait donc un CLI et un plugin
   intellij qui permet d'afficher différents types de vues selon les besoins. Il y a un artefact qui décrit les specs du
   plugin intellij que j'utilise actuellement. A voir si on a un intérêt de rester sur un plugin intellij ou si c'est
   mieux de passer à une interface web en lançant un petit serveur local. Si on part sur l'interface web, on pourra
   potentiellement faire des écrans plus poussés avec des stats qu'on collecte via le CLI et non via mon budget d'ia,
   de la gestion de projet et de corpus... » → The plugin handbook is the artifact "awawa-ui Handbook"
   https://claude.ai/artifact/36sEqmCxcT8zNfskpe5hz3 (read with the Artifact tool). Arbitrate IntelliJ plugin vs local
   web server and say whether both are kept; a branch selector (view any local branch/worktree without checkout) is
   wanted; propose a name and use it in the mockups; CLI language is mine to recommend, Python stdlib the default.
- awawa relationship: the user consumes awawa, knows its developer who may lack time; the plan wraps the binary as it
  is; desired awawa changes go to a separate "requests to awawa's author" list, never on the POC's critical path.
- Reminders from the coordinator: update HANDOFF.md at each milestone; write only in the work directory; publish.

## 6b. Added principle (coordinator, 2026-10-04, after the answers)

Verbatim: « l'idée c'est aussi d'alléger la charge côté agents ia en passant par notre cli chaque fois que c'est
possible? Le cli = éviter de faire appel à l'ia pour des tâches mécaniques / automatiques. » → Principle 1 of the
spec: the CLI does everything mechanical, the agent only judges. Every lifecycle step is marked CLI or agent; agents
receive pre-computed context through CLI commands and hand back verdicts/outputs through CLI commands (never
rediscover state via git/gh/file reads); diagrams and mockups show the split; rough savings estimates against today's
measured flow; the POC front-loads the deterministic commands.

## 6c. Design decisions taken by Max for phase 2 (apply unless the user objects)

- Name: **brigade** (`brigade` CLI; repo `~/Web/brigade`; operational corpus `~/.config/brigade`, a git repo; state
  `~/.local/state/brigade`). Kitchen brigade = the team of roles under the chef (the user); the verification gate is
  nicknamed "the pass". Checked free on PATH and in Debian packages on 2026-10-04 (`command -v`, `apt-cache search`).
- Stack: Python 3.13 stdlib + POSIX sh (systemd units); no third-party dependency; tests with unittest. Reasons: all
  of `~/.ai` tooling, hooks and context-web are Python/sh; a machine-wide tool must not depend on a JS toolchain;
  `@RULE.tool_introduction_is_the_users_call` is satisfied with what is installed.
- UI arbitration: build the **brigade dashboard** (loopback web server, machine-wide, ledger stats, queue actions,
  branch/worktree selector via `git archive` cache per SHA + `awawa --json`); keep **awawa-ui (IntelliJ 0.8.0)**
  unchanged for in-IDE work on the checkout (handbook read: four views, `awawa --json` only, no other branch, only
  write = Clean; its own gap note says user-defined views are the extension point → that is the dashboard's job);
  keep **awawa-web** as the structural editor of the brigade corpus. The dashboard exposes a local JSON API the plugin
  may consume later (follow-up, not POC).
- Coordinator = deterministic `brigade tick` (systemd timer, every 5 min, Persistent) + repair paths; no model in the
  loop. Judgment roles: ada (plans, new), prudence (verifies), remi (review rounds), bastien (builds/fixes), manu
  (rebase conflicts only), lex (rules), rita (reports, new), mina (triage + mining, new), dora (inventories). Max is
  never launched unattended (permission rule): a stuck design question parks the wave with a question for the user.
- Runs: `claude -p --output-format stream-json --agent <role>` under `systemd-run --user` (detached, logged,
  resumable with `--resume`); `claude --bg` listed as an alternative to evaluate (attachability).
- Quota: a rate-limit result pauses the wave (`paused:quota`), resume = `--resume <session>` at the reset time the
  message names, else +30 min; the probe is the resume itself.
- Storage: brigade corpus (PROJECT, POLICY, ROUTINE, REQUEST, PATTERN, CONSTRAINT) + JSONL ledger per month; waves and
  tasks stay in each project's corpus (a project without one is bootstrapped from awawa's `starter.awawa`).
- Artifact: single main page `index.html` (tabs by hash: Overview, Plan, Mockups, Tasks, Demo) + fragments fetched at
  runtime (`parts/plan.html`, `parts/mockups.html`, `parts/demo.html`); `capabilities: {db: {}}`; tasks seeded with
  ArtifactData batch after the first publish, doc path `tasks/<id>`; statuses todo|doing|review|done|blocked.
  Title "Brigade Blueprint", icon "factory".

## 7. Phase 2 plan (after the answers)

1. `Artifact` action `quickstart` with `intent: "other"` (a multi-page HTML page with a database, not a document).
2. Load skills `artifact-design`, `artifact-capabilities` (for `db`), `artifact-diagramming` (inline SVG), `dataviz`
   only if a chart is drawn.
3. Write `index.html` (+ supporting files if multi-page: `architecture.html`, `spec.html`, `mockups.html`,
   `tasks.html`, `demo.html`, shared `styles.css`, `app.js`) in the work directory; publish with `files`. Title: a
   2–4-word name (e.g. "Agent Factory Plan"); `icon`: "factory" or "plan".
4. Task page: `db` capability; seed the POC tasks (id, title, phase/rung, component, status
   todo|doing|review|done|blocked, owner role, acceptance line, dependencies) through the page's seed logic or
   `ArtifactData` batch after the first publish; statuses editable and persisted; a per-task "brief" block an agent
   can copy.
5. Mockups: terminal sessions (`fab status`, `fab inbox`, `fab triage`, `fab run`, `fab ledger`), dashboard screens,
   a systemd/tick timeline; diagrams: inner/outer loop, trust ladder with the rung chosen, component architecture,
   data flow signal → pattern → task/constraint, run lifecycle with budgets and hand-over.
6. Spec sections: goals/non-goals; glossary; trust ladder & policies; registry; intake connectors; buffer & triage;
   coordinator tick; runners & briefs; verification; review sampling; miner & privacy; ledger & dashboard; CLI
   reference; safety envelope (permissions, budgets, human-only actions); relation to `~/.ai` and awawa (what moves
   where, agent-agnosticism kept); POC scope & milestones; open decisions; sources (transcript timestamps).
7. Update this file with the Artifact URL and what remains; return the URL to the coordinator.

## 8. Phase 2 done (2026-10-04): what exists now

**Artifact URL: https://claude.ai/artifact/ENPmZkLZS85qhvVBakhXJe** — title "Brigade Blueprint", icon factory,
version 1 (id 1791149122-2347), `capabilities: {db: {}}`, private to the owner until shared. Republish from another
conversation with `url` set to that address, after an `Artifact read` of it; from this directory, publishing
`index.html` again with the same `files` map keeps the URL.

Pages (tabs by hash): `#overview` (inline in `index.html`: thesis, the settled answers, the trust ladder SVG, the
talk-vs-machine table), `#plan` (`parts/plan.html`, 20 sections, 5 SVG diagrams, CLI/agent tags, savings
estimates), `#mockups` (`parts/mockups.html`: 10 terminal mockups with ids `t-*`, 4 dashboard screens `s-*`),
`#tasks` (inline, `db`-backed board), `#demo` (`parts/demo.html` + JS in `index.html`: fake terminal replaying the
`t-*` mockups, a scripted wave stepper), `#brief` (`parts/brief.html`, the appendix rendered from
`BRIEF-and-relays.md`, the clean English version; added at the coordinator's request). Sub-anchors `p-*`, `m-*`,
`b-*`, `t-*`, `s-*` route to their tab.

Constraints honoured on every page: no verbatim French of the user, no home-directory or scratchpad path, no
account names (the instructions corpus is written `<rootDir>`, brigade's directories `$XDG_CONFIG_HOME/brigade`
and `$XDG_STATE_HOME/brigade`, the example project `<checkout>/planet-crafter-save-tools`). A scrub check
(`grep -nE '~/|/home/|chillie|delairec|Clauche|/tmp/'`) returned nothing on 2026-10-04.

Task board: collection `tasks`, documents `B01`…`B39` seeded by `ArtifactData batch` (all version 1, status
`todo`), fields id, title, milestone, milestone_title, component, role, acceptance, depends[], status, notes, order,
updated_at. The page writes `status`, `notes`, `updated_at`, `updated_by` through `update`. Seed source:
`seed/B*.json` in this directory, generated by the same Python data as `docs/tasks.awawa` of the repository.

Checks run before publishing: tag balance of the 5 HTML files (0 errors), dangling anchors (0), demo command ids
(all present), `node --check` on the page script (exit 0), SVG `var()` moved from presentation attributes to
`style`. No visual preview tool was available in this session; the first look at the rendered page is the user's.

**Local repository: `~/Web/brigade`** (created at the coordinator's invitation; local only, no remote, no push):
`README.md`, `HANDOFF.md` (copy of this file), `artifact/` (index.html + parts/), `docs/` (the project's own awawa
corpus: `_schema.awawa`, `project.awawa`, `milestones.awawa` M0–M6, `tasks.awawa` B01–B39 all `draft`,
`decisions.awawa` with 10 DECISIONs of this plan; `awawa lint --strict .` 0 errors, 0 warnings),
`schema/_schema.awawa.tpl` (the operational schema `brigade init` installs; linted in a temp workspace). One initial
commit on `main`.

What remains for the user or a successor:
- read the Artifact; the "Open decisions" section (plan §19) lists the five choices left open on purpose;
- ratify the POC tasks (board statuses, or `draft → todo` in `docs/tasks.awawa`) and start B01–B08 (deterministic
  commands first), ideally as a wave of the example project's machinery until brigade can run its own;
- the three new roles (ada, rita, mina) are a PR on the instructions corpus (B09), not yet written;
- optional: share the Artifact (it is private), pin it, and correct any rendering defect found at first look.

## 9. Files written by this run

Work directory: `HANDOFF.md`, `chatgpt-summary.md`, `index.html`, `parts/plan.html`, `parts/mockups.html`,
`parts/demo.html`, `parts/brief.html`, `seed/B01.json`…`seed/B39.json`. Repository: see §8.
