import unittest
from types import SimpleNamespace

from brigade.adapters.schedulers.cron import install, read_status
from brigade.errors import CommandFailed, ToolNotFound
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

LIST_CRONTAB = ("crontab", "-l")
REQUEST = {
    "brigade": "/opt/brigade/bin/brigade",
    "log_file": "/home/ada/.local/state/brigade/tick.log",
    "environment": {"PATH": "/usr/bin:/bin", "BRIGADE_NOTE": "100%"},
}
CRON_LINE = (
    "*/5 * * * * mkdir -p /home/ada/.local/state/brigade && PATH=/usr/bin:/bin BRIGADE_NOTE=100\\%"
    " /opt/brigade/bin/brigade tick --once >/dev/null 2>>/home/ada/.local/state/brigade/tick.log"
    " # brigade scheduler install"
)


def create_runtime(listing: ProcessAnswer) -> SimpleNamespace:
    return SimpleNamespace(run_process=RecordingProcessRunner({LIST_CRONTAB: listing}))


def refuse_missing_crontab(request):
    raise ToolNotFound("crontab is not on PATH")


class InstallCronTest(unittest.TestCase):
    def test_should_replace_the_earlier_line_of_brigade_and_keep_the_others(self):
        # Arrange
        runtime = create_runtime(
            ProcessAnswer(stdout="0 3 * * * backup\n*/5 * * * * old # brigade scheduler install\n")
        )

        # Act
        installation = install(REQUEST, runtime)

        # Assert
        self.assertEqual(
            (installation, runtime.run_process.requests[-1].stdin),
            (
                {
                    "schema_version": 1,
                    "scheduler": "cron",
                    "unit_files": [],
                    "cron_line": CRON_LINE,
                    "keep_running": None,
                },
                f"0 3 * * * backup\n{CRON_LINE}\n",
            ),
        )

    def test_should_start_the_crontab_of_a_user_who_has_none(self):
        # Arrange
        runtime = create_runtime(ProcessAnswer(exit_code=1, stderr="no crontab for ada\n"))

        # Act
        install(REQUEST, runtime)

        # Assert
        self.assertEqual(runtime.run_process.requests[-1].stdin, f"{CRON_LINE}\n")

    def test_should_refuse_a_crontab_that_cannot_be_listed(self):
        # Arrange
        runtime = create_runtime(ProcessAnswer(exit_code=1, stderr="crontab: permission denied\n"))

        # Act
        with self.assertRaises(CommandFailed) as refusal:
            install(REQUEST, runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "crontab -l exited 1: crontab: permission denied")


class ReadCronStatusTest(unittest.TestCase):
    def test_should_read_the_line_of_brigade_when_installed(self):
        # Arrange
        runtime = create_runtime(ProcessAnswer(stdout=f"0 3 * * * backup\n{CRON_LINE}\n"))

        # Act
        status = read_status({}, runtime)

        # Assert
        self.assertEqual(
            status,
            {"schema_version": 1, "installed": True, "unit_files": [], "cron_line": CRON_LINE, "next_activation": None},
        )

    def test_should_read_nothing_installed_without_crontab(self):
        # Arrange
        runtime = SimpleNamespace(run_process=refuse_missing_crontab)

        # Act
        status = read_status({}, runtime)

        # Assert
        self.assertEqual((status["installed"], status["cron_line"]), (False, None))
