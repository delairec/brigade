import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import CommandFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.studies.convert_study import Study
from brigade.studies.publish_task_report import publish_task_report
from brigade.studies.study_run_context import StudyRunContext
from brigade.studies.task_report_order import TaskReportOrder
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261103T100000Z-bbbbbb"
BRANCH = "feature/B46-local-mode"
REPORT_PATH = "corpus/tasks/B46-report.md"
MARKDOWN = "# REPORT oak_B46\n\n- TASK: B46\n"
STUDY = Study(
    name="task-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    task=TaskReportOrder(project="oak", task="B46", wave="oak_w4", branch=BRANCH),
)
NOTHING_BOUND = Configuration()


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "REPORT", "name": "oak_B46", "fields": [{"name": "TASK", "value": "B46"}]}]}


def create_forge() -> ForgeDouble:
    return ForgeDouble({"rewrite_pull_request_body": lambda request: {"schema_version": 1}})


class PublishTaskReportTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.checkout = self.run_directory / "checkout"
        self.forge = create_forge()
        self.processes.answer(("git", "fetch", "--quiet", "origin", BRANCH))
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), f"origin/{BRANCH}"))
        self.processes.answer(("git", "add", "--", REPORT_PATH))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", REPORT_PATH), exit_code=1)
        self.processes.answer(("git", "commit", "--quiet", "-m", "docs(tasks): add the report of B46"))
        self.processes.answer(("git", "push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}"))
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.checkout)))
        append_event(
            self.runtime.paths,
            self.runtime.now,
            TaskPrOpened(project="oak", task="B46", wave="oak_w4", branch="main", pr=212, login="octo-cli"),
        )

    def create_context(self, forge: str) -> StudyRunContext:
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("FORGE", forge), ("CORPUS", "corpus"), ("MAIN", "main"))},
        )
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(
                configuration=NOTHING_BOUND, forge=None, forge_name="github", resolve_client=None
            ),
            document=DocumentDouble(),
            resolve_forge={"github": self.forge}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id=RUN_ID, run_directory=self.run_directory, equipment=equipment
        )

    def test_should_write_the_markdown_of_the_report_under_the_tasks_folder_of_the_corpus(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_task_report(context)

        # Assert
        self.assertEqual((self.checkout / REPORT_PATH).read_text(encoding="utf-8"), MARKDOWN)

    def test_should_answer_the_report_the_task_branch_received_and_the_pull_request_whose_body_it_became(self):
        # Arrange
        context = self.create_context("github")

        # Act
        published = publish_task_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": 212})

    def test_should_replace_the_body_of_the_pull_request_of_the_task_with_the_report(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_task_report(context)

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body"),
            [{"repository": str(self.checkout), "number": 212, "body": MARKDOWN, "environment": {}}],
        )

    def test_should_replace_no_body_on_a_project_without_a_forge(self):
        # Arrange
        context = self.create_context("none")

        # Act
        published = publish_task_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": None})
        self.assertEqual(self.forge.list_operations(), [])

    def test_should_commit_the_report_on_a_detached_checkout_of_the_task_branch_push_it_and_remove_the_checkout(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_task_report(context)

        # Assert
        self.assertEqual(
            self.processes.list_argvs()[-7:],
            [
                ("git", "fetch", "--quiet", "origin", BRANCH),
                ("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), f"origin/{BRANCH}"),
                ("git", "add", "--", REPORT_PATH),
                ("git", "diff", "--cached", "--quiet", "--", REPORT_PATH),
                ("git", "commit", "--quiet", "-m", "docs(tasks): add the report of B46"),
                ("git", "push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}"),
                ("git", "worktree", "remove", "--force", str(self.checkout)),
            ],
        )

    def test_should_remove_its_checkout_from_the_project_when_the_push_fails(self):
        # Arrange
        self.processes.answer(("git", "push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}"), exit_code=1)
        context = self.create_context("github")

        # Act
        with self.assertRaises(CommandFailed):
            publish_task_report(context)

        # Assert
        self.assertEqual(self.processes.list_argvs()[-1], ("git", "worktree", "remove", "--force", str(self.checkout)))
