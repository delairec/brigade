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
		DESC "the number of the pull request that delivers it"
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
		FIELD DELIVERED_BY
			REQUIRED
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
