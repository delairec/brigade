import http.client
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.process_launcher import ProcessLauncher

STOP_WAIT_S = 20.0
LAST_TICK = '{"schema_version": 1, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 0}'
PARKED_WAVE_LEDGER = (
    '{"schema_version": 2, "ts": "2026-11-02T08:00:00Z", "event": "wave.started", "wave": "oak_w4",'
    ' "project": "oak", "branch": "integration/oak_w4", "tasks": ["B4"]}\n'
    '{"schema_version": 1, "ts": "2026-11-02T09:00:00Z", "event": "wave.parked", "wave": "oak_w4",'
    ' "reason": "forge_account"}\n'
)


def fetch_status(url: str) -> int:
    address = urlsplit(url)
    connection = http.client.HTTPConnection(address.hostname, address.port, timeout=STOP_WAIT_S)
    try:
        connection.request("GET", address.path)
        return connection.getresponse().status
    finally:
        connection.close()


def fetch(url: str, path: str) -> tuple[int, str]:
    address = urlsplit(url)
    connection = http.client.HTTPConnection(address.hostname, address.port, timeout=STOP_WAIT_S)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read().decode()
    finally:
        connection.close()


class BrigadeServeTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.machine = TemporaryMachine(Path(root.name))

    def start_serving(self) -> subprocess.Popen:
        process = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "serve", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(process.kill)
        return process

    def test_should_serve_the_page_at_the_url_it_prints_and_exit_0_on_a_stop_signal(self):
        # Arrange
        rows = [("SIGINT", signal.SIGINT), ("SIGTERM", signal.SIGTERM)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                process = self.start_serving()
                status = fetch_status(process.stdout.readline().strip())

                # Act
                process.send_signal(stop_signal)
                process.communicate(timeout=STOP_WAIT_S)

                # Assert
                self.assertEqual(status, 200)
                self.assertEqual(process.returncode, 0)

    def test_should_answer_the_shell_at_its_root(self):
        # Arrange
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<nav class="rail">', body)

    def test_should_answer_the_tones_in_its_stylesheet(self):
        # Arrange
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/dashboard.css")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn("--you: #b36b00;", body)

    def test_should_answer_the_heartbeat_region_with_the_last_tick(self):
        # Arrange
        heartbeat = self.machine.state_home / "brigade" / "tick.json"
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        heartbeat.write_text(LAST_TICK)
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/heartbeat")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<time datetime="2026-10-06T12:00:00Z">2026-10-06T12:00:00Z</time>', body)

    def test_should_answer_the_waves_view_with_its_sentence_and_the_pill_of_a_parked_wave(self):
        # Arrange
        ledger = self.machine.state_home / "brigade" / "ledger" / "2026-11.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(PARKED_WAVE_LEDGER)
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/waves")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<p class="status-sentence">Waves open: 1, parked: 1, blocked: 0.</p>', body)
        self.assertIn(
            '<span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>'
            "parked</span></span>",
            body,
        )

    def test_should_answer_the_ledger_view_with_its_callout_and_the_table_of_the_caps(self):
        # Arrange
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/ledger")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<div class="callout tone-faint"><p>The measures cover 0 runs finished in an empty ledger;', body)
        self.assertIn("<h3>Turn cap by role</h3>", body)


ADDON_SCHEMA = (
    'SCHEMA TASK\n\tDESC "a task"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
    "\tFIELD STATUS draft|todo|implemented\n\t\tREQUIRED\n"
)
ADDON_TASKS = 'TASK B1\n\tTITLE "Read the corpus"\n\tSTATUS todo\n'
BOARD_OF_THE_TASKS = "/api/awawa/app?view=board&type=TASK"


def list_children(process: subprocess.Popen) -> list[str]:
    listed = ProcessLauncher.run(["pgrep", "-P", str(process.pid)], check=False, capture_output=True, text=True)
    return listed.stdout.split()


class BrigadeServeTestCase(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name).resolve()
        self.machine = TemporaryMachine(self.root)
        self.machine.install_awawa(self)
        self.machine.run_init()

    def start_serving(self) -> tuple[subprocess.Popen, str]:
        process = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "serve", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(process.communicate, timeout=STOP_WAIT_S)
        self.addCleanup(process.terminate)
        return process, process.stdout.readline().strip()


class BrigadeServeWithAProjectHoldingACorpusTest(BrigadeServeTestCase):
    def setUp(self):
        super().setUp()
        project = TemporaryProject(self.root / "projects" / "app", self.machine.describe_environment())
        project.write("corpus/schema.awawa", ADDON_SCHEMA)
        project.write("corpus/tasks.awawa", ADDON_TASKS)
        project.track("corpus")
        project.run_git("commit", "--quiet", "-m", "first")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(project.path), "--corpus-mode", "control")

    def test_should_answer_the_board_of_the_tasks_through_the_awawa_addon(self):
        # Arrange
        process, url = self.start_serving()

        # Act
        status, body = fetch(url, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["columns"][1]["entities"][0]["code"], "B1")
        self.assertEqual(len(list_children(process)), 1)

    def test_should_keep_serving_once_the_addon_died_and_start_it_again_at_the_next_request(self):
        # Arrange
        process, url = self.start_serving()
        fetch(url, BOARD_OF_THE_TASKS)
        os.kill(int(list_children(process)[0]), signal.SIGKILL)

        # Act
        home_status, home = fetch(url, "/views/status")
        status, body = fetch(url, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(home_status, 200, home)
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["view"], "board")


class BrigadeServeWithoutAProjectHoldingACorpusTest(BrigadeServeTestCase):
    def test_should_start_no_child_process(self):
        # Arrange
        process, url = self.start_serving()

        # Act
        status, body = fetch(url, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(status, 404, body)
        self.assertEqual(list_children(process), [])
