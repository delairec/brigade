import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration, ConfigurationMissing
from brigade.system.paths import Paths
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, CONFIGURATION_REQUIRED, read_configuration
from brigade.system.trail_writer import TrailWriter

NO_PATH_NEEDED = ""
CONFIGURATION_FILE = "config.toml"


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"a read of the configuration ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"a read of the configuration resolved the {kind} plugin {name}")


def _create_runtime(root: Path) -> Runtime:
    return Runtime(
        run_process=_refuse_process,
        spawn_process=_refuse_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
        ),
        now=datetime(2026, 10, 8, 9, 0, 0, tzinfo=UTC),
        read_clock=lambda: datetime(2026, 10, 8, 9, 0, 0, tzinfo=UTC),
        read_monotonic=lambda: 0.0,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


class ReadConfigurationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()

    def test_should_read_the_configuration_file_when_written(self):
        # Arrange
        (self.root / "config" / CONFIGURATION_FILE).write_text('client = "fake"\n', encoding="utf-8")
        for request in [CONFIGURATION_REQUIRED, CONFIGURATION_OPTIONAL]:
            with self.subTest(request=request):
                # Act
                configuration = read_configuration(_create_runtime(self.root), request)

                # Assert
                self.assertEqual(configuration, Configuration(client="fake"))

    def test_should_answer_nothing_configured_when_the_file_is_optional_and_missing(self):
        # Act
        configuration = read_configuration(_create_runtime(self.root), CONFIGURATION_OPTIONAL)

        # Assert
        self.assertEqual(configuration, Configuration())

    def test_should_refuse_a_missing_file_when_the_configuration_is_required(self):
        # Arrange
        configuration_path = self.root / "config" / CONFIGURATION_FILE

        # Act
        with self.assertRaises(ConfigurationMissing) as raised:
            read_configuration(_create_runtime(self.root), CONFIGURATION_REQUIRED)

        # Assert
        self.assertEqual(str(raised.exception), f"no configuration at {configuration_path}; run brigade init")
