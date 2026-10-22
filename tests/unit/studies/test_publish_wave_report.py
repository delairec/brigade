import tempfile
import unittest
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_started import WaveStarted
from brigade.studies.convert_study import Study
from brigade.studies.publish_wave_report import publish_wave_report
from brigade.studies.study_run_context import StudyRunContext
from tests.unit.create_scripted_runtime import create_scripted_runtime
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


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "REPORT", "name": "oak_w2", "fields": [{"name": "WAVE", "value": "oak_w2"}]}]}


class ForgeDouble:
    def __init__(self):
        self.rewritten = []

    def rewrite_pull_request_body(self, request: dict, runtime) -> dict:
        self.rewritten.append(request)
        return {"schema_version": 1}


class PublishWaveReportTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.checkout = self.run_directory / "checkout"
        self.forge = ForgeDouble()
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

    def create_context(self, forge: str) -> StudyRunContext:
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("FORGE", forge), ("CORPUS", "corpus"))},
        )
        equipment = create_study_equipment(document=DocumentDouble(), resolve_forge={"github": self.forge}.__getitem__)
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
            self.forge.rewritten,
            [
                {
                    "repository": str(self.checkout),
                    "number": 181,
                    "body": "# REPORT oak_w2\n\n- WAVE: oak_w2\n",
                    "environment": {},
                }
            ],
        )

    def test_should_rewrite_no_pull_request_before_the_wave_opened_its_integration_pull_request(self):
        # Arrange
        context = self.create_context("github")

        # Act
        published = publish_wave_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": None})
        self.assertEqual(self.forge.rewritten, [])

    def test_should_rewrite_no_pull_request_of_a_project_without_a_forge(self):
        # Arrange
        self.open_integration_pull_request()
        context = self.create_context("none")

        # Act
        published = publish_wave_report(context)

        # Assert
        self.assertEqual(published, {"report": REPORT_PATH, "branch": BRANCH, "pull_request": None})
        self.assertEqual(self.forge.rewritten, [])

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
