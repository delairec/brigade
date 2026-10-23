import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.convert_study import Study
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext
from brigade.studies.write_answer_to_file import write_answer_to_file
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
BRANCH = f"brigade/study-trees-{RUN_ID}"
RELATIVE_PATH = f"docs/studies/{RUN_ID}.md"
FORCED_PUSH = ("git", "push", "--quiet", "--force", "origin", BRANCH)
PUBLICATION = AnswerPublication(title=f"Study trees, run {RUN_ID}", markdown="# FINDING trees_1\n")
STUDY = Study(
    name="trees",
    project="oak",
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="file:docs/studies/{run}.md",
    answer_type="FINDING",
    status="active",
)
CLI_BOUND_TO_OCTO_CLI = Configuration(forge_accounts={"cli": "octo-cli"})
NOTHING_BOUND = Configuration()


class ForgeDouble:
    def __init__(self):
        self.opened = []

    def open_pull_request(self, request: dict, runtime) -> dict:
        self.opened.append(request)
        return {"number": 7, "url": "https://github.com/acme/oak/pull/7"}

    def read_login_environment(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "environment": {"octo-cli": {"GH_TOKEN": "cli-token"}}.get(request["login"])}


class WriteAnswerToFileTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.checkout = self.run_directory / "checkout"
        self.forge = ForgeDouble()
        message = f"docs(studies): add the answer of trees, run {RUN_ID}"
        self.processes.answer(
            ("git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"), "origin/main\n"
        )
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), "main"))
        self.processes.answer(("git", "switch", "--quiet", "--force-create", BRANCH))
        self.processes.answer(("git", "add", "--", RELATIVE_PATH))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", RELATIVE_PATH), exit_code=1)
        self.processes.answer(("git", "commit", "--quiet", "-m", message))
        self.processes.answer(FORCED_PUSH)
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.checkout)))

    def create_context(self, forge: str, configuration: Configuration = NOTHING_BOUND) -> StudyRunContext:
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", forge))}
        )
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(configuration=configuration, forge=None, forge_name="github"),
            resolve_forge={"github": self.forge}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id=RUN_ID, run_directory=self.run_directory, equipment=equipment
        )

    def test_should_answer_the_branch_and_the_pull_request_of_the_answer(self):
        # Act
        written = write_answer_to_file(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertEqual(written, {"branch": BRANCH, "pull_request": "https://github.com/acme/oak/pull/7"})

    def test_should_open_the_pull_request_of_the_answer_on_the_main_branch(self):
        # Act
        write_answer_to_file(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertEqual(
            self.forge.opened,
            [
                {
                    "repository": str(self.checkout),
                    "base": "main",
                    "branch": BRANCH,
                    "title": f"Study trees, run {RUN_ID}",
                    "body": "# FINDING trees_1\n",
                    "milestone": None,
                    "environment": {},
                }
            ],
        )

    def test_should_push_the_branch_of_the_answer_as_the_login_bound_to_cli(self):
        # Act
        write_answer_to_file(self.create_context("github", CLI_BOUND_TO_OCTO_CLI), PUBLICATION)

        # Assert
        self.assertIn(
            ProcessRequest(
                argv=FORCED_PUSH, cwd=str(self.checkout), timeout_s=120.0, environment={"GH_TOKEN": "cli-token"}
            ),
            self.processes.requests,
        )

    def test_should_open_the_pull_request_of_the_answer_as_the_login_bound_to_cli(self):
        # Act
        write_answer_to_file(self.create_context("github", CLI_BOUND_TO_OCTO_CLI), PUBLICATION)

        # Assert
        self.assertEqual(self.forge.opened[0]["environment"], {"GH_TOKEN": "cli-token"})

    def test_should_write_the_answer_at_the_path_the_output_names_for_the_run(self):
        # Act
        write_answer_to_file(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertEqual((self.checkout / RELATIVE_PATH).read_text(encoding="utf-8"), "# FINDING trees_1\n")

    def test_should_answer_no_pull_request_for_a_project_without_a_forge(self):
        # Act
        written = write_answer_to_file(self.create_context("none"), PUBLICATION)

        # Assert
        self.assertEqual(written, {"branch": BRANCH, "pull_request": None})

    def test_should_keep_the_branch_of_a_project_without_a_forge_local(self):
        # Act
        write_answer_to_file(self.create_context("none"), PUBLICATION)

        # Assert
        self.assertNotIn(FORCED_PUSH, self.processes.list_argvs())

    def test_should_remove_the_checkout_once_the_answer_is_committed(self):
        # Act
        write_answer_to_file(self.create_context("github"), PUBLICATION)

        # Assert
        self.assertEqual(self.processes.list_argvs()[-1], ("git", "worktree", "remove", "--force", str(self.checkout)))
