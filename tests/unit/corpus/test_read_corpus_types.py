import json
import unittest
from pathlib import Path

from brigade.corpus.read_corpus_types import read_corpus_types
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

ROOT = Path("/cache/refs/oak/de446f3")
STATUS_OF_THE_CORPUS = json.dumps(
    {
        "types": [{"type": "DECISION", "total": 4}, {"type": "TASK", "total": 9}],
        "entities": [{"type": "TASK", "name": "B30", "target": "@TASK.B30"}],
    }
)


class ReadCorpusTypesTest(unittest.TestCase):
    def test_should_list_the_entity_types_of_the_corpus_at_the_root(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {("awawa", "status", "--json", str(ROOT)): ProcessAnswer(stdout=STATUS_OF_THE_CORPUS)}
        )

        # Act
        types = read_corpus_types(runner.run, ROOT)

        # Assert
        self.assertEqual(types, ["DECISION", "TASK"])
