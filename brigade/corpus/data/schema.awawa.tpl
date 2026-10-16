// Schema of the brigade operational corpus, installed by `brigade init` as _schema.awawa in the
// config directory from brigade/corpus/data/schema.awawa.tpl, a name that keeps it out of brigade's
// own corpus (two SCHEMA * in one workspace collide).
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
		DESC "the corpus folder, relative to PATH, the anchors resolve from: corpus/ when brigade"
			+ "creates it, else the root project add discovered"
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
	FIELD MERGE squash|rebase|merge
		DEFAULT squash
	FIELD GRAPH string
		DESC "the command that regenerates the dependency graph document"
	FIELD CLIENT string
		DESC "the client adapter of this project's runs; config.toml's default when absent"
	FIELD ROLESET string
		DESC "builtin, corpus, or a directory of role files; the resolution order when absent"
	FIELD ROLE string
		REPEATABLE
		DESC "slot=role, an override of the binding, e.g. remediate=builder"
	FIELD PRIVATE string
		REPEATABLE
		DESC "a regular expression the privacy scan and the scrubber refuse, e.g. stn_[0-9a-f]{12}"
	FIELD FORGE string
		DESC "github or none"
	FIELD STATUS active|paused
		REQUIRED

SCHEMA POLICY
	DESC "how far a project's waves run on their own"
	FIELD PROJECT @PROJECT
		REQUIRED
	FIELD PLAN_REVIEW ask|auto
		DEFAULT auto
	FIELD REVIEW approval|verdict
		DEFAULT verdict
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

SCHEMA STUDY
	DESC "a question answered by evidence: collectors, then at most one judging run; with no slot,"
		+ "a scan"
	FIELD TITLE string
		REQUIRED
	FIELD QUESTION string
		DESC "the user's words, verbatim; absent for a scan"
	FIELD PROJECT @PROJECT
		DESC "absent for a machine-wide study"
	FIELD COLLECTOR string
		REQUIRED
		REPEATABLE
		DESC "a collector name with its parameters, e.g. git-log since=30d, or shell: <command>,"
			+ "one argv split by shlex.split and run without a shell"
	FIELD SLOT report|explore|triage|rules|none
		DEFAULT report
		DESC "the judging slot; none makes the study a scan"
	FIELD EVERY string
		DESC "a brigade schedule evaluated by the tick: 5m, 1h, daily@09:00, mon@09:00; absent"
			+ "means on demand"
	FIELD OUTPUT string
		REQUIRED
		DESC "file:<path pattern>, entity:<TYPE>, issue, or an output on PATH; inbox refused until"
			+ "task B22"
	FIELD ANSWER string
		DEFAULT "ANSWER"
		DESC "the entity type of this schema the answer is written as"
	FIELD STATUS active|paused|archived
		REQUIRED
	WHEN STATUS archived
		GATE suppressed

SCHEMA ANSWER
	DESC "the answer of one run of a study: the CLI fills what the collectors gave, the judging"
		+ "slot the prose"
	FIELD STUDY string
		REQUIRED
		DESC "the name of the STUDY answered"
	FIELD RUN string
		REQUIRED
		DESC "the run of the study"
	FIELD COLLECTED string
		REPEATABLE
		DESC "one per collector, its name, filled by the CLI"
		FIELD SUMMARY string
			REQUIRED
			DESC "the summary of its document, as JSON"
		FIELD DOCUMENT string
			REQUIRED
			DESC "the path of its full document"
	FIELD NARRATIVE string
		REPEATABLE
		DESC "filled by the judging slot"
	FIELD FINDING string
		REPEATABLE
		DESC "one finding with its evidence, filled by the judging slot"

SCHEMA ORDER
	DESC "one instance of a recipe: its parameters, its project, its schedule"
	FIELD RECIPE string
		REQUIRED
	FIELD PROJECT @PROJECT
		DESC "absent for a machine-wide order"
	FIELD TEXT string
		DESC "the user's words, verbatim, when the recipe takes them"
	FIELD PARAM string
		REPEATABLE
		DESC "key=value"
	FIELD EVERY string
		DESC "a brigade schedule evaluated by the tick; absent means on demand"
	FIELD OUTPUT string
		DESC "an override of the recipe's output"
	FIELD STATUS active|paused|archived
		REQUIRED
	WHEN STATUS archived
		GATE suppressed

SCHEMA REQUEST
	DESC "what the user wants for one project, in their words; it becomes one wave"
	FIELD PROJECT @PROJECT
		REQUIRED
	FIELD TEXT string
		REQUIRED
	FIELD CREATED_AT string
		DESC "the UTC instant the request was recorded, YYYY-MM-DDTHH:MM:SSZ"
	FIELD STATUS planning|planned|running|paused|reporting|delivered|closed|cancelled
		REQUIRED
	FIELD MILESTONE string
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
	FIELD ACTION wave|constraint|order|dismiss
	FIELD RECIPE string
		DESC "the recipe an order action places"
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
