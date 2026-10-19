import json
import tempfile
import unittest
from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.studies.convert_study import Study
from brigade.studies.start_study_run import start_study_run
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

STUDY = Study(
    name="trees",
    project="oak",
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="issue",
    answer_type="FINDING",
    status="active",
)


class StartStudyRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_scripted_runtime(self.root, ScriptedProcesses())

    def test_should_record_the_study_of_the_new_run_in_its_directory(self):
        # Act
        run_id = start_study_run(self.runtime, STUDY)

        # Assert
        record = self.root / "state" / "runs" / run_id / "study.json"
        self.assertEqual(
            json.loads(record.read_text(encoding="utf-8")), {"schema_version": 1, "study": "trees", "project": "oak"}
        )

    def test_should_record_the_order_started_in_the_ledger(self):
        # Act
        run_id = start_study_run(self.runtime, STUDY)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[0].event.to_document(),
            {"project": "oak", "kind": "study", "order": "trees", "run": run_id},
        )
