SCHEMA STEP
	DESC "a step the run completed"
	FIELD DONE string
		REQUIRED
		DESC "what the step did, one line"
	FIELD FACT string
		REPEATABLE
		DESC "a fact the next run needs and no command gives back, five at most"
	FIELD NEXT string
		REQUIRED
		DESC "the step to resume at, as the procedure names it, or complete"

SCHEMA HANDOVER
	DESC "the state of a run that hands over"
	FIELD FACT string
		REPEATABLE
		DESC "a fact no step holds, five at most"
	FIELD REMAINING string
		REQUIRED
		REPEATABLE
		DESC "a step not done, one per line"
	FIELD NEXT string
		REQUIRED
		DESC "the step to resume at, as the procedure names it"
