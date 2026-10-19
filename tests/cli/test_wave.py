import json
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.run_test_case import FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject

REQUEST_TEXT = "let the customer empty the cart in one click"
PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n"
    "\t\tREQUIRED\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD DELIVERED_BY uint\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running|delivered\n"
    "\t\tREQUIRED\n"
)
MAIN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n'
WAVE_TASKS = (
    "TASK S2\n"
    '\tTITLE "Remove an item from the cart"\n'
    "\tSTATUS implemented\n"
    "\n"
    "TASK S3\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS todo\n"
    "\tMILESTONE @MILESTONE.M1\n"
    "\n"
    "TASK S4\n"
    '\tTITLE "Confirm before emptying the cart"\n'
    "\tSTATUS implemented\n"
    "\tMILESTONE @MILESTONE.M1\n"
    "\tDELIVERED_BY 12\n"
)
WAVE_MILESTONES = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS planned\n'
WAVE_BRANCH = "integration/M1-empty-cart"
PLANNED_REQUEST = (
    "REQUEST shop_1\n"
    "\tPROJECT @PROJECT.shop\n"
    f'\tTEXT "{REQUEST_TEXT}"\n'
    '\tCREATED_AT "2026-10-12T09:30:00Z"\n'
    "\tSTATUS planned\n"
    '\tMILESTONE "M1"\n'
    f'\tBRANCH "{WAVE_BRANCH}"\n'
)
RUNNING_REQUEST = (
    "REQUEST shop_1\n"
    "\tPROJECT @PROJECT.shop\n"
    f'\tTEXT "{REQUEST_TEXT}"\n'
    '\tCREATED_AT "2026-10-12T09:30:00Z"\n'
    "\tSTATUS running\n"
    '\tMILESTONE "M1"\n'
    f'\tBRANCH "{WAVE_BRANCH}"\n'
)
PLANNING_REQUEST = (
    "REQUEST shop_2\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "show the total of the cart"\n'
    '\tCREATED_AT "2026-10-13T14:00:00Z"\n'
    "\tSTATUS planning\n"
)
WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3", "S4"]}}\n'
)
WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3", "S4"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "queued"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "running"}\n'
    '{"schema_version": 2, "ts": "2026-10-13T11:30:00Z", "event": "wave.started", "wave": "cafe_w1",'
    f' "project": "cafe", "branch": "{WAVE_BRANCH}", "tasks": ["S3"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T12:00:00Z", "event": "task.state", "wave": "cafe_w1", "task": "S3",'
    ' "state": "merged"}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:10:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T110000Z-a00001", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "main_steps": 50, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:20:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T121500Z-a00002", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:30:00Z", "event": "run.finished", "wave": "cafe_w1", "task": "S3",'
    ' "run": "20261013T122500Z-a00003", "client": "fake", "project": "cafe", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
)
ASKING_POLICY = "POLICY shop_review\n\tPROJECT @PROJECT.shop\n\tPLAN_REVIEW ask\n"


class WaveTestCase(FileWaitingTestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.run_init()
        self.project = TemporaryProject(
            root / "projects" / "shop", {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        )
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", MAIN_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.runs = self.machine.state_home / "brigade" / "runs"
        self.ledger = self.machine.state_home / "brigade" / "ledger"

    def tearDown(self):
        self.root.cleanup()

    def run_wave(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", *arguments)

    def write_requests(self, requests: str) -> None:
        (self.machine.corpus / "requests.awawa").write_text(requests)

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted(self.ledger.glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def cut_wave_branch(self, tasks: str = WAVE_TASKS) -> None:
        self.project.run_git("checkout", "--quiet", "-b", WAVE_BRANCH)
        self.project.write("corpus/tasks.awawa", tasks)
        self.project.write("corpus/milestones.awawa", WAVE_MILESTONES)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of M1")
        self.project.run_git("checkout", "--quiet", "main")


class BrigadeWaveShowTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        self.cut_wave_branch()
        self.write_requests(f"{RUNNING_REQUEST}\n{PLANNING_REQUEST}")
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(WAVE_EVENTS)

    def test_should_print_the_request_and_the_tasks_of_its_wave_with_their_states(self):
        # Act
        completed = self.run_wave("show", "shop_1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "request": "shop_1",
                "project": "shop",
                "text": REQUEST_TEXT,
                "status": "running",
                "wave": "shop_w1",
                "milestone": "M1",
                "branch": WAVE_BRANCH,
                "created_at": "2026-10-12T09:30:00Z",
                "waits_for": None,
                "tasks": [
                    {
                        "task": "S3",
                        "title": "Empty the cart in one click",
                        "state": "running",
                        "run": "20261013T121500Z-a00002",
                        "pull_request": None,
                    },
                    {
                        "task": "S4",
                        "title": "Confirm before emptying the cart",
                        "state": "queued",
                        "run": None,
                        "pull_request": 12,
                    },
                ],
            },
        )

    def test_should_print_that_a_planned_request_waits_for_wave_start_under_plan_review_ask(self):
        # Arrange
        self.write_requests(PLANNED_REQUEST)
        (self.machine.corpus / "policies.awawa").write_text(ASKING_POLICY)

        # Act
        completed = self.run_wave("show", "shop_1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["waits_for"], "brigade wave start")

    def test_should_print_a_planning_request_without_a_wave(self):
        # Act
        completed = self.run_wave("show", "shop_2", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "request": "shop_2",
                "project": "shop",
                "text": "show the total of the cart",
                "status": "planning",
                "wave": None,
                "milestone": None,
                "branch": None,
                "created_at": "2026-10-13T14:00:00Z",
                "waits_for": None,
                "tasks": [],
            },
        )

    def test_should_print_the_request_and_its_tasks_as_text(self):
        # Act
        completed = self.run_wave("show", "shop_1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "@REQUEST.shop_1 of @PROJECT.shop  running\n"
            f"{REQUEST_TEXT}\n"
            "wave        shop_w1\n"
            "milestone   M1\n"
            f"branch      {WAVE_BRANCH}\n"
            "created at  2026-10-12T09:30:00Z\n"
            "waits for   -\n"
            "\n"
            "task  state    run                      pull request  title\n"
            "S3    running  20261013T121500Z-a00002  -             Empty the cart in one click\n"
            "S4    queued                            12            Confirm before emptying the cart\n",
        )

    def test_should_read_the_tasks_with_the_root_of_the_project_tree_as_the_awawa_workspace(self):
        # Arrange
        sha = self.project.run_git("rev-parse", WAVE_BRANCH).strip()
        tree = self.machine.cache_home / "brigade" / "refs" / "shop" / sha

        # Act
        completed = self.run_wave("show", "shop_1", "--verbose")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            f"brigade wave show: ran awawa status TASK --where MILESTONE==@MILESTONE.M1 --json {tree},",
            completed.stderr,
        )

    def test_should_exit_1_naming_a_request_the_operational_corpus_does_not_define(self):
        # Act
        completed = self.run_wave("show", "shop_9")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave show: @REQUEST.shop_9 is not defined in the operational corpus\n"),
        )


class BrigadeWaveShowOfAProjectWithoutACorpusTest(WaveTestCase):
    def test_should_exit_1_naming_the_project(self):
        # Arrange
        cafe = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "cafe", self.machine.describe_environment()
        )
        cafe.write("README.md", "# cafe\n")
        cafe.track("README.md")
        cafe.run_git("commit", "--quiet", "-m", "the readme")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(cafe.path))
        self.write_requests(
            "REQUEST cafe_1\n"
            "\tPROJECT @PROJECT.cafe\n"
            '\tTEXT "print the receipt"\n'
            '\tCREATED_AT "2026-10-14T07:15:00Z"\n'
            "\tSTATUS planned\n"
            '\tMILESTONE "M1"\n'
            f'\tBRANCH "{WAVE_BRANCH}"\n'
        )

        # Act
        completed = self.run_wave("show", "cafe_1")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr), (1, "brigade wave show: @PROJECT.cafe declares no corpus\n")
        )


class BrigadeWaveListTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        cafe = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "cafe", self.machine.describe_environment()
        )
        cafe.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        cafe.track("corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(cafe.path))
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(WAVE_STARTED)
        self.write_requests(
            f"{RUNNING_REQUEST}\n{PLANNING_REQUEST}\n"
            "REQUEST cafe_1\n"
            "\tPROJECT @PROJECT.cafe\n"
            '\tTEXT "print the receipt"\n'
            '\tCREATED_AT "2026-10-14T07:15:00Z"\n'
            "\tSTATUS planning\n"
        )

    def test_should_print_one_row_per_request(self):
        # Act
        completed = self.run_wave("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "requests": [
                    {
                        "name": "cafe_1",
                        "project": "cafe",
                        "status": "planning",
                        "wave": None,
                        "milestone": None,
                        "branch": None,
                        "created_at": "2026-10-14T07:15:00Z",
                    },
                    {
                        "name": "shop_1",
                        "project": "shop",
                        "status": "running",
                        "wave": "shop_w1",
                        "milestone": "M1",
                        "branch": WAVE_BRANCH,
                        "created_at": "2026-10-12T09:30:00Z",
                    },
                    {
                        "name": "shop_2",
                        "project": "shop",
                        "status": "planning",
                        "wave": None,
                        "milestone": None,
                        "branch": None,
                        "created_at": "2026-10-13T14:00:00Z",
                    },
                ],
            },
        )

    def test_should_narrow_the_rows_to_one_project(self):
        # Act
        completed = self.run_wave("list", "--project", "cafe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["requests"],
            [
                {
                    "name": "cafe_1",
                    "project": "cafe",
                    "status": "planning",
                    "wave": None,
                    "milestone": None,
                    "branch": None,
                    "created_at": "2026-10-14T07:15:00Z",
                }
            ],
        )

    def test_should_print_the_rows_as_text(self):
        # Act
        completed = self.run_wave("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "request  project  status    wave     milestone  branch                     created at\n"
            "cafe_1   cafe     planning  -        -          -                          2026-10-14T07:15:00Z\n"
            f"shop_1   shop     running   shop_w1  M1         {WAVE_BRANCH}  2026-10-12T09:30:00Z\n"
            "shop_2   shop     planning  -        -          -                          2026-10-13T14:00:00Z\n",
        )


class BrigadeWaveListWithoutRequestsTest(WaveTestCase):
    def test_should_print_no_row(self):
        # Act
        completed = self.run_wave("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"schema_version": 1, "requests": []})


class BrigadeWaveBeforeInitTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())

    def tearDown(self):
        self.root.cleanup()

    def test_should_exit_1_naming_brigade_init(self):
        for arguments, expected_stderr in [
            (("show", "shop_1"), "brigade wave show: the operational corpus is missing; run brigade init first\n"),
            (("list",), "brigade wave list: the operational corpus is missing; run brigade init first\n"),
        ]:
            with self.subTest(arguments=arguments):
                # Act
                completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", *arguments)

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, expected_stderr))
