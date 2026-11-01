import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.inbox.read_inbox import Signal, read_inbox
from brigade.studies.convert_study import Study
from brigade.studies.record_scan_signals import record_scan_signals
from brigade.studies.study_run_context import StudyRunContext
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
CORPUS_LINT_OF_OAK = Study(
    name="corpus_lint_oak",
    project="oak",
    question=None,
    collectors=("corpus-lint", "corpus-fmt"),
    slot="none",
    every="24h",
    output="inbox",
    answer_type="ANSWER",
    status="active",
)
HEALTH = Study(
    name="health",
    project=None,
    question=None,
    collectors=("stale-worktrees",),
    slot="none",
    every="24h",
    output="inbox",
    answer_type="ANSWER",
    status="active",
)
DIAGNOSTIC = {"rule": "L003", "file": "corpus/tasks.awawa", "fingerprint": "L003:corpus/tasks.awawa:TASK.B1"}
UNFORMATTED_FILE = {"file": "corpus/tasks.awawa", "fingerprint": "corpus/tasks.awawa"}
STALE_WORKTREE = {"path": "/srv/oak/.brigade/worktrees/B1", "fingerprint": "/srv/oak/.brigade/worktrees/B1"}
ITEM_WITHOUT_FINGERPRINT = {"file": "corpus/tasks.awawa"}


class RecordScanSignalsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))
        self.run_directory = self.root / "state" / "runs" / RUN_ID

    def collect(self, documents: dict) -> None:
        collected = []
        for index, (collector, items) in enumerate(documents.items(), start=1):
            path = self.run_directory / "collectors" / str(index) / "document.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"collector": collector, "summary": {}, "items": items}), encoding="utf-8")
            collected.append({"collector": collector, "summary": {}, "document": str(path)})
        (self.run_directory / "steps").mkdir(parents=True)
        (self.run_directory / "steps" / "collect.json").write_text(
            json.dumps({"collected": collected}), encoding="utf-8"
        )

    def create_context(self, study: Study) -> StudyRunContext:
        return StudyRunContext(
            runtime=self.runtime,
            study=study,
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=create_study_equipment(),
        )

    def test_should_record_one_signal_per_item_fingerprinted_by_the_study_the_project_and_the_item(self):
        # Arrange
        self.collect({"corpus-lint": [DIAGNOSTIC], "corpus-fmt": [UNFORMATTED_FILE]})

        # Act
        record_scan_signals(self.create_context(CORPUS_LINT_OF_OAK))

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW),
            (
                Signal(
                    id="37d107242e0509152526c9589779126fa7e27db355f292f7506a93441d28129f",
                    fingerprint="corpus_lint_oak:oak:L003:corpus/tasks.awawa:TASK.B1",
                    kind="scan",
                    project="oak",
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={
                        "rule": "L003",
                        "file": "corpus/tasks.awawa",
                        "fingerprint": "L003:corpus/tasks.awawa:TASK.B1",
                    },
                ),
                Signal(
                    id="c78d85cf5f8f4e9803ce4934376245c0c059ffa090fc156ce2ebdab5dc6862ea",
                    fingerprint="corpus_lint_oak:oak:corpus/tasks.awawa",
                    kind="scan",
                    project="oak",
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={"file": "corpus/tasks.awawa", "fingerprint": "corpus/tasks.awawa"},
                ),
            ),
        )

    def test_should_leave_the_project_of_the_fingerprint_empty_for_a_study_naming_none(self):
        # Arrange
        self.collect({"stale-worktrees": [STALE_WORKTREE]})

        # Act
        record_scan_signals(self.create_context(HEALTH))

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW),
            (
                Signal(
                    id="53b32703b9316c3633b041e48d56ccc290977d28ff28870b564ec1ea862d1539",
                    fingerprint="health::/srv/oak/.brigade/worktrees/B1",
                    kind="scan",
                    project=None,
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={
                        "path": "/srv/oak/.brigade/worktrees/B1",
                        "fingerprint": "/srv/oak/.brigade/worktrees/B1",
                    },
                ),
            ),
        )

    def test_should_record_no_signal_when_the_collectors_print_no_item(self):
        # Arrange
        no_item = []
        self.collect({"corpus-lint": no_item, "corpus-fmt": no_item})

        # Act
        record_scan_signals(self.create_context(CORPUS_LINT_OF_OAK))

        # Assert
        self.assertEqual(read_inbox(self.runtime.paths.state_root, FIXED_NOW), ())

    def test_should_refuse_an_item_without_a_fingerprint_naming_its_collector(self):
        # Arrange
        self.collect({"corpus-lint": [DIAGNOSTIC], "corpus-fmt": [ITEM_WITHOUT_FINGERPRINT]})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_scan_signals(self.create_context(CORPUS_LINT_OF_OAK))

        # Assert
        self.assertEqual(str(refusal.exception), "the collector corpus-fmt printed an item without a fingerprint")

    def test_should_record_no_signal_of_a_run_an_item_without_a_fingerprint_fails(self):
        # Arrange
        self.collect({"corpus-lint": [DIAGNOSTIC], "corpus-fmt": [ITEM_WITHOUT_FINGERPRINT]})

        # Act
        with self.assertRaises(BrigadeError):
            record_scan_signals(self.create_context(CORPUS_LINT_OF_OAK))

        # Assert
        self.assertEqual(read_inbox(self.runtime.paths.state_root, FIXED_NOW), ())
