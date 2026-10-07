import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.adapters.schedulers.systemd import read_status
from brigade.system.run_process import ProcessRecord


def create_runtime(exit_code: int, stdout: str) -> SimpleNamespace:
    def run_systemctl(request):
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="", duration_ms=0
        )

    return SimpleNamespace(run_process=run_systemctl)


class ReadStatusOfAnInstalledTimerTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.units = Path(self.root.name) / "systemd" / "user"
        self.units.mkdir(parents=True)
        (self.units / "brigade.service").write_text("[Service]\n")
        (self.units / "brigade.timer").write_text("[Timer]\n")

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_no_next_activation_when_systemctl_names_none(self):
        rows = [
            ("systemctl failing", 1, "Failed to connect to bus\n"),
            ("an empty answer", 0, "\n"),
            ("no elapse planned", 0, "n/a\n"),
        ]
        for answer, exit_code, stdout in rows:
            with self.subTest(answer=answer):
                # Arrange
                runtime = create_runtime(exit_code, stdout)

                # Act
                status = read_status({"unit_directory": str(self.units)}, runtime)

                # Assert
                self.assertEqual(
                    status,
                    {
                        "schema_version": 1,
                        "installed": True,
                        "unit_files": [str(self.units / "brigade.service"), str(self.units / "brigade.timer")],
                        "cron_line": None,
                        "next_activation": None,
                    },
                )
