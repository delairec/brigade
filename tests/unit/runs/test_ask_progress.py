import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.ask_progress import ask_progress
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.system.entry_detection import EntryDetection
from brigade.system.read_configuration import Configuration

NO_ARGUMENTS = {}
NO_WAVE = None
NO_TASK = None
NO_WARNINGS = ()
NO_RUNTIME_NEEDED = None


class EntryDetectorDouble:
    def __init__(self):
        self.paths = []

    def detect_entry(self, request: dict, runtime) -> dict:
        self.paths.append(request["path"])
        return {"schema_version": 1, "holds_entry": False}


class EntryDetectorAnsweringNoVersionDouble:
    def detect_entry(self, request: dict, runtime) -> dict:
        return {"holds_entry": False}


def _create_plan(document, configuration: Configuration) -> RunPlan:
    return RunPlan(
        run_id="20261013T194621Z-3077b0",
        run_directory=Path("/state/brigade/runs/20261013T194621Z-3077b0"),
        procedure=Procedure(
            name="awawa-task",
            location="built-in",
            argument="awawa-task",
            capabilities=("read", "write", "shell"),
            budget=75,
            body="Deliver the task.",
        ),
        slot="build",
        role=ResolvedRole(slot="build", role="ada", source="machine", front_matter={"reasoning": "standard"}, body=""),
        client="claude-code",
        client_adapter=None,
        document=document,
        progress_file=Path("/state/brigade/runs/20261013T194621Z-3077b0/progress.md"),
        configuration=configuration,
        project="brigade",
        cwd=Path("/srv/brigade"),
        worktree=Path("/srv/brigade/.claude/worktrees/b106"),
        disposable_worktree=False,
        capabilities=("read", "write", "shell"),
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


class AskProgressTest(unittest.TestCase):
    def test_should_ask_the_document_of_the_run_about_its_progress_file(self):
        # Arrange
        document = EntryDetectorDouble()
        plan = _create_plan(document, Configuration(document="markdown"))

        # Act
        answer = ask_progress(plan, "detect_entry", NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(document.paths, ["/state/brigade/runs/20261013T194621Z-3077b0/progress.md"])
        self.assertEqual(answer, EntryDetection(holds_entry=False))

    def test_should_refuse_an_answer_breaking_its_shape_naming_the_plugin_the_configuration_chose(self):
        # Arrange
        plan = _create_plan(EntryDetectorAnsweringNoVersionDouble(), Configuration(document="markdown"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_progress(plan, "detect_entry", NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "document plugin markdown answered detect_entry: lacks the key schema_version"
        )
