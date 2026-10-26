import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.inbox_families import collect
from brigade.inbox.dismiss_signal import dismiss_signal
from brigade.inbox.read_inbox import Signal
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
ENVIRONMENT = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "1970-01-01", "BRIGADE_PARAMS": "{}"}
RECORDED_AT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
FIRST_THREAD_ON_THE_CLI = NewSignal(
    kind="review_thread",
    project="oak",
    fingerprint="rt:101",
    evidence={"pull_request": 7, "path": "brigade/cli.py", "line": 3, "comment": "see @RULE.kiss"},
)
THREAD_ON_THE_PLANNER = NewSignal(
    kind="review_thread",
    project="oak",
    fingerprint="rt:102",
    evidence={"pull_request": 8, "path": "brigade/tick/plan.py", "line": 9, "comment": "@RULE.kiss again"},
)
SECOND_THREAD_ON_THE_CLI = NewSignal(
    kind="review_thread",
    project="oak",
    fingerprint="rt:103",
    evidence={"pull_request": 8, "path": "brigade/cli.py", "line": 40, "comment": "rename it"},
)
LINT_FAILING_ON_A_PULL_REQUEST = NewSignal(
    kind="check_run",
    project="oak",
    fingerprint="cr:oak:7:lint:abc1234",
    evidence={"pull_request": 7, "name": "lint", "conclusion": "failure"},
)
LINT_FAILING_ON_MAIN = NewSignal(
    kind="check_run",
    project="oak",
    fingerprint="cr:oak:main:lint:def5678",
    evidence={"branch": "main", "name": "lint", "conclusion": "failure"},
)
NOTE = NewSignal(kind="note", project=None, fingerprint="note:5f2b1c0d9e8a", evidence={"text": "the tick is slow"})


class InboxFamiliesCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), now=NOW, run_process=self.processes)

    def record(self, *signals: NewSignal) -> None:
        for signal in signals:
            record_signal(self.runtime.paths, RECORDED_AT, signal)

    def answer_patterns(self, patterns: dict) -> None:
        self.processes.answer_entities(self.runtime.paths.config_root, "PATTERN", patterns)

    def test_should_group_the_signals_by_rule_cited_by_file_and_by_check_name(self):
        # Arrange
        self.record(
            FIRST_THREAD_ON_THE_CLI,
            THREAD_ON_THE_PLANNER,
            SECOND_THREAD_ON_THE_CLI,
            LINT_FAILING_ON_A_PULL_REQUEST,
            LINT_FAILING_ON_MAIN,
            NOTE,
        )
        no_patterns = {}
        self.answer_patterns(no_patterns)

        # Act
        document = collect(ENVIRONMENT, self.runtime, EQUIPMENT)

        # Assert
        first_thread_on_the_cli = {
            "id": "cb358a1d6802f45160655a3b27b17a1bfd58f4fe6adba1c785d46bfe3beb051e",
            "fingerprint": "rt:101",
            "evidence": {"pull_request": 7, "path": "brigade/cli.py", "line": 3, "comment": "see @RULE.kiss"},
        }
        self.assertEqual(
            document["items"],
            [
                {
                    "by": "rule",
                    "key": "@RULE.kiss",
                    "signals": [
                        first_thread_on_the_cli,
                        {
                            "id": "698b1dbbc546f21b357b8fdcb69ceea5144cf18aa4b8d264d9356d15c1ec2c61",
                            "fingerprint": "rt:102",
                            "evidence": {
                                "pull_request": 8,
                                "path": "brigade/tick/plan.py",
                                "line": 9,
                                "comment": "@RULE.kiss again",
                            },
                        },
                    ],
                },
                {
                    "by": "file",
                    "key": "brigade/cli.py",
                    "signals": [
                        first_thread_on_the_cli,
                        {
                            "id": "89480cd0f7d57ed2256762d1272b769cb716ede258b368390dcb1f32424546ac",
                            "fingerprint": "rt:103",
                            "evidence": {
                                "pull_request": 8,
                                "path": "brigade/cli.py",
                                "line": 40,
                                "comment": "rename it",
                            },
                        },
                    ],
                },
                {
                    "by": "check",
                    "key": "lint",
                    "signals": [
                        {
                            "id": "152a89fc782cb339567797429da3dc30d92edd6265a0f30e1f71fd3b46152f4f",
                            "fingerprint": "cr:oak:7:lint:abc1234",
                            "evidence": {"pull_request": 7, "name": "lint", "conclusion": "failure"},
                        },
                        {
                            "id": "317d13df492b268ff314d59bc819fe24b930a004ce9e53b3b21b5bd21691af60",
                            "fingerprint": "cr:oak:main:lint:def5678",
                            "evidence": {"branch": "main", "name": "lint", "conclusion": "failure"},
                        },
                    ],
                },
                {
                    "by": "signal",
                    "key": "note:5f2b1c0d9e8a",
                    "signals": [
                        {
                            "id": "97986f6bdd47308c06c684b91b212c36472aa66c85c9e837511e95965ebce429",
                            "fingerprint": "note:5f2b1c0d9e8a",
                            "evidence": {"text": "the tick is slow"},
                        }
                    ],
                },
            ],
        )

    def test_should_leave_out_the_dismissed_signals_and_those_a_pattern_cites(self):
        # Arrange
        self.record(FIRST_THREAD_ON_THE_CLI, SECOND_THREAD_ON_THE_CLI, NOTE)
        dismiss_signal(
            self.runtime.paths,
            RECORDED_AT,
            Signal(
                id="97986f6bdd47308c06c684b91b212c36472aa66c85c9e837511e95965ebce429",
                fingerprint="note:5f2b1c0d9e8a",
                kind="note",
                project=None,
                count=1,
                age_s=0,
                status="new",
                evidence={"text": "the tick is slow"},
            ),
        )
        self.answer_patterns(
            {
                "P1": (
                    ("TITLE", "the cli is hard to read"),
                    ("STATUS", "ratified"),
                    ("EVIDENCE", "rt:101 see @RULE.kiss"),
                    ("ACTION", "constraint"),
                ),
                "P2": (("TITLE", "an older thread"), ("STATUS", "new"), ("EVIDENCE", "rt:10")),
            }
        )

        # Act
        document = collect(ENVIRONMENT, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document["items"],
            [
                {
                    "by": "signal",
                    "key": "rt:103",
                    "signals": [
                        {
                            "id": "89480cd0f7d57ed2256762d1272b769cb716ede258b368390dcb1f32424546ac",
                            "fingerprint": "rt:103",
                            "evidence": {
                                "pull_request": 8,
                                "path": "brigade/cli.py",
                                "line": 40,
                                "comment": "rename it",
                            },
                        }
                    ],
                }
            ],
        )

    def test_should_count_the_families_and_their_signals(self):
        # Arrange
        self.record(FIRST_THREAD_ON_THE_CLI, SECOND_THREAD_ON_THE_CLI, NOTE)
        no_patterns = {}
        self.answer_patterns(no_patterns)

        # Act
        document = collect(ENVIRONMENT, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(document["summary"], {"families": 2, "signals": 3})

    def test_should_declare_its_document_never_cached(self):
        # Arrange
        no_patterns = {}
        self.answer_patterns(no_patterns)

        # Act
        document = collect(ENVIRONMENT, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(document["cache"], False)
