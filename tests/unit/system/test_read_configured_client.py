import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.read_configured_client import read_configured_client
from brigade.system.trail_writer import TrailWriter

NO_PATH_NEEDED = ""
CONFIGURATION_FILE = "config.toml"
CONFIGURED_CLIENT = "fake"
CONFIGURATION = f'client = "{CONFIGURED_CLIENT}"\nreasoning.deepest = {{ model = "mistral-large", effort = "high" }}\n'
CONFIGURATION_WITHOUT_CLIENT = 'scheduler = "cron"\n'


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"a read of the configured client ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"a read of the configured client resolved the {kind} plugin {name}")


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
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


class ReadConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()

    def test_should_read_the_name_of_the_configured_client_with_its_configuration(self):
        # Arrange
        (self.root / "config" / CONFIGURATION_FILE).write_text(CONFIGURATION, encoding="utf-8")

        # Act
        configured = read_configured_client(_create_runtime(self.root))

        # Assert
        self.assertEqual(configured.name, CONFIGURED_CLIENT)
        self.assertEqual(configured.configuration.client, CONFIGURED_CLIENT)
        self.assertEqual(configured.configuration.reasoning["deepest"].model, "mistral-large")

    def test_should_refuse_a_configuration_that_names_no_client(self):
        # Arrange
        configuration_path = self.root / "config" / CONFIGURATION_FILE
        configuration_path.write_text(CONFIGURATION_WITHOUT_CLIENT, encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_configured_client(_create_runtime(self.root))

        # Assert
        self.assertEqual(
            str(raised.exception), f"config.toml names no client: set the client key in {configuration_path}"
        )
