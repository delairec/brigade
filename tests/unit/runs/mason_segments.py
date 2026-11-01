MASON_ROLE = (
    "---\n"
    "name: mason\n"
    "slot: build\n"
    "work: the delivery of a task\n"
    "reasoning: standard\n"
    "capabilities: read, write, shell\n"
    "budget: 40\n"
    "returns: the pull request\n"
    "---\n"
    "You build on this machine.\n"
)
SURVEY_PROCEDURE = "---\ncapabilities: read\n---\nSurvey the code.\n"
EARLIER_MASON_BUDGET_APPLIED = (
    '{"schema_version": 1, "ts": "2026-09-30T16:00:00Z", "event": "budget.applied", "role": "mason",'
    ' "before": 40, "after": 50, "segments": 5, "restarts": 3, "growth": 80.0, "restart_tokens": 100000.0}\n'
)
STONEMASON_BUDGET_APPLIED = (
    '{"schema_version": 1, "ts": "2026-10-01T16:00:00Z", "event": "budget.applied", "role": "stonemason",'
    ' "before": 40, "after": 63, "segments": 6, "restarts": 3, "growth": 100.0, "restart_tokens": 200000.0}\n'
)
MASON_BUDGET_APPLIED = (
    '{"schema_version": 1, "ts": "2026-10-01T16:00:00Z", "event": "budget.applied", "role": "mason",'
    ' "before": 40, "after": 63, "segments": 6, "restarts": 3, "growth": 100.0, "restart_tokens": 200000.0}\n'
)
MASON_SEGMENTS = (
    '{"schema_version": 2, "ts": "2026-10-01T10:00:00Z", "event": "run.finished", "run": "r1", "segment": 1, "procedure": "survey", "slot": "build", "role": "mason", "client": "fake", "project": null, "session": null, "main_steps": 10, "total_steps": 10, "duration_ms": 1000, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 15000}, "outcome": "turn_limit", "error_class": null, "exit": 0, "wave": null, "task": null, "nulls": {}, "role_digest": "1744eae073ad8eb50f762784e42bd950632bb2af9f119d4431640e691deddd3c", "procedure_digest": "2a3fea52accc14572c3f7875f2f6c3b320ccd1d8eeea874d5e0de4b583eb2b22"}\n'
    '{"schema_version": 2, "ts": "2026-10-01T11:00:00Z", "event": "run.finished", "run": "r1", "segment": 2, "procedure": "survey", "slot": "build", "role": "mason", "client": "fake", "project": null, "session": null, "main_steps": 20, "total_steps": 20, "duration_ms": 1000, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 40000}, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null, "nulls": {}, "tokens_to_first_edit": 200000, "role_digest": "1744eae073ad8eb50f762784e42bd950632bb2af9f119d4431640e691deddd3c", "procedure_digest": "2a3fea52accc14572c3f7875f2f6c3b320ccd1d8eeea874d5e0de4b583eb2b22"}\n'
    '{"schema_version": 2, "ts": "2026-10-01T12:00:00Z", "event": "run.finished", "run": "r2", "segment": 1, "procedure": "survey", "slot": "build", "role": "mason", "client": "fake", "project": null, "session": null, "main_steps": 30, "total_steps": 30, "duration_ms": 1000, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 75000}, "outcome": "turn_limit", "error_class": null, "exit": 0, "wave": null, "task": null, "nulls": {}, "role_digest": "1744eae073ad8eb50f762784e42bd950632bb2af9f119d4431640e691deddd3c", "procedure_digest": "2a3fea52accc14572c3f7875f2f6c3b320ccd1d8eeea874d5e0de4b583eb2b22"}\n'
    '{"schema_version": 2, "ts": "2026-10-01T13:00:00Z", "event": "run.finished", "run": "r2", "segment": 2, "procedure": "survey", "slot": "build", "role": "mason", "client": "fake", "project": null, "session": null, "main_steps": 40, "total_steps": 40, "duration_ms": 1000, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 120000}, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null, "nulls": {}, "tokens_to_first_edit": 200000, "role_digest": "1744eae073ad8eb50f762784e42bd950632bb2af9f119d4431640e691deddd3c", "procedure_digest": "2a3fea52accc14572c3f7875f2f6c3b320ccd1d8eeea874d5e0de4b583eb2b22"}\n'
    '{"schema_version": 2, "ts": "2026-10-01T14:00:00Z", "event": "run.finished", "run": "r3", "segment": 1, "procedure": "survey", "slot": "build", "role": "mason", "client": "fake", "project": null, "session": null, "main_steps": 50, "total_steps": 50, "duration_ms": 1000, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 175000}, "outcome": "turn_limit", "error_class": null, "exit": 0, "wave": null, "task": null, "nulls": {}, "role_digest": "1744eae073ad8eb50f762784e42bd950632bb2af9f119d4431640e691deddd3c", "procedure_digest": "2a3fea52accc14572c3f7875f2f6c3b320ccd1d8eeea874d5e0de4b583eb2b22"}\n'
    '{"schema_version": 2, "ts": "2026-10-01T15:00:00Z", "event": "run.finished", "run": "r3", "segment": 2, "procedure": "survey", "slot": "build", "role": "mason", "client": "fake", "project": null, "session": null, "main_steps": 10, "total_steps": 10, "duration_ms": 1000, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 15000}, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null, "nulls": {}, "tokens_to_first_edit": 200000, "role_digest": "1744eae073ad8eb50f762784e42bd950632bb2af9f119d4431640e691deddd3c", "procedure_digest": "2a3fea52accc14572c3f7875f2f6c3b320ccd1d8eeea874d5e0de4b583eb2b22"}\n'
)
STONEMASON_ROLE = MASON_ROLE.replace("name: mason\n", "name: stonemason\n").replace("slot: build\n", "slot: plan\n")
