import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.registry.require_operational_corpus import require_operational_corpus
from tests.unit.create_test_runtime import create_test_paths


class RequireOperationalCorpusTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def test_should_pass_once_the_schema_of_the_corpus_is_written(self):
        # Arrange
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")

        # Act
        outcome = require_operational_corpus(self.paths)

        # Assert
        self.assertIsNone(outcome)

    def test_should_refuse_before_brigade_init(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            require_operational_corpus(self.paths)

        # Assert
        self.assertEqual(str(refusal.exception), "the operational corpus is missing; run brigade init first")
