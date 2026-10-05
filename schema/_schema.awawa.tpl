// Schema of the brigade operational corpus, installed by `brigade init` as _schema.awawa in the
// config directory. Kept with a .tpl extension here so that it does not join this repository's own
// corpus (two SCHEMA * in one workspace collide).
SCHEMA *
	DESC "fields legal on every entity of the operational corpus"
	FIELD DESC string
		REPEATABLE
	FIELD RATIONALE string
		REPEATABLE
		CATEGORY reasoning

SCHEMA PROJECT
	DESC "a registered repository on this machine"
	FIELD PATH string
		REQUIRED
	FIELD REMOTE string
	FIELD MAIN string
		REQUIRED
	FIELD CORPUS string
		DESC "the workspace root the anchors resolve from, relative to PATH"
	FIELD ACCEPTANCE string
		REPEATABLE
		DESC "a light command run by task check"
	FIELD HEAVY string
		REPEATABLE
		DESC "a suite left to continuous integration, read on the pull request"
	FIELD SETUP string
		REPEATABLE
		DESC "a per-worktree command"
	FIELD SLOTS uint
		DEFAULT 4
	FIELD ADAPTER string
		DESC "the agent-CLI adapter that launches the runs; the first adapter when absent"
	FIELD GRAPH string
		DESC "the command that regenerates the dependency graph document"
	FIELD STATUS active|paused
		REQUIRED

SCHEMA POLICY
	DESC "how far a project's waves run on their own"
	FIELD PROJECT @PROJECT
		REQUIRED
	FIELD PLAN_REVIEW ask|auto
		DEFAULT ask
		DESC "ask for the first waves of a newly registered project, then auto"
	FIELD VERIFY_ROUNDS uint
		DEFAULT 2
	FIELD HANDOVERS uint
		DEFAULT 2
	FIELD AUTO_MERGE integration|none
		DEFAULT integration
	FIELD AUTO_RATIFY uint
		DEFAULT 0
	FIELD SAMPLING suggestions|none
		DEFAULT suggestions

SCHEMA ROUTINE
	DESC "a scheduled deterministic scan whose non-zero output is a signal"
	FIELD KIND gardening|intake
		REQUIRED
	FIELD COMMAND string
		REQUIRED
	FIELD EVERY string
		REQUIRED
		DESC "a systemd calendar expression"
	FIELD PROJECT @PROJECT
	FIELD STATUS active|paused
		REQUIRED

SCHEMA REQUEST
	DESC "what the user wants for one project, in their words; it becomes one wave"
	FIELD PROJECT @PROJECT
		REQUIRED
	FIELD TEXT string
		REQUIRED
	FIELD STATUS planning|planned|running|paused|reporting|delivered|closed|cancelled
		REQUIRED
	FIELD WAVE string
	FIELD BRANCH string
	FIELD FROM @PATTERN
	WHEN STATUS closed
		GATE suppressed
	WHEN STATUS cancelled
		GATE suppressed

SCHEMA PATTERN
	DESC "several signals that are one thing, with their evidence"
	FIELD TITLE string
		REQUIRED
	FIELD STATUS new|ratified|dismissed|delivered
		REQUIRED
	FIELD EVIDENCE string
		REPEATABLE
	FIELD ACTION wave|constraint|dismiss
	FIELD TARGET string
	WHEN STATUS dismissed
		GATE suppressed

SCHEMA CONSTRAINT
	DESC "what a ratified pattern becomes: a rule, a guard, a lint, a schema change, a skill or a"
		+ "script"
	FIELD TITLE string
		REQUIRED
	FIELD KIND rule|guard|lint|schema|skill|script
		REQUIRED
	FIELD FROM @PATTERN
		REQUIRED
	FIELD TARGET string
		REQUIRED
	FIELD STATUS proposed|delivered|rejected
		REQUIRED
	FIELD DELIVERED_BY string
	WHEN STATUS rejected
		GATE suppressed
