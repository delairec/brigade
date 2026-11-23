SCHEMA *
	DESC "fields legal on every entity of this corpus"
	FIELD DESC string
		REPEATABLE
		FIELD REF reference
			REPEATABLE
			DESC "an entity the prose above names, indexed"
	FIELD RATIONALE string
		REPEATABLE
		CATEGORY reasoning
		FIELD REF reference
			REPEATABLE
			DESC "an entity the prose above names, indexed"
	FIELD SOURCE string
		REPEATABLE
		DESC "where this was decided or read"
		FIELD REF reference
			REPEATABLE
			DESC "an entity the prose above names, indexed"

SCHEMA MILESTONE
	DESC "a delivery the tasks are planned against"
	FIELD TITLE string
		REQUIRED
	FIELD SUBJECT string
		DESC "the subject of its pull request, opening on a verb in the imperative"
	FIELD STATUS planned|active|reached
		REQUIRED
	WHEN STATUS reached
		GATE error

SCHEMA TASK
	DESC "a unit of work delivered by one pull request"
	FIELD TITLE string
		REQUIRED
		DESC "what the task delivers, in one line"
	FIELD STATUS draft|todo|implemented|archived
		REQUIRED
		DESC "draft: not ratified; todo: ratified; implemented: merged; archived: retired"
	FIELD TYPE build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test
		DESC "the Conventional Commits type of the pull request that delivers it"
	FIELD SPEC string
		REQUIRED
		REPEATABLE
		DESC "one acceptance criterion, observable once delivered"
		FIELD IMPL anchor
			REPEATABLE
			DESC "the test or the code where the criterion is proven; written at delivery"
	FIELD MILESTONE @MILESTONE
		CONVERSE COMPRISES
	FIELD COMPONENT string
		DESC "the part of the project the task touches"
	FIELD AFTER @TASK
		REPEATABLE
		CONVERSE BEFORE
		DESC "the task that must merge before this one"
	FIELD DELIVERED_BY uint
		DESC "the number of the pull request that delivers it; absent on a project with no forge"
	FIELD CORRECTS uint
		REPEATABLE
		DESC "the number of a pull request the task corrects; required on a fix by brigade build pr"
	WHEN STATUS draft
		GATE suppressed
	WHEN STATUS todo
		GATE error
		FIELD TYPE
			REQUIRED
	WHEN STATUS implemented
		GATE error
		FIELD TYPE
			REQUIRED
		FIELD SPEC
			REQUIRED
			REPEATABLE
			FIELD IMPL
				REQUIRED
				REPEATABLE
	WHEN STATUS archived
		GATE suppressed

SCHEMA DECISION
	DESC "a ruling of the project, and what it turned down"
	FIELD TITLE string
		REQUIRED
	FIELD STATUS active|archived
		REQUIRED
	FIELD REJECTED string
		REPEATABLE
		DESC "an alternative, then why it was refused"
	FIELD CLOSES @OPEN_QUESTION
		REPEATABLE
		CONVERSE CLOSED_BY
	WHEN STATUS active
		GATE error
	WHEN STATUS archived
		GATE suppressed

SCHEMA OPEN_QUESTION
	DESC "a project-level fact left undecided"
	FIELD QUESTION string
		REQUIRED
	FIELD STATUS open|closed
		REQUIRED
	FIELD BLOCKS @TASK
		REPEATABLE
		CONVERSE BLOCKED_BY
		DESC "a task that cannot be ratified until the question is ruled"
	WHEN STATUS closed
		GATE suppressed

SCHEMA PREFLIGHT
	DESC "a custom preflight of the project, a named set of collectors and checks brigade preflight"
		+ "<name> runs; the entity is named after the preflight, its hyphens as underscores"
	FIELD TITLE string
		REQUIRED
		DESC "what the preflight checks, in one line"
	FIELD COLLECTOR string
		REPEATABLE
		DESC "a collector the preflight runs first, by name"
		FIELD PARAMETER string
			REPEATABLE
			DESC "a parameter of the collector, key=value"
	FIELD CHECK string
		REPEATABLE
		DESC "a check the preflight runs on the documents of its collectors, by name"
		FIELD PARAMETER string
			REPEATABLE
			DESC "a parameter of the check, key=value"

SCHEMA RECIPE
	DESC "a kind of work brigade runs as ordered steps; its name is the name of the recipe"
	FIELD SCHEMA_VERSION uint
		REQUIRED
	FIELD PARAM string
		REPEATABLE
		DESC "a parameter the order gives, substituted where a value holds {name}"
	FIELD MAX_WALL uint
		REQUIRED
		DESC "the minutes a run of the recipe may last"
	FIELD STEP collect|command|gate|judge|output|order|corpus|op
		REQUIRED
		REPEATABLE
		DESC "one step, in the order the recipe runs them"
		FIELD COLLECTOR string
		FIELD PARAMETER string
			REPEATABLE
			DESC "key=value, a parameter of the collector or of the order"
		FIELD ARGV string
			REPEATABLE
			DESC "one argument of the command, in order"
		FIELD PREFLIGHT string
		FIELD SLOT string
		FIELD PROCEDURE string
		FIELD ANSWER string
			DESC "the schema of the answer of a judge step, the entity it fills"
		FIELD OUTPUT string
		FIELD RECIPE string
		FIELD ENTITY string
		FIELD OP worktree|commit|pull-request|merge
		FIELD ON_FAIL string
			DESC "park by default, else skip, stop or retry:N"
