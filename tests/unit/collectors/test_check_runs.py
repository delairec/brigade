import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.check_runs import collect
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

TESTS_JOB = "https://github.com/octo/oak/actions/runs/7/job/70"
FAILED_TESTS = {
    "pull_request": 12,
    "branch": "task/oak_w1/B3",
    "head": "0123abc",
    "name": "tests",
    "conclusion": "failure",
    "link": TESTS_JOB,
}
PASSED_LINT = {
    "pull_request": 12,
    "branch": "task/oak_w1/B3",
    "head": "0123abc",
    "name": "lint",
    "conclusion": "success",
    "link": "https://github.com/octo/oak/actions/runs/7/job/71",
}
TIMED_OUT_BUILD_ON_MAIN = {
    "pull_request": None,
    "branch": "main",
    "head": "4567def",
    "name": "build",
    "conclusion": "timed_out",
    "link": "https://ci.example.com/build/9",
}
TESTS_STEPS = [
    {"name": "Set up job", "conclusion": "success"},
    {"name": "Run tests", "conclusion": "failure"},
    {"name": "Upload report", "conclusion": "failure"},
]
STEPS_BY_JOB_LINK = {TESTS_JOB: TESTS_STEPS}
NO_JOB = None
CONCLUSIONS_AND_FAILING_COUNTS = [
    ("failure", 1),
    ("timed_out", 1),
    ("startup_failure", 1),
    ("success", 0),
    ("cancelled", 0),
    ("skipped", 0),
    ("neutral", 0),
    ("action_required", 0),
    ("pending", 0),
]


def create_environment() -> dict:
    return {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": "{}"}


def create_forge(check_runs: list[dict], steps_by_link: dict = STEPS_BY_JOB_LINK) -> ForgeDouble:
    return ForgeDouble(
        {
            "list_check_runs": lambda request: {"schema_version": 1, "check_runs": check_runs},
            "read_job_steps": lambda request: {
                "schema_version": 1,
                "steps": steps_by_link.get(request["link"], NO_JOB),
            },
        }
    )


class CheckRunsCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def register_project(self, forge: str) -> None:
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"), ("FORGE", forge))},
        )

    def create_equipment(self, forge: ForgeDouble) -> CollectorEquipment:
        return CollectorEquipment(configuration=Configuration(), forge=forge, forge_name="github")

    def test_should_list_the_failing_check_runs_with_their_first_failing_step(self):
        # Arrange
        self.register_project("github")
        forge = create_forge([FAILED_TESTS, PASSED_LINT, TIMED_OUT_BUILD_ON_MAIN])

        # Act
        document = collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "check-runs",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"12": 1, "main": 1},
                "items": [
                    {
                        "pull_request": 12,
                        "branch": "task/oak_w1/B3",
                        "head": "0123abc",
                        "name": "tests",
                        "conclusion": "failure",
                        "link": "https://github.com/octo/oak/actions/runs/7/job/70",
                        "first_failing_step": "Run tests",
                    },
                    {
                        "pull_request": None,
                        "branch": "main",
                        "head": "4567def",
                        "name": "build",
                        "conclusion": "timed_out",
                        "link": "https://ci.example.com/build/9",
                        "first_failing_step": None,
                    },
                ],
            },
        )

    def test_should_take_as_failing_a_check_run_that_failed_timed_out_or_failed_to_start(self):
        for conclusion, expected_count in CONCLUSIONS_AND_FAILING_COUNTS:
            with self.subTest(conclusion=conclusion):
                # Arrange
                self.register_project("github")
                forge = create_forge([{**TIMED_OUT_BUILD_ON_MAIN, "conclusion": conclusion}])

                # Act
                document = collect(create_environment(), self.runtime, self.create_equipment(forge))

                # Assert
                self.assertEqual(len(document["items"]), expected_count)

    def test_should_ask_the_forge_for_the_check_runs_of_the_main_branch_with_no_account_bound_by_default(self):
        # Arrange
        self.register_project("github")
        no_check_runs: list[dict] = []
        forge = create_forge(no_check_runs)

        # Act
        collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("list_check_runs"),
            [{"schema_version": 1, "repository": "/srv/oak", "branch": "main", "environment": {}}],
        )

    def test_should_read_the_steps_of_the_job_each_failing_check_run_links_to(self):
        # Arrange
        self.register_project("github")
        forge = create_forge([FAILED_TESTS, PASSED_LINT])

        # Act
        collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("read_job_steps"),
            [
                {
                    "schema_version": 1,
                    "repository": "/srv/oak",
                    "link": "https://github.com/octo/oak/actions/runs/7/job/70",
                    "environment": {},
                }
            ],
        )

    def test_should_name_no_first_failing_step_of_a_job_whose_steps_all_passed(self):
        # Arrange
        self.register_project("github")
        passed_steps = [{"name": "Run tests", "conclusion": "success"}]
        forge = create_forge([FAILED_TESTS], {TESTS_JOB: passed_steps})

        # Act
        document = collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertIsNone(document["items"][0]["first_failing_step"])

    def test_should_be_absent_from_a_project_with_no_forge(self):
        # Arrange
        self.register_project("none")
        no_check_runs: list[dict] = []
        forge = create_forge(no_check_runs)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(str(refusal.exception), "check-runs is absent: FORGE none")
