import http.client
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.process_launcher import ProcessLauncher

STOP_WAIT_S = 20.0
LAST_TICK = '{"schema_version": 1, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 0}'


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
