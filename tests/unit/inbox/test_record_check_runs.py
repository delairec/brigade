import json
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.inbox.record_check_runs import CheckRunsRecording, record_check_runs
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.system.parse_configuration import Configuration
from brigade.system.resolve_collector import CollectorAnswer
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

FAILED_BUILD_ON_MAIN = {
    "pull_request": None,
    "branch": "main",
    "head": "4567def",
    "name": "build",
    "conclusion": "failure",
    "link": "https://github.com/octo/oak/actions/runs/7/job/70",
    "first_failing_step": "Compile",
}
NO_FORGE_NEEDED = None


class CollectorDouble:
    name = "check-runs"
    command = "brigade.collectors.check_runs"

    def __init__(self, items: list[dict]):
        self.items = items

    def collect(self, environment: dict, runtime, equipment) -> CollectorAnswer:
        document = {
            "schema_version": 1,
            "collector": "check-runs",
            "collected_at": "2026-10-19T09:00:00Z",
            "cache": False,
            "summary": {},
            "items": self.items,
        }
        return CollectorAnswer(exit_code=0, stdout=json.dumps(document), stderr="", duration_ms=0)


class RecordCheckRunsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))
        self.signals = self.root / "state" / "inbox" / "signals.jsonl"

    def create_recording(self, items: list[dict]) -> CheckRunsRecording:
        return CheckRunsRecording(
            project="oak",
            path=Path("/srv/oak"),
            collector=CollectorDouble(items),
            equipment=CollectorEquipment(configuration=Configuration(), forge=NO_FORGE_NEEDED, forge_name="github"),
        )

    def read_signal_lines(self) -> list[dict]:
        return list(map(json.loads, self.signals.read_text(encoding="utf-8").splitlines()))

    def test_should_record_each_failing_check_run_as_a_signal_of_kind_check_run(self):
        # Act
        record_check_runs(self.runtime, self.create_recording([FAILED_BUILD_ON_MAIN]))

        # Assert
        self.assertEqual(
            self.read_signal_lines(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "recorded",
                    "kind": "check_run",
                    "project": "oak",
                    "fingerprint": "cr:oak:main:build:4567def",
                    "evidence": {
                        "pull_request": None,
                        "branch": "main",
                        "head": "4567def",
                        "name": "build",
                        "conclusion": "failure",
                        "link": "https://github.com/octo/oak/actions/runs/7/job/70",
                        "first_failing_step": "Compile",
                    },
                }
            ],
        )

    def test_should_not_record_again_a_check_run_the_inbox_holds(self):
        # Arrange
        held = NewSignal(kind="check_run", project="oak", fingerprint="cr:oak:main:build:4567def", evidence={})
        record_signal(self.runtime.paths, self.runtime.now, held)

        # Act
        record_check_runs(self.runtime, self.create_recording([FAILED_BUILD_ON_MAIN]))

        # Assert
        self.assertEqual(
            self.read_signal_lines(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "recorded",
                    "kind": "check_run",
                    "project": "oak",
                    "fingerprint": "cr:oak:main:build:4567def",
                    "evidence": {},
                }
            ],
        )

    def test_should_refuse_a_check_run_lacking_its_head_naming_the_collector(self):
        # Arrange
        headless = {"pull_request": None, "branch": "main", "name": "build"}

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_check_runs(self.runtime, self.create_recording([headless]))

        # Assert
        self.assertEqual(str(refusal.exception), "collector check-runs answered a check run that lacks the key head")
