import json
import tempfile
import time
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, FILE_POLL_S, FILE_WAIT_S
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
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
CLOSED_REQUEST = (
    "REQUEST shop_1\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "list the items of the cart"\n'
    '\tCREATED_AT "2026-10-11T08:00:00Z"\n'
    "\tSTATUS closed\n"
)
PLANNED_REQUEST = (
    "REQUEST shop_1\n"
    "\tPROJECT @PROJECT.shop\n"
    f'\tTEXT "{REQUEST_TEXT}"\n'
    '\tCREATED_AT "2026-10-12T09:30:00Z"\n'
    "\tSTATUS planned\n"
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
TASK_STATES = (
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "M1", "task": "S3",'
    ' "state": "queued"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "task.state", "wave": "M1", "task": "S3",'
    ' "state": "running"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T12:00:00Z", "event": "task.state", "wave": "M0", "task": "S3",'
    ' "state": "merged"}\n'
)
PINNED_COMMIT_DATES = {"GIT_AUTHOR_DATE": "2026-10-12T09:00:00Z", "GIT_COMMITTER_DATE": "2026-10-12T09:00:00Z"}
ASKING_POLICY = "POLICY shop_review\n\tPROJECT @PROJECT.shop\n\tPLAN_REVIEW ask\n"


class WaveTestCase(unittest.TestCase):
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

    def read_requests(self) -> str:
        return (self.machine.corpus / "requests.awawa").read_text()

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted(self.ledger.glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def cut_wave_branch(self) -> None:
        self.project.run_git("checkout", "--quiet", "-b", WAVE_BRANCH)
        self.project.write("corpus/tasks.awawa", WAVE_TASKS)
        self.project.write("corpus/milestones.awawa", WAVE_MILESTONES)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of M1")
        self.project.run_git("checkout", "--quiet", "main")

    def wait_for_result(self, run_id: str) -> None:
        result = self.runs / run_id / "result.json"
        deadline = time.monotonic() + FILE_WAIT_S
        while not result.exists():
            if time.monotonic() > deadline:
                self.fail(f"{result} never appeared")
            time.sleep(FILE_POLL_S)


class BrigadeWaveNewTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "planner.json").write_text(json.dumps(DONE_RESULT))
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )

    def test_should_record_the_request_planning_with_the_instant_of_its_creation(self):
        # Act
        completed = self.run_wave("new", "shop", REQUEST_TEXT, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.wait_for_result(json.loads(completed.stdout)["run"])
        self.assertRegex(
            self.read_requests(),
            r'^REQUEST shop_1\n\tPROJECT @PROJECT\.shop\n\tTEXT "let the customer empty the cart in one click"\n'
            r'\tCREATED_AT "\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ"\n\tSTATUS planning\n$',
        )
        self.assertEqual(
            self.machine.read_git("log", "-1", "--format=%s"), "brigade wave new: @REQUEST.shop_1 of @PROJECT.shop\n"
        )

    def test_should_name_the_request_after_the_last_number_its_project_holds(self):
        # Arrange
        self.write_requests(CLOSED_REQUEST)

        # Act
        completed = self.run_wave("new", "shop", REQUEST_TEXT, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.wait_for_result(json.loads(completed.stdout)["run"])
        self.assertEqual(json.loads(completed.stdout)["request"], "shop_2")

    def test_should_launch_the_planner_on_the_request_detached_and_print_its_run(self):
        # Act
        completed = self.run_wave("new", "shop", REQUEST_TEXT, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertRegex(document["run"], RUN_ID_PATTERN)
        self.assertEqual(document, {"schema_version": 1, "request": "shop_1", "run": document["run"]})
        self.wait_for_result(document["run"])
        run_record = json.loads((self.runs / document["run"] / "run.json").read_text())
        self.assertEqual(
            (run_record["procedure"], run_record["slot"], run_record["project"], run_record["arguments"]),
            ("wave-plan", "plan", "shop", {"request": "shop_1"}),
        )

    def test_should_print_the_request_and_its_run_as_text(self):
        # Act
        completed = self.run_wave("new", "shop", REQUEST_TEXT)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(completed.stdout, r"^@REQUEST\.shop_1 planning, run \d{8}T\d{6}Z-[0-9a-f]{6}\n$")
        self.wait_for_result(completed.stdout.split()[-1])

    def test_should_exit_1_naming_a_project_that_is_not_registered(self):
        # Act
        completed = self.run_wave("new", "cafe", REQUEST_TEXT)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr), (1, "brigade wave new: @PROJECT.cafe is not registered\n")
        )
        self.assertFalse((self.machine.corpus / "requests.awawa").exists())

    def test_should_exit_1_naming_a_paused_project(self):
        # Arrange
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "pause", "shop")

        # Act
        completed = self.run_wave("new", "shop", REQUEST_TEXT)

        # Assert
        self.assertEqual((completed.returncode, completed.stderr), (1, "brigade wave new: @PROJECT.shop is paused\n"))
        self.assertFalse((self.machine.corpus / "requests.awawa").exists())


