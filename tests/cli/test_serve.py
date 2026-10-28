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


def fetch_status(url: str) -> int:
    address = urlsplit(url)
    connection = http.client.HTTPConnection(address.hostname, address.port, timeout=STOP_WAIT_S)
    try:
        connection.request("GET", address.path)
        return connection.getresponse().status
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
