import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.wave_list import COMMAND
from tests.unit.commands.command_runtime import (
    create_corpus_double,
    create_runtime,
    write_ledger,
    write_operational_corpus,
)

EVERY_PROJECT = None
TIDES_REQUEST = (
    ("PROJECT", "@PROJECT.tidepool"),
    ("STATUS", "running"),
    ("MILESTONE", "M4"),
    ("BRANCH", "integration/M4-tides"),
    ("CREATED_AT", "2026-09-30T21:00:00Z"),
)
GAUGES_REQUEST = (
    ("PROJECT", "@PROJECT.gauges"),
    ("STATUS", "planning"),
    ("CREATED_AT", "2026-10-01T21:00:00Z"),
)
TIDES_ROW = {
    "name": "R1",
    "project": "tidepool",
    "status": "running",
    "milestone": "M4",
    "branch": "integration/M4-tides",
    "created_at": "2026-09-30T21:00:00Z",
    "wave": "tidepool_w16",
}
GAUGES_ROW = {
    "name": "R2",
    "project": "gauges",
    "status": "planning",
    "milestone": None,
    "branch": None,
    "created_at": "2026-10-01T21:00:00Z",
    "wave": None,
}


class WaveListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_request_marking_what_is_absent(self):
        # Arrange
        document = {"schema_version": 1, "requests": [TIDES_ROW, GAUGES_ROW]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "request  project   status    wave          milestone  branch                created at\n"
            "R1       tidepool  running   tidepool_w16  M4         integration/M4-tides  2026-09-30T21:00:00Z\n"
            "R2       gauges    planning  -             -          -                     2026-10-01T21:00:00Z",
        )


class WaveListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "requests": []})

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


class WaveListOfTheRequestsTest(unittest.TestCase):
    def test_should_list_the_requests_of_the_project_asked_with_their_wave(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        write_ledger(
            root,
            [
                {
                    "schema_version": 2,
                    "ts": "2026-09-30T22:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4-tides",
                    "tasks": ["T7"],
                }
            ],
        )
        entities = {"REQUEST": {"R1": TIDES_REQUEST, "R2": GAUGES_REQUEST}}
        runtime = create_runtime(root, run_process=create_corpus_double(entities))
        rows = [
            ("every project", EVERY_PROJECT, [TIDES_ROW, GAUGES_ROW]),
            ("one project", "gauges", [GAUGES_ROW]),
        ]
        for case, project, expected_requests in rows:
            with self.subTest(case=case):
                # Act
                document = COMMAND.run(SimpleNamespace(project=project), runtime)

                # Assert
                self.assertEqual(document, {"schema_version": 1, "requests": expected_requests})
