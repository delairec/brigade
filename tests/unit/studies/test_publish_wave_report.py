import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import CommandFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_started import WaveStarted
from brigade.studies.convert_study import Study
from brigade.studies.publish_wave_report import publish_wave_report
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261022T150000Z-aaaaaa"
BRANCH = "integration/oak_w2"
REPORT_PATH = "corpus/waves/2-report.md"
STUDY = Study(
    name="wave-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    wave="oak_w2",
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

CLI_BOUND_TO_OCTO_CLI = Configuration(forge_accounts={"cli": "octo-cli"})
NOTHING_BOUND = Configuration()


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "REPORT", "name": "oak_w2", "fields": [{"name": "WAVE", "value": "oak_w2"}]}]}


def create_forge() -> ForgeDouble:
    return ForgeDouble(
        {
            "rewrite_pull_request_body": lambda request: {"schema_version": 1},
            "read_login_environment": lambda request: {
                "schema_version": 1,
                "environment": {"octo-cli": {"GH_TOKEN": "cli-token"}}.get(request["login"]),
            },
        }
    )


class PublishWaveReportTest(unittest.TestCase):
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
        append_event(
            self.runtime.paths,
            self.runtime.now,
            WaveStarted(wave="oak_w2", project="oak", branch=BRANCH, tasks=("B17",)),
        )
        self.processes.answer(("git", "fetch", "--quiet", "origin", BRANCH))
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), f"origin/{BRANCH}"))
        self.processes.answer(("git", "switch", "--quiet", "--force-create", BRANCH))
        self.processes.answer(("git", "add", "--", REPORT_PATH))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", REPORT_PATH), exit_code=1)
        self.processes.answer(("git", "commit", "--quiet", "-m", "docs(waves): add the report of oak_w2"))
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH))
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.checkout)))

    def create_context(self, forge: str, configuration: Configuration = NOTHING_BOUND) -> StudyRunContext:
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("FORGE", forge), ("CORPUS", "corpus"))},
        )
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(configuration=configuration, forge=None, forge_name="github"),
            document=DocumentDouble(),
            resolve_forge={"github": self.forge}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id=RUN_ID, run_directory=self.run_directory, equipment=equipment
        )

    def open_integration_pull_request(self) -> None:
        append_event(self.runtime.paths, self.runtime.now, WavePrOpened(wave="oak_w2", pr=181, login="octo-bot"))

    def test_should_write_the_markdown_of_the_report_under_the_corpus_folder_of_the_project(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_wave_report(context)

        # Assert
        self.assertEqual(
            (self.checkout / REPORT_PATH).read_text(encoding="utf-8"), "# REPORT oak_w2\n\n- WAVE: oak_w2\n"
        )

    def test_should_answer_the_report_the_integration_branch_received_and_its_pull_request(self):
        # Arrange
        self.open_integration_pull_request()
        context = self.create_context("github")

        # Act
        published = publish_wave_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": 181})

    def test_should_rewrite_the_body_of_the_integration_pull_request_with_the_report(self):
        # Arrange
        self.open_integration_pull_request()
        context = self.create_context("github")

        # Act
        publish_wave_report(context)

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body"),
            [
                {
                    "repository": str(self.checkout),
                    "number": 181,
                    "body": "# REPORT oak_w2\n\n- WAVE: oak_w2\n",
                    "environment": {},
                }
            ],
        )

    def test_should_fetch_the_integration_branch_as_the_login_bound_to_cli(self):
        # Arrange
        context = self.create_context("github", CLI_BOUND_TO_OCTO_CLI)

        # Act
        publish_wave_report(context)

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
        publish_wave_report(context)

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

    def test_should_rewrite_the_body_of_the_integration_pull_request_as_the_login_bound_to_cli(self):
        # Arrange
        self.open_integration_pull_request()
        context = self.create_context("github", CLI_BOUND_TO_OCTO_CLI)

        # Act
        publish_wave_report(context)

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body")[0]["environment"], {"GH_TOKEN": "cli-token"}
        )

    def test_should_rewrite_no_pull_request_before_the_wave_opened_its_integration_pull_request(self):
        # Arrange
        context = self.create_context("github")

        # Act
        published = publish_wave_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": None})
        self.assertEqual(self.forge.list_requests("rewrite_pull_request_body"), [])

    def test_should_rewrite_no_pull_request_of_a_project_without_a_forge(self):
        # Arrange
        self.open_integration_pull_request()
        context = self.create_context("none")

        # Act
        published = publish_wave_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": None})
        self.assertEqual(self.forge.list_requests("rewrite_pull_request_body"), [])

    def test_should_commit_the_report_on_the_integration_branch_push_it_and_remove_its_checkout(self):
        # Arrange
        context = self.create_context("github")

        # Act
        publish_wave_report(context)

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
                ("git", "commit", "--quiet", "-m", "docs(waves): add the report of oak_w2"),
                ("git", "push", "--quiet", "origin", BRANCH),
                ("git", "worktree", "remove", "--force", str(self.checkout)),
            ],
        )

    def test_should_remove_its_checkout_from_the_project_when_the_push_fails(self):
        # Arrange
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH), exit_code=1)
        context = self.create_context("github")

        # Act
        with self.assertRaises(CommandFailed):
            publish_wave_report(context)

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
                ("git", "commit", "--quiet", "-m", "docs(waves): add the report of oak_w2"),
                ("git", "push", "--quiet", "origin", BRANCH),
                ("git", "worktree", "remove", "--force", str(self.checkout)),
            ],
        )
