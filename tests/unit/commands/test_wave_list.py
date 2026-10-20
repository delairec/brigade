import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.wave_list import COMMAND
from tests.unit.commands.command_runtime import create_runtime, write_ledger

EVERY_PROJECT = None
TIDES_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7", "T8"],
}
TIDES_CANCELLED = {
    "schema_version": 1,
    "ts": "2026-10-01T22:00:00Z",
    "event": "wave.cancelled",
    "wave": "tidepool_w16",
    "reason": "user",
}
GAUGES_STARTED = {
    **TIDES_STARTED,
    "ts": "2026-10-02T22:00:00Z",
    "wave": "gauges_w1",
    "project": "gauges",
    "branch": "integration/gauges_w1",
    "tasks": ["G1"],
}
TIDES_ROW = {
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "last_event": "wave.cancelled",
    "tasks": 2,
}
GAUGES_ROW = {
    "wave": "gauges_w1",
    "project": "gauges",
    "branch": "integration/gauges_w1",
    "last_event": "wave.started",
    "tasks": 1,
}


class WaveListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_wave(self):
        # Arrange
        document = {"schema_version": 1, "waves": [GAUGES_ROW, TIDES_ROW]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave          project   branch                    last event      tasks\n"
            "gauges_w1     gauges    integration/gauges_w1     wave.started    1\n"
            "tidepool_w16  tidepool  integration/tidepool_w16  wave.cancelled  2",
        )


class WaveListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "waves": []})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(project=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveListOfTheLedgerTest(unittest.TestCase):
    def test_should_list_the_waves_of_the_project_asked_the_open_waves_first(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(root, [TIDES_STARTED, TIDES_CANCELLED, GAUGES_STARTED])
        runtime = create_runtime(root)
        rows = [
            ("every project", EVERY_PROJECT, [GAUGES_ROW, TIDES_ROW]),
            ("one project", "tidepool", [TIDES_ROW]),
        ]
        for case, project, expected_waves in rows:
            with self.subTest(case=case):
                # Act
                document = COMMAND.run(SimpleNamespace(project=project), runtime)

                # Assert
                self.assertEqual(document, {"schema_version": 1, "waves": expected_waves})
