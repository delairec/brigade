import json
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
REQUEST_TEXT = "let the customer empty the cart in one click"
PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n"
    "\t\tREQUIRED\n"
)
MAIN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n'
CANCELLED_REQUEST = (
    "REQUEST shop_r1\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "list the items of the cart"\n'
    '\tCREATED_AT "2026-10-11T08:00:00Z"\n'
    "\tSTATUS cancelled\n"
)
PLANNED_REQUEST = (
    "REQUEST shop_r1\n"
    "\tPROJECT @PROJECT.shop\n"
    f'\tTEXT "{REQUEST_TEXT}"\n'
    '\tCREATED_AT "2026-10-12T09:30:00Z"\n'
    "\tSTATUS planned\n"
    '\tMILESTONE "M1"\n'
    "\tPR 7\n"
)
PLANNING_REQUEST = (
    "REQUEST shop_r2\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "show the total of the cart"\n'
    '\tCREATED_AT "2026-10-13T14:00:00Z"\n'
    "\tSTATUS planning\n"
)
CAFE_REQUEST = (
    "REQUEST cafe_r1\n"
    "\tPROJECT @PROJECT.cafe\n"
    '\tTEXT "print the receipt"\n'
    '\tCREATED_AT "2026-10-14T07:15:00Z"\n'
    "\tSTATUS planning\n"
)


class RequestTestCase(FileWaitingTestCase):
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

    def tearDown(self):
        self.root.cleanup()

    def run_request(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "request", *arguments)

    def write_requests(self, requests: str) -> None:
        (self.machine.corpus / "requests.awawa").write_text(requests)

    def commit_requests(self) -> None:
        self.machine.read_git("add", "requests.awawa")
        self.machine.read_git("commit", "--quiet", "-m", "the requests of an older brigade")

    def read_requests(self) -> str:
        return (self.machine.corpus / "requests.awawa").read_text()

    def wait_for_result(self, run_id: str) -> None:
        self.wait_for_file(self.runs / run_id / "result.json")


class BrigadeRequestNewTest(RequestTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "planner.json").write_text(json.dumps(DONE_RESULT))
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )

    def test_should_launch_the_planner_on_the_request_detached_and_print_its_run(self):
        # Act
        completed = self.run_request("new", "shop", REQUEST_TEXT, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertRegex(document["run"], RUN_ID_PATTERN)
        self.assertEqual(document, {"schema_version": 1, "request": "shop_r1", "run": document["run"]})
        self.wait_for_result(document["run"])
        run_record = json.loads((self.runs / document["run"] / "run.json").read_text())
        self.assertEqual(
            (run_record["procedure"], run_record["slot"], run_record["project"], run_record["arguments"]),
            ("wave-plan", "plan", "shop", {"request": "shop_r1"}),
        )


class BrigadeWaveNewTest(RequestTestCase):
    def test_should_be_no_command_of_brigade(self):
        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", "new", "shop", REQUEST_TEXT)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("invalid choice: 'new'", completed.stderr)


class BrigadeRequestShowTest(RequestTestCase):
    def setUp(self):
        super().setUp()
        self.write_requests(f"{PLANNED_REQUEST}\n{PLANNING_REQUEST}")

    def test_should_print_the_request_with_its_plan_and_its_pull_request(self):
        # Act
        completed = self.run_request("show", "shop_r1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "request": "shop_r1",
                "project": "shop",
                "text": REQUEST_TEXT,
                "status": "planned",
                "milestone": "M1",
                "pr": 7,
                "created_at": "2026-10-12T09:30:00Z",
            },
        )


class BrigadeRequestListTest(RequestTestCase):
    def setUp(self):
        super().setUp()
        cafe = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "cafe", self.machine.describe_environment()
        )
        cafe.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        cafe.track("corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(cafe.path))
        self.write_requests(f"{PLANNED_REQUEST}\n{PLANNING_REQUEST}\n{CAFE_REQUEST}")

    def test_should_print_one_row_per_request(self):
        # Act
        completed = self.run_request("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "requests": [
                    {
                        "name": "cafe_r1",
                        "project": "cafe",
                        "status": "planning",
                        "milestone": None,
                        "pr": None,
                        "created_at": "2026-10-14T07:15:00Z",
                    },
                    {
                        "name": "shop_r1",
                        "project": "shop",
                        "status": "planned",
                        "milestone": "M1",
                        "pr": 7,
                        "created_at": "2026-10-12T09:30:00Z",
                    },
                    {
                        "name": "shop_r2",
                        "project": "shop",
                        "status": "planning",
                        "milestone": None,
                        "pr": None,
                        "created_at": "2026-10-13T14:00:00Z",
                    },
                ],
            },
        )


class BrigadeRequestCancelTest(RequestTestCase):
    def setUp(self):
        super().setUp()
        self.write_requests(f"{PLANNED_REQUEST}\n{PLANNING_REQUEST}\n{CANCELLED_REQUEST.replace('shop_r1', 'shop_r3')}")

    def test_should_move_a_request_to_cancelled(self):
        for request in ["shop_r1", "shop_r2"]:
            with self.subTest(request=request):
                # Act
                completed = self.run_request("cancel", request, "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout), {"schema_version": 1, "request": request, "status": "cancelled"}
                )
                self.assertEqual(
                    self.machine.read_git("log", "-1", "--format=%s"),
                    f"brigade request cancel: @REQUEST.{request} cancelled\n",
                )


if __name__ == "__main__":
    unittest.main()
