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

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, SHIPPED_SCHEMA, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.cli.wave_tick_test_case import WaveTickTestCase
from tests.process_launcher import ProcessLauncher

STOP_WAIT_S = 20.0
PARKED_WAVE = (
    '{"schema_version": 2, "ts": "2026-11-18T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/M1-empty-cart", "tasks": ["S3"]}\n'
    '{"schema_version": 1, "ts": "2026-11-18T10:00:00Z", "event": "wave.parked", "wave": "shop_w1",'
    ' "reason": "forge_account"}\n'
)
RUN_ID = "20261118T101500Z-a1b2c3"
RUN_RECORD = {
    "schema_version": 1,
    "run": RUN_ID,
    "procedure": "build-task",
    "procedure_path": "built-in",
    "slot": "build",
    "role": "builder",
    "role_source": "built-in",
    "client": "fake",
    "project": None,
    "cwd": "/srv/tidepool",
    "worktree": "/srv/tidepool",
    "capabilities": ["read"],
    "budget": 40,
    "wall_limit_s": 1500.0,
    "arguments": {},
    "wave": None,
    "task": None,
    "brief": None,
}
SEGMENT_RESULT = {
    "schema_version": 3,
    "ts": "2026-11-18T10:20:00Z",
    "event": "run.finished",
    "run": RUN_ID,
    "segment": 1,
    "procedure": "build-task",
    "slot": "build",
    "role": "builder",
    "client": "fake",
    "project": None,
    "session": None,
    "main_turns": 12,
    "total_turns": 12,
    "duration_ms": 300000,
    "usage": None,
    "outcome": "done",
    "error_class": None,
    "exit": 0,
    "wave": None,
    "task": None,
    "nulls": {},
    "cost_usd": 0.5,
}
REPORT = (
    'REPORT oak_w3\n\tWAVE "oak_w3"\n\tPROJECT "oak"\n\tSTATISTIC "tasks 1"\n'
    '\tNARRATIVE "the wave ran once"\n\tNARRATIVE "Verdict: delivered"\n'
)
PROPOSED_PATTERN = (
    "PATTERN FlakyTests\n"
    '\tTITLE "the tests are flaky"\n'
    "\tSTATUS new\n"
    '\tEVIDENCE "rt:PRRT_kwDO a thread on the flaky test"\n'
    "\tACTION wave\n"
    '\tTARGET "shop"\n'
)
LAST_TICK = '{"schema_version": 1, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 0}'
PARKED_WAVE_LEDGER = (
    '{"schema_version": 2, "ts": "2026-11-02T08:00:00Z", "event": "wave.started", "wave": "oak_w4",'
    ' "project": "oak", "branch": "integration/oak_w4", "tasks": ["B4"]}\n'
    '{"schema_version": 1, "ts": "2026-11-02T09:00:00Z", "event": "wave.parked", "wave": "oak_w4",'
    ' "reason": "forge_account"}\n'
)
REPORT_OF_M13 = (
    "REPORT brigade_M13\n"
    '\tMILESTONE "M13"\n'
    '\tPROJECT "brigade"\n'
    '\tSTATISTIC "tasks 4"\n'
    '\tSTATISTIC "merged 3"\n'
    '\tNARRATIVE "Verdict: M13 delivered three of its four tasks."\n'
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
        self.assertIn('<time datetime="2026-10-06T12:00:00Z">12:00:00Z</time>', body)

    def test_should_answer_the_views_of_the_rail_with_what_each_holds(self):
        # Arrange
        self.machine.install_awawa(self)
        self.machine.run_init()
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/rail")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<a href="#waves">Waves <span class="count num">0 open</span></a>', body)

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
        self.assertIn('<div class="block-head"><h2>Do the turn caps fit?</h2>', body)

    def write_finished_run(self) -> None:
        run_directory = self.machine.state_home / "brigade" / "runs" / RUN_ID
        (run_directory / "segments" / "1").mkdir(parents=True)
        (run_directory / "run.json").write_text(json.dumps(RUN_RECORD))
        (run_directory / "segments" / "1" / "result.json").write_text(json.dumps(SEGMENT_RESULT))
        (run_directory / "result.json").write_text(json.dumps(SEGMENT_RESULT))

    def test_should_answer_the_runs_view_with_its_explainer(self):
        # Arrange
        self.write_finished_run()
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/runs")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn(
            '<details class="explainer"><summary>How to read this page</summary><div><p>A run is one procedure', body
        )

    def test_should_answer_the_page_of_a_run_with_its_segments(self):
        # Arrange
        self.write_finished_run()
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, f"/views/runs/{RUN_ID}")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn("<td>2026-11-18T10:15:00Z</td><td>5m00s</td><td>$0.50</td></tr>", body)

    def test_should_answer_the_page_of_a_report_with_its_verdict_before_any_other_field(self):
        # Arrange
        self.machine.install_awawa(self)
        self.machine.run_init()
        (self.machine.corpus / "reports.awawa").write_text(REPORT)
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/reports/oak_w3")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<p class="lede">delivered</p>', body)

    def test_should_answer_the_reports_view_with_its_explainer_open_and_the_verdict_of_each_report(self):
        # Arrange
        self.machine.install_awawa(self)
        self.machine.run_init()
        (self.machine.corpus / "reports.awawa").write_text(REPORT_OF_M13)
        url = self.start_serving().stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/reports")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<details class="explainer" open><summary>What a report is, and when to read one</summary>', body)
        self.assertIn("<td>M13 delivered three of its four tasks.</td>", body)


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

    def test_should_draw_one_column_per_status_on_the_board_of_the_awawa_tab(self):
        # Arrange
        _, url = self.start_serving()

        # Act
        status, body = fetch(url, "/views/awawa/app?view=board&type=TASK&field=STATUS")

        # Assert
        self.assertEqual(status, 200, body)
        self.assertIn(
            '<h3>draft <span class="awawa-count">0</span></h3><ul class="awawa-cards"></ul></section>'
            '<section class="awawa-column"><h3>todo <span class="awawa-count">1</span></h3>',
            body,
        )
        self.assertIn(
            '<h3>implemented <span class="awawa-count">0</span></h3><ul class="awawa-cards"></ul></section></div>', body
        )