class BrigadeWaveNewWithAClientCountingNoStepsTest(WaveTestCase):
    def test_should_print_the_warning_of_the_planner_run(self):
        # Arrange
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "planner.json").write_text(json.dumps(DONE_RESULT))
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n[clients.fake]\nrecordings = "{recordings}"\n'
        )

        # Act
        completed = self.run_wave("new", "shop", REQUEST_TEXT, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.wait_for_result(json.loads(completed.stdout)["run"])
        self.assertEqual(
            completed.stderr,
            "brigade wave new: fake counts no steps: the budget of 30 steps is held on the clock"
            " and the run cut at its limit of 1140 s\n",
        )


class BrigadeWaveStartTest(WaveTestCase):
    def test_should_move_a_planned_request_to_running(self):
        # Arrange
        self.write_requests(PLANNED_REQUEST)

        # Act
        completed = self.run_wave("start", "shop_1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "request": "shop_1", "status": "running", "milestone": "M1", "project": "shop"},
        )
        self.assertEqual(self.read_requests(), PLANNED_REQUEST.replace("STATUS planned", "STATUS running"))

    def test_should_record_the_start_of_the_wave_in_the_ledger(self):
        # Arrange
        self.write_requests(PLANNED_REQUEST)

        # Act
        self.run_wave("start", "shop_1")

        # Assert
        [started] = self.read_events("wave.started")
        self.assertEqual((started["wave"], started["project"]), ("M1", "shop"))

    def test_should_print_the_start_as_text(self):
        # Arrange
        self.write_requests(PLANNED_REQUEST)

        # Act
        completed = self.run_wave("start", "shop_1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "@REQUEST.shop_1 running, wave @MILESTONE.M1 of @PROJECT.shop\n")

    def test_should_exit_1_naming_the_status_of_a_request_that_is_not_planned(self):
        # Arrange
        self.write_requests(PLANNING_REQUEST)

        # Act
        completed = self.run_wave("start", "shop_2")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave start: @REQUEST.shop_2 is planning, not planned\n"),
        )
        self.assertEqual(self.read_requests(), PLANNING_REQUEST)
        self.assertEqual(self.read_events("wave.started"), [])


class BrigadeWaveShowTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        self.cut_wave_branch()
        self.write_requests(f"{PLANNED_REQUEST}\n{PLANNING_REQUEST}")
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(TASK_STATES)

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
                "status": "planned",
                "milestone": "M1",
                "branch": WAVE_BRANCH,
                "created_at": "2026-10-12T09:30:00Z",
                "waits_for": "the next tick",
                "tasks": [
                    {"task": "S3", "title": "Empty the cart in one click", "state": "running", "pull_request": None},
                    {"task": "S4", "title": "Confirm before emptying the cart", "state": "queued", "pull_request": 12},
                ],
            },
        )

    def test_should_print_that_a_planned_request_waits_for_wave_start_under_plan_review_ask(self):
        # Arrange
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
            "@REQUEST.shop_1 of @PROJECT.shop  planned\n"
            f"{REQUEST_TEXT}\n"
            "milestone   M1\n"
            f"branch      {WAVE_BRANCH}\n"
            "created at  2026-10-12T09:30:00Z\n"
            "waits for   the next tick\n"
            "\n"
            "task  state    pull request  title\n"
            "S3    running  -             Empty the cart in one click\n"
            "S4    queued   12            Confirm before emptying the cart\n",
        )

    def test_should_exit_1_naming_a_request_the_operational_corpus_does_not_define(self):
        # Act
        completed = self.run_wave("show", "shop_9")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave show: @REQUEST.shop_9 is not defined in the operational corpus\n"),
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
        self.write_requests(
            f"{PLANNED_REQUEST}\n{PLANNING_REQUEST}\n"
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
                        "milestone": None,
                        "branch": None,
                        "created_at": "2026-10-14T07:15:00Z",
                    },
                    {
                        "name": "shop_1",
                        "project": "shop",
                        "status": "planned",
                        "milestone": "M1",
                        "branch": WAVE_BRANCH,
                        "created_at": "2026-10-12T09:30:00Z",
                    },
                    {
                        "name": "shop_2",
                        "project": "shop",
                        "status": "planning",
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
            "request  project  status    milestone  branch                     created at\n"
            "cafe_1   cafe     planning  -          -                          2026-10-14T07:15:00Z\n"
            f"shop_1   shop     planned   M1         {WAVE_BRANCH}  2026-10-12T09:30:00Z\n"
            "shop_2   shop     planning  -          -                          2026-10-13T14:00:00Z\n",
        )
