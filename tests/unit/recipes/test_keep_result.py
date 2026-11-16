import tempfile
import unittest
from pathlib import Path

from brigade.recipes.keep_result import keep_result
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

HELD_RESULT = 'RESULT triage_20261018T090000Z_aaaaaa\n\tORDER "triage"\n\tRUN "20261018T090000Z-aaaaaa"\n'
NEW_RESULT = 'RESULT triage_20261019T090000Z_bbbbbb\n\tORDER "triage"\n\tRUN "20261019T090000Z-bbbbbb"\n'


class KeepResultTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=self.processes)
        self.config_root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(
            self.config_root, ("results.awawa",), "brigade order run: the result of @ORDER.triage"
        )

    def test_should_append_the_result_to_the_results_the_operational_corpus_holds(self):
        # Arrange
        (self.config_root / "results.awawa").write_text(HELD_RESULT, encoding="utf-8")

        # Act
        keep_result(self.runtime, "triage", NEW_RESULT)

        # Assert
        self.assertEqual(
            (self.config_root / "results.awawa").read_text(encoding="utf-8"),
            'RESULT triage_20261018T090000Z_aaaaaa\n\tORDER "triage"\n\tRUN "20261018T090000Z-aaaaaa"\n\n'
            'RESULT triage_20261019T090000Z_bbbbbb\n\tORDER "triage"\n\tRUN "20261019T090000Z-bbbbbb"\n',
        )

    def test_should_write_the_first_result_alone_in_a_new_results_file(self):
        # Act
        keep_result(self.runtime, "triage", NEW_RESULT)

        # Assert
        self.assertEqual(
            (self.config_root / "results.awawa").read_text(encoding="utf-8"),
            'RESULT triage_20261019T090000Z_bbbbbb\n\tORDER "triage"\n\tRUN "20261019T090000Z-bbbbbb"\n',
        )

    def test_should_commit_the_result_to_the_operational_corpus(self):
        # Act
        keep_result(self.runtime, "triage", NEW_RESULT)

        # Assert
        self.assertIn(
            ("git", "commit", "--quiet", "-m", "brigade order run: the result of @ORDER.triage"),
            self.processes.list_argvs(),
        )