class BrigadeServeWithoutAProjectHoldingACorpusTest(BrigadeServeTestCase):
    def test_should_serve_the_corpus_view_no_more(self):
        # Arrange
        _, url = self.start_serving()

        # Act
        status, body = fetch(url, "/views/corpus")

        # Assert
        self.assertEqual(status, 404, body)

    def test_should_start_no_child_process(self):
        # Arrange
        process, url = self.start_serving()

        # Act
        status, body = fetch(url, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(status, 404, body)
        self.assertEqual(list_children(process), [])


class BrigadeServeOfAWaveTest(WaveTickTestCase):
    def test_should_answer_the_page_of_a_wave_with_its_sentence_its_tiles_and_its_events_folded(self):
        # Arrange
        process = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "serve", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.describe_environment(),
        )
        self.addCleanup(process.communicate, timeout=STOP_WAIT_S)
        self.addCleanup(process.terminate)
        url = process.stdout.readline().strip()

        # Act
        status, body = fetch(url, "/views/waves/shop_w1")

        # Assert
        self.assertEqual(status, 200, body)
        self.assertIn('<h1>Wave <span class="mono">shop_w1</span>', body)
        self.assertIn('<div class="stat-tiles"><div class="stat-tile">', body)
        self.assertIn('<details class="fold"><summary>Show the events <span>', body)


class BrigadeServeHomeTest(BrigadeServeTestCase):
    def test_should_answer_home_opening_on_the_sentence_of_brigade(self):
        # Arrange
        _, url = self.start_serving()

        # Act
        status, body = fetch(url, "/views/status")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn('<p class="status-sentence">brigade is ', body)

    def test_should_answer_home_with_a_parked_wave_under_needs_you(self):
        # Arrange
        ledger = self.machine.state_home / "brigade" / "ledger" / "2026-11.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(PARKED_WAVE)
        _, url = self.start_serving()

        # Act
        status, body = fetch(url, "/views/status")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn(
            '<section><h2>Needs you</h2><ul class="needs-you-list">'
            '<li class="needs-you tone-you"><span class="mark">II</span>'
            "<div><h3>Wave shop_w1 is halted</h3><p>parked on forge_account</p></div>",
            body,
        )


class BrigadeServeOfTheInboxTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.machine = TemporaryMachine(Path(root.name))
        self.machine.install_awawa(self)
        self.machine.corpus.mkdir(parents=True)
        (self.machine.corpus / "_schema.awawa").write_bytes(SHIPPED_SCHEMA.read_bytes())
        (self.machine.corpus / "patterns.awawa").write_text(PROPOSED_PATTERN)

    def start_serving(self) -> str:
        process = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "serve", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(process.kill)
        return process.stdout.readline().strip()

    def test_should_answer_the_inbox_view_with_the_title_of_a_proposed_pattern(self):
        # Arrange
        url = self.start_serving()

        # Act
        status, body = fetch(url, "/views/inbox")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn("<h3>the tests are flaky</h3>", body)

    def test_should_answer_the_page_of_a_proposed_pattern_with_its_evidence(self):
        # Arrange
        url = self.start_serving()

        # Act
        status, body = fetch(url, "/views/inbox/FlakyTests")

        # Assert
        self.assertEqual(status, 200)
        self.assertIn("<li>rt:PRRT_kwDO a thread on the flaky test</li>", body)
