import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_document_plugin import name_document_plugin


class NameDocumentPluginTest(unittest.TestCase):
    def test_should_route_a_file_to_the_plugin_of_its_extension(self):
        for path, plugin in [("/state/runs/r1/progress.md", "markdown"), ("/state/runs/r1/progress.awawa", "awawa")]:
            with self.subTest(path=path):
                # Act
                name = name_document_plugin(Path(path))

                # Assert
                self.assertEqual(name, plugin)

    def test_should_refuse_an_extension_no_plugin_reads_naming_the_file(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            name_document_plugin(Path("/state/runs/r1/progress.txt"))

        # Assert
        self.assertEqual(str(refusal.exception), "no document plugin reads /state/runs/r1/progress.txt")
