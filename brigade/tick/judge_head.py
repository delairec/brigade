from brigade.tick.head_proof import GREEN, PENDING, RED, UNPROVEN, HeadEvidence, HeadProof

SUCCESSFUL_CHECK = "success"
PENDING_CHECK = "pending"
PASSED_EXIT_CODE = 0


def _list_forge_failures(evidence: HeadEvidence) -> tuple[str, ...] | None:
    if not evidence.forge_checks:
        return None
    return tuple(check.name for check in evidence.forge_checks if check.verdict != SUCCESSFUL_CHECK)


def _list_task_check_failures(evidence: HeadEvidence) -> tuple[str, ...] | None:
    if evidence.task_check is None or evidence.task_check.head != evidence.commit:
        return None
    return evidence.task_check.failed_commands


def _list_commit_check_failures(evidence: HeadEvidence) -> tuple[str, ...] | None:
    if evidence.commit_checks is None:
        return None
    return tuple(result.command for result in evidence.commit_checks.results if result.exit_code != PASSED_EXIT_CODE)


def _is_forge_pending(evidence: HeadEvidence) -> bool:
    return any(check.verdict == PENDING_CHECK for check in evidence.forge_checks)


def judge_head(evidence: HeadEvidence) -> HeadProof:
    readings = tuple(
        failures
        for failures in (
            _list_forge_failures(evidence),
            _list_task_check_failures(evidence),
            _list_commit_check_failures(evidence),
        )
        if failures is not None
    )
    if any(not failures for failures in readings):
        return HeadProof(commit=evidence.commit, state=GREEN, failed_commands=())
    if _is_forge_pending(evidence):
        return HeadProof(commit=evidence.commit, state=PENDING, failed_commands=())
    if readings:
        return HeadProof(commit=evidence.commit, state=RED, failed_commands=readings[0])
    return HeadProof(commit=evidence.commit, state=UNPROVEN, failed_commands=())
