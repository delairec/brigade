import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext
from brigade.studies.write_answer_to_pull_request import write_answer_to_pull_request
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
HEAD_BRANCH = "feature/S1-empty-the-cart"
RELATIVE_PATH = "docs/usage-reports/12.md"
PUSH_TO_THE_HEAD = ("git", "push", "--quiet", "origin", f"HEAD:refs/heads/{HEAD_BRANCH}")
PUBLICATION = AnswerPublication(title=f"Study usage, run {RUN_ID}", markdown="# RESULT usage_1\n")
STUDY = Study(
    name="pr_usage_report_20261019T090000Z",
    project="oak",
    question=None,
    collectors=(),
    slot="judging",
    every=None,
    output=f"pr-file:12:{RELATIVE_PATH}",
    answer_type="RESULT",
    status="active",
)
CLI_BOUND_TO_OCTO_CLI = Configuration(forge_accounts={"cli": "octo-cli"})


def create_forge() -> ForgeDouble:
    return ForgeDouble(
        {
            "read_pull_request": lambda request: {
                "schema_version": 1,
                "pull_request": {"number": 12, "head": HEAD_BRANCH, "head_sha": "3a3a3a3"},
            },
            "read_login_environment": lambda request: {
                "schema_version": 1,
                "environment": {"octo-cli": {"GH_TOKEN": "cli-token"}}.get(request["login"]),
            },
        }
    )


class WriteAnswerToPullRequestTest(unittest.TestCase):
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
        self.processes.answer(("git", "fetch", "--quiet", "origin", HEAD_BRANCH))
        self.processes.answer(
            (
                "git",
                "worktree",
                "add",
                "--quiet",
                "--detach",
                "--lock",
                "--reason",
                "brigade writing an answer on a pull request",
                str(self.checkout),
                f"origin/{HEAD_BRANCH}",
            )
        )
        self.processes.answer(("git", "add", "--", RELATIVE_PATH))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", RELATIVE_PATH), exit_code=1)
        self.processes.answer(
            ("git", "commit", "--quiet", "-m", f"docs(reports): add the answer of {STUDY.name}, run {RUN_ID}")
        )
        self.processes.answer(PUSH_TO_THE_HEAD)
        self.processes.answer(("git", "worktree", "remove", "--force", "--force", str(self.checkout)))

    def create_context(self, forge: str) -> StudyRunContext:
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", forge))}
        )
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(
                configuration=CLI_BOUND_TO_OCTO_CLI, forge=None, forge_name="github", resolve_client=None
            ),
            resolve_forge={"github": self.forge}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id=RUN_ID, run_directory=self.run_directory, equipment=equipment
        )

    def test_should_answer_the_head_branch_of_the_pull_request_the_answer_was_committed_on(self):
        # Act
        written = write_answer_to_pull_request(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertEqual(written, {"branch": HEAD_BRANCH, "pull_request": 12})

    def test_should_write_the_markdown_of_the_answer_at_the_path_of_the_output(self):
        # Act
        write_answer_to_pull_request(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertEqual((self.checkout / RELATIVE_PATH).read_text(encoding="utf-8"), "# RESULT usage_1\n")

    def test_should_push_the_commit_to_the_head_branch_as_the_login_bound_to_cli(self):
        # Act
        write_answer_to_pull_request(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertIn(
            ProcessRequest(
                argv=PUSH_TO_THE_HEAD, cwd=str(self.checkout), timeout_s=120.0, environment={"GH_TOKEN": "cli-token"}
            ),
            self.processes.requests,
        )

    def test_should_refuse_a_project_without_forge(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            write_answer_to_pull_request(self.create_context("none"), PUBLICATION)

        # Assert
        self.assertEqual(
            str(raised.exception), f"the output pr-file:12:{RELATIVE_PATH} needs a project with a forge"
        )

