import tempfile
import unittest
from pathlib import Path

from brigade.recipes.hand_result import ResultHandoff, hand_result
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment
from tests.value_matchers import PatternMatcher

RUN_ID = "20261019T090000Z-aaaaaa"
RESULT = 'RESULT triage_20261019T090000Z_aaaaaa\n\tORDER "triage"\n\tNARRATIVE "two issues stay open"\n'


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "RESULT", "name": "triage_20261019T090000Z_aaaaaa", "fields": []}]}


class HandResultTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=self.processes)
        self.run_directory = root / "state" / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "answer.awawa").write_text(RESULT, encoding="utf-8")

    def create_handoff(self, output: str) -> ResultHandoff:
        return ResultHandoff(
            runtime=self.runtime,
            order="triage",
            project="shop",
            output=output,
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=create_study_equipment(document=DocumentDouble()),
        )

    def test_should_hand_nothing_further_for_an_entity_output_the_kept_result_already_is(self):
        # Act
        handed = hand_result(self.create_handoff("entity:RESULT"))

        # Assert
        self.assertEqual(handed, {})
        self.assertEqual(self.processes.list_argvs(), [])

    def test_should_record_the_result_into_the_inbox(self):
        # Act
        handed = hand_result(self.create_handoff("inbox"))

        # Assert
        self.assertEqual(
            handed,
            {"signal": PatternMatcher("[A-Za-z0-9-]+"), "fingerprint": PatternMatcher("study:triage:[0-9a-f]{12}")},
        )
