import functools
import json
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.preflights.run_preflight import PreflightRun, run_preflight
from brigade.system.parse_configuration import Configuration
from brigade.system.resolve_plugin import resolve_plugin
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NO_PLUGIN_SOURCES = None
NIGHTLY = (
    "schema_version = 1\n"
    'name = "nightly"\n'
    'description = "the nightly checks of the shop"\n'
    'collectors = [{ name = "notes", parameters = { depth = "1" } }]\n'
    'checks = [{ name = "coverage" }]\n'
)
NOTES = {
    "schema_version": 1,
    "collector": "notes",
    "collected_at": "2026-10-19T09:00:00Z",
    "cache": False,
    "summary": {"open": 2},
    "items": [],
}
FAILED_COVERAGE = {"schema_version": 1, "name": "coverage", "verdict": "fail", "findings": ["cart.py: 80%"]}
PASSED_COVERAGE = {"schema_version": 1, "name": "coverage", "verdict": "pass", "findings": []}


def refuse_to_resolve_a_client(name: str):
    raise AssertionError(f"the client {name} should not be resolved")


def place_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)


class RunPreflightTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.project = root / "shop"
        self.preflights = root / "preflights"
        self.preflights.mkdir()
        (self.preflights / "nightly.toml").write_text(NIGHTLY)
        self.collector = self.project / ".brigade" / "collectors" / "notes"
        self.check = self.project / ".brigade" / "checks" / "coverage"
        place_executable(self.collector)
        place_executable(self.check)
        self.paths = create_test_paths(root)

    def run_nightly(self, name: str, coverage: dict) -> tuple[RecordingProcessRunner, object]:
        runner = RecordingProcessRunner(
            {
                (str(self.collector),): ProcessAnswer(stdout=json.dumps(NOTES)),
                (str(self.check),): ProcessAnswer(stdout=json.dumps(coverage)),
            }
        )
        runtime = create_test_runtime(
            self.paths, run_process=runner, resolve_plugin=functools.partial(resolve_plugin, sources=NO_PLUGIN_SOURCES)
        )
        run = PreflightRun(
            name=name,
            project=self.project,
            parameters={"pr": "42"},
            equipment=CollectorEquipment(
                configuration=Configuration(),
                forge=None,
                forge_name="none",
                resolve_client=refuse_to_resolve_a_client,
            ),
            preflights=self.preflights,
        )
        return runner, run_preflight(run, runtime)

    def test_should_fail_a_preflight_a_check_of_which_fails(self):
        # Act
        _runner, outcome = self.run_nightly("nightly", FAILED_COVERAGE)

        # Assert
        self.assertEqual(outcome.verdict, "fail")

    def test_should_pass_a_preflight_every_check_of_which_passes(self):
        # Act
        _runner, outcome = self.run_nightly("nightly", PASSED_COVERAGE)

        # Assert
        self.assertEqual(outcome.verdict, "pass")

    def test_should_return_the_verdict_and_the_findings_of_each_check(self):
        # Act
        _runner, outcome = self.run_nightly("nightly", FAILED_COVERAGE)

        # Assert
        self.assertEqual(outcome.checks, [{"name": "coverage", "verdict": "fail", "findings": ["cart.py: 80%"]}])

    def test_should_hand_each_check_the_parameters_and_the_documents_of_the_collectors(self):
        # Act
        runner, _outcome = self.run_nightly("nightly", PASSED_COVERAGE)

        # Assert
        self.assertEqual(
            json.loads(runner.requests[-1].stdin),
            {
                "schema_version": 1,
                "project": str(self.project),
                "parameters": {"pr": "42"},
                "collected": {
                    "notes": {
                        "schema_version": 1,
                        "collector": "notes",
                        "collected_at": "2026-10-19T09:00:00Z",
                        "cache": False,
                        "summary": {"open": 2},
                        "items": [],
                    }
                },
            },
        )

    def test_should_hand_each_collector_its_parameters_and_those_of_the_command_line(self):
        # Act
        runner, _outcome = self.run_nightly("nightly", PASSED_COVERAGE)

        # Assert
        self.assertEqual(json.loads(runner.requests[0].environment["BRIGADE_PARAMS"]), {"depth": "1", "pr": "42"})

    def test_should_refuse_a_name_no_preflight_carries(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.run_nightly("weekly", PASSED_COVERAGE)

        # Assert
        self.assertEqual(str(refusal.exception), f"no preflight weekly: no weekly.toml in {self.preflights}")
