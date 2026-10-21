import unittest
from pathlib import Path

from brigade.planning.read_entity_sites import EntitySite, read_entity_sites

ROOT = Path("/srv/oak")
DOCUMENTS = {
    (ROOT, ("status",)): {
        "entities": [
            {"type": "TASK", "name": "B12", "file": "/srv/oak/corpus/tasks.awawa", "line": 4},
            {"type": "DECISION", "name": "OneStore", "file": "corpus/decisions.awawa", "line": 1},
        ]
    }
}


def read_awawa_document(root: Path, arguments: tuple[str, ...]) -> dict:
    return DOCUMENTS[(root, arguments)]


class ReadEntitySitesTest(unittest.TestCase):
    def test_should_locate_each_entity_by_its_file_relative_to_the_root_and_its_line(self):
        # Act
        sites = read_entity_sites(read_awawa_document, ROOT)

        # Assert
        self.assertEqual(
            sites,
            (
                EntitySite(type="TASK", name="B12", file="corpus/tasks.awawa", line=4),
                EntitySite(type="DECISION", name="OneStore", file="corpus/decisions.awawa", line=1),
            ),
        )
