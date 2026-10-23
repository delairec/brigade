import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.scheduler_install import COMMAND
from brigade.errors import ToolNotFound
from tests.unit.commands.command_runtime import answer, create_runtime


class SchedulerDouble:
    def __init__(self, name: str):
        self.name = name

    def install(self, request: dict, runtime) -> dict:
        return {
            "schema_version": 1,
            "scheduler": self.name,
            "unit_files": [f"/home/user/.config/systemd/user/brigade-{self.name}.timer"],
            "cron_line": None,
            "keep_running": None,
        }


def _resolve_a_scheduler_double(kind: str, name: str, **places):
    return SchedulerDouble(name)


def _create_systemd_double(state: str):
    return lambda request: answer(request, f"{state}\n")


def _refuse_systemctl(request):
    raise ToolNotFound("systemctl is not on PATH")


class SchedulerInstallTextTest(unittest.TestCase):
    def test_should_print_what_was_installed(self):
        # Arrange
        rows = [
            (
                "units",
                {"scheduler": "systemd", "chosen_by": "probe", "unit_files": ["/u/brigade.timer"], "cron_line": None},
                "systemd installed, chosen by the probe of the user systemd instance\nunit  /u/brigade.timer",
            ),
            (
                "a cron line",
                {"scheduler": "cron", "chosen_by": "configuration", "unit_files": [], "cron_line": "*/5 * * * * b"},
                "cron installed, chosen by config.toml\ncron line  */5 * * * * b",
            ),
        ]
        for case, installed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text({"schema_version": 1, **installed, "keep_running": None})

                # Assert
                self.assertEqual(text, expected_text)

    def test_should_ask_to_keep_the_command_running_when_nothing_is_installed(self):
        # Arrange
        document = {
            "schema_version": 1,
            "scheduler": "loop",
            "chosen_by": "configuration",
            "unit_files": [],
            "cron_line": None,
            "keep_running": "brigade tick --loop",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text, "loop chosen by config.toml: nothing installed; keep this command running\nbrigade tick --loop"
        )


class SchedulerInstallExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class SchedulerInstallRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class SchedulerInstallChoiceTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_install_the_scheduler_the_configuration_names(self):
        # Arrange
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text('scheduler = "cron"\n', encoding="utf-8")
        runtime = create_runtime(self.root, resolve_plugin=_resolve_a_scheduler_double)

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "scheduler": "cron",
                "chosen_by": "configuration",
                "unit_files": ["/home/user/.config/systemd/user/brigade-cron.timer"],
                "cron_line": None,
                "keep_running": None,
            },
        )

    def test_should_install_the_scheduler_the_probe_of_systemd_chooses(self):
        # Arrange
        rows = [
            ("a running instance", _create_systemd_double("running"), "systemd"),
            ("a degraded instance", _create_systemd_double("degraded"), "systemd"),
            ("an offline instance", _create_systemd_double("offline"), "cron"),
            ("no systemctl", _refuse_systemctl, "cron"),
        ]
        for case, run_process, expected_scheduler in rows:
            with self.subTest(case=case):
                # Arrange
                runtime = create_runtime(self.root, run_process=run_process, resolve_plugin=_resolve_a_scheduler_double)

                # Act
                document = COMMAND.run(Namespace(), runtime)

                # Assert
                self.assertEqual(document["scheduler"], expected_scheduler)
