from brigade.tick.build_snapshot import ProjectFacts, Snapshot
from brigade.tick.is_milestone_cut_due import is_milestone_cut_due
from brigade.tick.is_rebase_due import is_rebase_due
from brigade.waves.list_candidate_waves import CandidateWave

AUTOMATIC_WAVE_START = "auto"


def _is_rebased_in_the_round(snapshot: Snapshot, project: ProjectFacts, candidate: CandidateWave) -> bool:
    return any(
        is_rebase_due(milestone)
        for milestone in snapshot.milestones
        if (milestone.project, milestone.milestone) == (project.name, candidate.milestone)
    )


def _is_cut_in_the_round(project: ProjectFacts, candidate: CandidateWave) -> bool:
    return any(
        is_milestone_cut_due(uncut) for uncut in project.uncut_milestones if uncut.milestone == candidate.milestone
    )


def find_wave_start_hold(snapshot: Snapshot, project: ProjectFacts, candidate: CandidateWave) -> str | None:
    if project.wave_start != AUTOMATIC_WAVE_START:
        return f"the policy of @PROJECT.{project.name} asks before a wave start, WAVE_START {project.wave_start}"
    if _is_rebased_in_the_round(snapshot, project, candidate):
        return f"the branch of {candidate.milestone} is rebased in this round"
    if _is_cut_in_the_round(project, candidate):
        return f"the branch of {candidate.milestone} is cut in this round"
    return None
