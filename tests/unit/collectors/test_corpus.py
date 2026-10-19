import json
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.corpus import collect
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
STATUS = {
    "types": [{"type": "TASK", "counts": {"todo": 1, "implemented": 2}}],
    "entities": [{"type": "TASK", "name": "B1", "status": "todo"}],
}


class CorpusCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        self.processes.answer_json(("awawa", "status", "--json", "."), STATUS)

    def create_cached_tree(self, ref: str, sha: str) -> None:
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"), stdout=f"{sha}\n"
        )
        (self.root / "cache" / "refs" / "oak" / sha).mkdir(parents=True)

    def test_should_count_the_entities_of_the_corpus_at_head_by_type(self):
        # Arrange
        self.create_cached_tree("HEAD", "c0ffee")
        environment = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": "{}"}

        # Act
        document = collect(environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "corpus",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": True,
                "summary": {"TASK": {"todo": 1, "implemented": 2}},
                "items": [{"type": "TASK", "name": "B1", "status": "todo"}],
            },
        )

    def test_should_read_the_corpus_at_the_ref_it_is_given(self):
        # Arrange
        self.create_cached_tree("v1", "bead")
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/oak",
            "BRIGADE_SINCE": "2026-10-01",
            "BRIGADE_PARAMS": json.dumps({"ref": "v1"}),
        }

        # Act
        collect(environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(self.processes.requests[-1].cwd, str(self.root / "cache" / "refs" / "oak" / "bead"))
