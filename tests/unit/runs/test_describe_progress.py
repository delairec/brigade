import unittest
from pathlib import Path

from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.describe_progress import describe_progress
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.system.document_request import DocumentRequest
from brigade.system.parse_configuration import Configuration

NO_ARGUMENTS = {}
NO_WAVE = None
NO_TASK = None
NO_WARNINGS = ()
PROGRESS_SCHEMA = """SCHEMA STEP
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
"""


def _create_plan(capabilities: tuple[str, ...]) -> RunPlan:
    return RunPlan(
        run_id="20261013T194621Z-3077b0",
        run_directory=Path("/state/brigade/runs/20261013T194621Z-3077b0"),
        procedure=Procedure(
            name="awawa-task",
            location="built-in",
            argument="awawa-task",
            capabilities=capabilities,
            budget=75,
            body="Deliver the task.",
        ),
        slot="build",
        role=ResolvedRole(slot="build", role="ada", source="machine", front_matter={"reasoning": "standard"}, body=""),
        client="claude-code",
        client_adapter=None,
        document=None,
        progress_file=Path("/state/brigade/runs/20261013T194621Z-3077b0/progress.awawa"),
        configuration=Configuration(),
        project="brigade",
        cwd=Path("/srv/brigade"),
        worktree=Path("/srv/brigade/.claude/worktrees/b106"),
        disposable_worktree=False,
        capabilities=capabilities,
        wall_limit_s=2820.0,
        arguments=NO_ARGUMENTS,
        wave=NO_WAVE,
        task=NO_TASK,
        brief_path=None,
        brief=None,
        counts_steps=True,
        reads_actions=True,
        reads_transcripts=True,
        handovers=1,
        warnings=NO_WARNINGS,
    )


class DescribeProgressTest(unittest.TestCase):
    def test_should_describe_the_progress_of_the_run_to_its_document_plugin(self):
        # Arrange
        plan = _create_plan(capabilities=("read", "write", "shell"))

        # Act
        request = describe_progress(plan)

        # Assert
        self.assertEqual(
            request,
            DocumentRequest(
                document="progress",
                path="/state/brigade/runs/20261013T194621Z-3077b0/progress.awawa",
                schema=PROGRESS_SCHEMA,
                frame=(
                    (
                        "one entry per major step: what it did in one line, the facts it established, one line each"
                        " and five at most, and the next step as the procedure names it, complete at the end"
                    ),
                    "a fact is what the next segment needs and no command gives back",
                    (
                        "never command output, a diff, the course of the step, a restatement of the brief or a fact"
                        " an earlier entry holds"
                    ),
                    "a handover entry holds what remains, one line per step not done, and the next step",
                ),
                role_has_shell=True,
            ),
        )

    def test_should_tell_the_plugin_that_a_role_without_shell_cannot_run_awawa(self):
        # Arrange
        plan = _create_plan(capabilities=("read", "write"))

        # Act
        request = describe_progress(plan)

        # Assert
        self.assertFalse(request.role_has_shell)
