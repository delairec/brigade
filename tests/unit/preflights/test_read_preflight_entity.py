import json
import tempfile
import unittest
from pathlib import Path

from brigade.preflights.read_preflight_entity import read_preflight_entity
from brigade.preflights.read_preflight_file import read_preflight_file
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NIGHTLY_GATE_ENTITY = {
    "file": "/srv/shop/preflights.awawa",
    "fields": [
        {"name": "TITLE", "atoms": ['"the nightly checks of the shop"'], "fields": []},
        {
            "name": "COLLECTOR",
            "atoms": ['"notes"'],
            "fields": [{"name": "PARAMETER", "atoms": ['"depth=1"'], "fields": []}],
        },
        {"name": "CHECK", "atoms": ['"coverage"'], "fields": []},
    ],
}
NIGHTLY_GATE_FILE = (
    "schema_version = 1\n"
    'name = "nightly-gate"\n'
    'description = "the nightly checks of the shop"\n'
    'collectors = [{ name = "notes", parameters = { depth = "1" } }]\n'
    'checks = [{ name = "coverage", parameters = {} }]\n'
)
ROOT = Path("/srv/shop")


def create_runner(answer: ProcessAnswer) -> RecordingProcessRunner:
    return RecordingProcessRunner({("awawa", "show", "@PREFLIGHT.nightly_gate", "--json", "/srv/shop"): answer})


class ReadPreflightEntityTest(unittest.TestCase):
    def test_should_read_the_preflight_entity_named_after_the_preflight_its_hyphens_as_underscores(self):
        # Arrange
        runner = create_runner(ProcessAnswer(stdout=json.dumps(NIGHTLY_GATE_ENTITY)))

        # Act
        preflight = read_preflight_entity(runner, ROOT, "nightly-gate")

        # Assert
        self.assertEqual(
            preflight,
            {
                "schema_version": 1,
                "name": "nightly-gate",
                "description": "the nightly checks of the shop",
                "collectors": [{"name": "notes", "parameters": {"depth": "1"}}],
                "checks": [{"name": "coverage", "parameters": {}}],
            },
        )

    def test_should_keep_every_separator_after_the_first_in_the_value_of_a_parameter(self):
        # Arrange
        entity = {
            "file": "/srv/shop/preflights.awawa",
            "fields": [
                {"name": "TITLE", "atoms": ['"the nightly checks of the shop"'], "fields": []},
                {
                    "name": "CHECK",
                    "atoms": ['"coverage"'],
                    "fields": [{"name": "PARAMETER", "atoms": ['"filter=kind=unit"'], "fields": []}],
                },
            ],
        }
        runner = create_runner(ProcessAnswer(stdout=json.dumps(entity)))

        # Act
        preflight = read_preflight_entity(runner, ROOT, "nightly-gate")

        # Assert
        self.assertEqual(preflight["checks"], [{"name": "coverage", "parameters": {"filter": "kind=unit"}}])

    def test_should_hold_no_preflight_where_the_corpus_defines_no_such_entity(self):
        # Arrange
        not_defined = ProcessAnswer(
            exit_code=1, stderr="awawa show: @PREFLIGHT.nightly_gate is not defined in the workspace\n"
        )
        runner = create_runner(not_defined)

        # Act
        preflight = read_preflight_entity(runner, ROOT, "nightly-gate")

        # Assert
        self.assertIsNone(preflight)

    def test_should_read_one_preflight_written_as_an_entity_as_it_reads_it_written_as_a_toml_file(self):
        # Arrange
        runner = create_runner(ProcessAnswer(stdout=json.dumps(NIGHTLY_GATE_ENTITY)))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        (Path(directory.name) / "nightly-gate.toml").write_text(NIGHTLY_GATE_FILE)

        # Act
        from_entity = read_preflight_entity(runner, ROOT, "nightly-gate")

        # Assert
        self.assertEqual(from_entity, read_preflight_file(Path(directory.name), "nightly-gate"))
