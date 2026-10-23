import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.studies.convert_study import Study
from brigade.studies.start_study_run import start_study_run
from tests.unit.create_test_runtime import FIXED_NOW
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-c0ffee"
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
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class StartStudyRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=ScriptedProcesses())

    def test_should_record_the_study_of_the_new_run_in_its_directory(self):
        # Act
        start_study_run(self.runtime, STUDY, RUN_ID)

        # Assert
        record = self.root / "state" / "runs" / RUN_ID / "study.json"
        self.assertEqual(
            json.loads(record.read_text(encoding="utf-8")),
            {"schema_version": 1, "study": "trees", "project": "oak", "wave": None},
        )

    def test_should_record_the_wave_a_study_reports(self):
        # Arrange
        study = dataclasses.replace(STUDY, name="wave-report", wave="oak_w2")

        # Act
        start_study_run(self.runtime, study, RUN_ID)

        # Assert
        record = self.root / "state" / "runs" / RUN_ID / "study.json"
        self.assertEqual(
            json.loads(record.read_text(encoding="utf-8")),
            {"schema_version": 1, "study": "wave-report", "project": "oak", "wave": "oak_w2"},
        )

    def test_should_record_the_order_started_in_the_ledger(self):
        # Act
        start_study_run(self.runtime, STUDY, RUN_ID)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderStarted(project="oak", kind="study", order="trees", run=RUN_ID),
                ),
            ),
        )
