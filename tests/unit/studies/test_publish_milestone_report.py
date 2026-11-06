import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import CommandFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_pr_described import MilestonePrDescribed
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.read_ledger import read_ledger
from brigade.studies.convert_study import Study
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.publish_milestone_report import publish_milestone_report
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261022T150000Z-aaaaaa"
BRANCH = "integration/hardening"
REPORT_PATH = "corpus/milestones/M6-report.md"
MILESTONES_PATH = "corpus/milestones.awawa"
MILESTONE_M6_ACTIVE = 'MILESTONE M6\n\tTITLE "Hardening"\n\tSTATUS active\n'
REACHED_MESSAGE = "docs(corpus): mark @MILESTONE.M6 reached"
MARKDOWN = "# REPORT oak_M6\n\n- MILESTONE: M6\n"
STUDY = Study(
    name="milestone-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    milestone=MilestoneReportOrder(project="oak", milestone="M6", branch=BRANCH, waves=("oak_w2",), tasks=("B17",)),
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

CLI_BOUND_TO_OCTO_CLI = Configuration(forge_accounts={"cli": "octo-cli"})
NOTHING_BOUND = Configuration()


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "REPORT", "name": "oak_M6", "fields": [{"name": "MILESTONE", "value": "M6"}]}]}


def answer_opened_pull_request(request: dict) -> dict:
    return {"schema_version": 1, "url": "https://github.com/octo/oak/pull/190", "number": 190}


def create_forge(open_pull_request: Callable[[dict], dict] = answer_opened_pull_request) -> ForgeDouble:
    return ForgeDouble(
        {
            "rewrite_pull_request_body": lambda request: {"schema_version": 1},
            "open_pull_request": open_pull_request,
            "describe_account": lambda request: {"schema_version": 1, "login": "octo-cli"},
            "read_pull_request": lambda request: {
                "schema_version": 1,
                "pull_request": {
                    "number": 341,
                    "title": "feat(tick): open the pull request of a milestone (@TASK.B17)",
                },
            },
            "read_login_environment": lambda request: {
                "schema_version": 1,
                "environment": {"octo-cli": {"GH_TOKEN": "cli-token"}}.get(request["login"]),
            },
        }
    )


