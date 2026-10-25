import tempfile
import unittest
from pathlib import Path

from brigade.inbox.read_inbox import Signal, read_inbox
from brigade.studies.convert_study import Study
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.record_answer_signal import record_answer_signal
from brigade.studies.study_run_context import StudyRunContext
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
PUBLICATION = AnswerPublication(title="Study trees, run 20261019T090000Z-aaaaaa", markdown="# FINDING trees_1\n")
TREES_OF_OAK = Study(
    name="trees",
    project="oak",
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="inbox",
    answer_type="FINDING",
    status="active",
)


class RecordAnswerSignalTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        self.context = StudyRunContext(
            runtime=self.runtime,
            study=TREES_OF_OAK,
            run_id=RUN_ID,
            run_directory=Path("/run"),
            equipment=create_study_equipment(),
        )

    def test_should_record_the_answer_as_a_signal_of_the_study(self):
        # Act
        record_answer_signal(self.context, PUBLICATION)

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW),
            (
                Signal(
                    id="5cc0da6f673d5bd0bbad90835dbe41e02471b3714828472350a671b943d7c0af",
                    fingerprint="study:trees:1efb66b557ad",
                    kind="study",
                    project="oak",
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={"study": "trees", "run": RUN_ID, "answer": "# FINDING trees_1\n"},
                ),
            ),
        )

    def test_should_answer_the_signal_it_recorded(self):
        # Act
        recorded = record_answer_signal(self.context, PUBLICATION)

        # Assert
        self.assertEqual(
            recorded,
            {
                "signal": "5cc0da6f673d5bd0bbad90835dbe41e02471b3714828472350a671b943d7c0af",
                "fingerprint": "study:trees:1efb66b557ad",
            },
        )
