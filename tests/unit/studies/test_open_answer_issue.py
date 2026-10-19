import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.open_answer_issue import open_answer_issue
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

PUBLICATION = AnswerPublication(title="Study trees, run 1", markdown="# FINDING trees_1\n")


def create_study(project: str | None) -> Study:
    return Study(
        name="trees",
        project=project,
        question=None,
        collectors=(),
        slot="none",
        every=None,
        output="issue",
        answer_type="FINDING",
        status="active",
    )


class ForgeDouble:
    def __init__(self):
        self.issues = []

    def open_issue(self, request: dict, runtime) -> dict:
        self.issues.append(request)
        return {"url": "https://github.com/acme/oak/issues/3"}


class OpenAnswerIssueTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)
        self.forges = {"github": ForgeDouble()}

    def create_context(self, project: str | None) -> StudyRunContext:
        equipment = create_study_equipment(resolve_forge=self.forges.__getitem__)
        return StudyRunContext(
            runtime=self.runtime,
            study=create_study(project),
            run_id="1",
            run_directory=Path("/run"),
            equipment=equipment,
        )

    def register_project(self, forge: str) -> None:
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", forge))}
        )

    def test_should_answer_the_issue_it_opened(self):
        # Arrange
        self.register_project("github")

        # Act
        opened = open_answer_issue(self.create_context("oak"), PUBLICATION)

        # Assert
        self.assertEqual(opened, {"issue": "https://github.com/acme/oak/issues/3"})

    def test_should_open_an_issue_holding_the_answer_on_the_forge_of_the_project(self):
        # Arrange
        self.register_project("github")

        # Act
        open_answer_issue(self.create_context("oak"), PUBLICATION)

        # Assert
        self.assertEqual(
            self.forges["github"].issues,
            [{"repository": "/srv/oak", "title": "Study trees, run 1", "body": "# FINDING trees_1\n"}],
        )

    def test_should_refuse_a_project_without_a_forge(self):
        # Arrange
        self.register_project("none")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_answer_issue(self.create_context("oak"), PUBLICATION)

        # Assert
        self.assertEqual(str(refusal.exception), "the output issue needs a project with a forge")

    def test_should_refuse_a_study_of_no_project(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_answer_issue(self.create_context(None), PUBLICATION)

        # Assert
        self.assertEqual(str(refusal.exception), "the output issue needs a project")