class PublishMilestoneReportTest(unittest.TestCase):
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
        self.processes.answer(("git", "switch", "--quiet", "--force-create", BRANCH))
        self.processes.answer(("git", "add", "--", REPORT_PATH))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", REPORT_PATH), exit_code=1)
        self.processes.answer(("git", "commit", "--quiet", "-m", "docs(milestones): add the report of M6"))
        self.processes.answer_json(
            ("awawa", "show", "@MILESTONE.M6", "--json", str(self.checkout)),
            {"file": str(self.checkout / MILESTONES_PATH)},
        )
        self.processes.answer_corpus_change(self.checkout, (MILESTONES_PATH,), REACHED_MESSAGE)
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH))
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.checkout)))
        (self.checkout / "corpus").mkdir(parents=True)
        (self.checkout / MILESTONES_PATH).write_text(MILESTONE_M6_ACTIVE, encoding="utf-8")
        self.processes.answer(("git", "rev-parse", "HEAD"), stdout="8885daa\n")
        self.processes.answer_entities(
            self.checkout,
            "TASK",
            {"B17": (("TYPE", "feat"), ("COMPONENT", "tick"), ("MILESTONE", "@MILESTONE.M6"), ("DELIVERED_BY", "341"))},
            ("STATUS==implemented",),
        )

    def create_context(self, forge: str, configuration: Configuration = NOTHING_BOUND) -> StudyRunContext:
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("FORGE", forge), ("CORPUS", "corpus"), ("MAIN", "main"))},
        )
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(
                configuration=configuration, forge=None, forge_name="github", resolve_client=None
            ),
            document=DocumentDouble(),
            resolve_forge={"github": self.forge}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id=RUN_ID, run_directory=self.run_directory, equipment=equipment
        )

    def open_milestone_pull_request(self) -> None:
        append_event(
            self.runtime.paths,
            self.runtime.now,
            MilestonePrOpened(project="oak", milestone="M6", pr=181, login="octo-cli"),
        )

    def test_should_write_the_markdown_of_the_report_under_the_corpus_folder_of_the_project(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual((self.checkout / REPORT_PATH).read_text(encoding="utf-8"), MARKDOWN)

    def test_should_answer_the_report_the_milestone_branch_received_and_the_pull_request_it_opened(self):
        # Arrange
        context = self.create_context("github")

        # Act
        published = publish_milestone_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": 190})

    def test_should_open_the_pull_request_of_the_milestone_into_main_with_the_report_as_its_body(self):
        # Arrange
        context = self.create_context("github", CLI_BOUND_TO_OCTO_CLI)

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            self.forge.list_requests("open_pull_request"),
            [
                {
                    "repository": "/srv/oak",
                    "base": "main",
                    "branch": BRANCH,
                    "title": "feat(tick): open the pull request of a milestone (M6, @TASK.B17)",
                    "body": MARKDOWN,
                    "milestone": None,
                    "environment": {"GH_TOKEN": "cli-token"},
                }
            ],
        )

    def test_should_record_the_pull_request_of_the_milestone_with_the_login_bound_to_cli(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            read_ledger(self.runtime.paths.state_root).entries[0].event,
            MilestonePrOpened(project="oak", milestone="M6", pr=190, login="octo-cli"),
        )

    def test_should_record_the_head_it_described_the_pull_request_of_the_milestone_at_after_its_opening(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            read_ledger(self.runtime.paths.state_root).entries[-1].event,
            MilestonePrDescribed(project="oak", milestone="M6", pr=190, head="8885daa", login="octo-cli"),
        )

    def test_should_open_no_second_pull_request_once_the_milestone_opened_one(self):
        # Arrange
        self.open_milestone_pull_request()
        context = self.create_context("github")

        # Act
        published = publish_milestone_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": 181})
        self.assertEqual(self.forge.list_requests("open_pull_request"), [])

    def test_should_rewrite_the_body_of_the_pull_request_the_milestone_opened_with_the_report(self):
        # Arrange
        self.open_milestone_pull_request()
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body"),
            [
                {
                    "repository": str(self.checkout),
                    "number": 181,
                    "body": MARKDOWN,
                    "environment": {},
                }
            ],
        )

    def test_should_fetch_the_milestone_branch_as_the_login_bound_to_cli(self):
        # Arrange
        context = self.create_context("github", CLI_BOUND_TO_OCTO_CLI)

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertIn(
            ProcessRequest(
                argv=("git", "fetch", "--quiet", "origin", BRANCH),
                cwd="/srv/oak",
                timeout_s=120.0,
                environment={"GH_TOKEN": "cli-token"},
            ),
            self.processes.requests,
        )

    def test_should_push_the_report_as_the_login_bound_to_cli(self):
        # Arrange
        context = self.create_context("github", CLI_BOUND_TO_OCTO_CLI)

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertIn(
            ProcessRequest(
                argv=("git", "push", "--quiet", "origin", BRANCH),
                cwd=str(self.checkout),
                timeout_s=120.0,
                environment={"GH_TOKEN": "cli-token"},
            ),
            self.processes.requests,
        )

    def test_should_rewrite_the_body_of_the_pull_request_the_milestone_opened_as_the_login_bound_to_cli(self):
        # Arrange
        self.open_milestone_pull_request()
        context = self.create_context("github", CLI_BOUND_TO_OCTO_CLI)

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body"),
            [
                {
                    "repository": str(self.checkout),
                    "number": 181,
                    "body": MARKDOWN,
                    "environment": {"GH_TOKEN": "cli-token"},
                }
            ],
        )

    def test_should_open_no_pull_request_on_a_project_without_a_forge(self):
        # Arrange
        context = self.create_context("none")

        # Act
        published = publish_milestone_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": None})
        self.assertEqual(self.forge.list_operations(), [])

    def test_should_commit_the_report_then_the_reached_milestone_on_its_branch_push_both_and_remove_its_checkout(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            self.processes.list_argvs(),
            [
                ("awawa", "status", "PROJECT", "--json", str(self.runtime.paths.config_root)),
                ("awawa", "show", "@PROJECT.oak", "--json", str(self.runtime.paths.config_root)),
                ("awawa", "status", "PROJECT", "--json", str(self.runtime.paths.config_root)),
                ("awawa", "show", "@PROJECT.oak", "--json", str(self.runtime.paths.config_root)),
                ("git", "fetch", "--quiet", "origin", BRANCH),
                ("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), f"origin/{BRANCH}"),
                ("git", "switch", "--quiet", "--force-create", BRANCH),
                ("git", "add", "--", REPORT_PATH),
                ("git", "diff", "--cached", "--quiet", "--", REPORT_PATH),
                ("git", "commit", "--quiet", "-m", "docs(milestones): add the report of M6"),
                ("awawa", "show", "@MILESTONE.M6", "--json", str(self.checkout)),
                ("awawa", "fmt", str(self.checkout / MILESTONES_PATH)),
                ("awawa", "lint", "--strict", str(self.checkout)),
                ("git", "add", "--", MILESTONES_PATH),
                ("git", "diff", "--cached", "--quiet", "--", MILESTONES_PATH),
                ("git", "commit", "--quiet", "-m", REACHED_MESSAGE),
                ("git", "push", "--quiet", "origin", BRANCH),
                ("awawa", "status", "TASK", "--where", "STATUS==implemented", "--json", str(self.checkout)),
                ("awawa", "show", "@TASK.B17", "--json", str(self.checkout)),
                ("git", "rev-parse", "HEAD"),
                ("git", "worktree", "remove", "--force", str(self.checkout)),
            ],
        )

    def test_should_open_the_pull_request_of_the_milestone_once_the_reached_milestone_is_pushed_on_its_branch(self):
        # Arrange
        processes_before_opening = []

        def open_pull_request(request: dict) -> dict:
            processes_before_opening.extend(self.processes.list_argvs())
            return answer_opened_pull_request(request)

        self.forge = create_forge(open_pull_request)
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            processes_before_opening[-4:],
            [
                ("git", "commit", "--quiet", "-m", REACHED_MESSAGE),
                ("git", "push", "--quiet", "origin", BRANCH),
                ("awawa", "status", "TASK", "--where", "STATUS==implemented", "--json", str(self.checkout)),
                ("awawa", "show", "@TASK.B17", "--json", str(self.checkout)),
            ],
        )

    def test_should_remove_its_checkout_from_the_project_when_the_push_fails(self):
        # Arrange
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH), exit_code=1)
        context = self.create_context("github")

        # Act
        with self.assertRaises(CommandFailed):
            publish_milestone_report(context)

        # Assert
        self.assertEqual(
            self.processes.list_argvs(),
            [
                ("awawa", "status", "PROJECT", "--json", str(self.runtime.paths.config_root)),
                ("awawa", "show", "@PROJECT.oak", "--json", str(self.runtime.paths.config_root)),
                ("awawa", "status", "PROJECT", "--json", str(self.runtime.paths.config_root)),
                ("awawa", "show", "@PROJECT.oak", "--json", str(self.runtime.paths.config_root)),
                ("git", "fetch", "--quiet", "origin", BRANCH),
                ("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), f"origin/{BRANCH}"),
                ("git", "switch", "--quiet", "--force-create", BRANCH),
                ("git", "add", "--", REPORT_PATH),
                ("git", "diff", "--cached", "--quiet", "--", REPORT_PATH),
                ("git", "commit", "--quiet", "-m", "docs(milestones): add the report of M6"),
                ("awawa", "show", "@MILESTONE.M6", "--json", str(self.checkout)),
                ("awawa", "fmt", str(self.checkout / MILESTONES_PATH)),
                ("awawa", "lint", "--strict", str(self.checkout)),
                ("git", "add", "--", MILESTONES_PATH),
                ("git", "diff", "--cached", "--quiet", "--", MILESTONES_PATH),
                ("git", "commit", "--quiet", "-m", REACHED_MESSAGE),
                ("git", "push", "--quiet", "origin", BRANCH),
                ("git", "worktree", "remove", "--force", str(self.checkout)),
            ],
        )

    def test_should_mark_the_milestone_reached_in_the_corpus_at_its_branch(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertEqual(
            (self.checkout / MILESTONES_PATH).read_text(encoding="utf-8"),
            'MILESTONE M6\n\tTITLE "Hardening"\n\tSTATUS reached\n',
        )

    def test_should_commit_the_reached_milestone_on_its_branch_on_a_project_without_a_forge(self):
        # Arrange
        context = self.create_context("none")

        # Act
        publish_milestone_report(context)

        # Assert
        self.assertIn(("git", "commit", "--quiet", "-m", REACHED_MESSAGE), self.processes.list_argvs())
