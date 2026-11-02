import tempfile
import unittest
from pathlib import Path

from brigade.mining.scrub_document import scrub_document
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ScrubDocumentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {
                "oak": (("PATH", "/srv/oak"), ("PRIVATE", r"Acme\w*"), ("PUBLIC", "AcmeOpen")),
                "elm": (("PATH", "/srv/elm"), ("PRIVATE", "Zorg")),
            },
        )

    def test_should_replace_each_private_identifier_by_the_kind_of_its_pattern(self):
        # Arrange
        document = {
            "summary": {"reason": "no transcript at /home/alice/.claude/projects/s1.jsonl"},
            "items": [
                {"content": [{"type": "text", "text": "Ask ada@example.org about AcmeBilling and Zorg."}]},
                {"content": "AcmeOpen stays public", "position": 3},
            ],
        }

        # Act
        scrubbed = scrub_document(document, self.runtime)

        # Assert
        self.assertEqual(
            scrubbed,
            {
                "summary": {"reason": "no transcript at [home path]/.claude/projects/s1.jsonl"},
                "items": [
                    {"content": [{"type": "text", "text": "Ask [e-mail address] about [private] and [private]."}]},
                    {"content": "AcmeOpen stays public", "position": 3},
                ],
            },
        )
