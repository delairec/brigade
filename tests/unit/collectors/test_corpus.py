import json
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.corpus import collect
from brigade.errors import EntityNotDefined
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
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
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
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
        self.assertEqual(
            self.processes.requests,
            [
                ProcessRequest(
                    argv=("awawa", "status", "PROJECT", "--json", f"{self.root}/config"),
                    cwd=f"{self.root}/config",
                    timeout_s=300.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("awawa", "show", "@PROJECT.oak", "--json", f"{self.root}/config"),
                    cwd=f"{self.root}/config",
                    timeout_s=300.0,
                    acceptable_exit_codes=(0, 1),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("awawa", "status", "PROJECT", "--json", f"{self.root}/config"),
                    cwd=f"{self.root}/config",
                    timeout_s=300.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("awawa", "show", "@PROJECT.oak", "--json", f"{self.root}/config"),
                    cwd=f"{self.root}/config",
                    timeout_s=300.0,
                    acceptable_exit_codes=(0, 1),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "v1^{commit}"),
                    cwd="/srv/oak",
                    timeout_s=10.0,
                    acceptable_exit_codes=(0, 1),
                    stdin=None,
                ),
                ProcessRequest(
                    argv=("awawa", "status", "--json", "."),
                    cwd=f"{self.root}/cache/refs/oak/bead",
                    timeout_s=300.0,
                    acceptable_exit_codes=EVERY_EXIT_CODE,
                    stdin=None,
                ),
            ],
        )

    def test_should_list_each_entity_it_is_given_whole(self):
        # Arrange
        self.create_cached_tree("HEAD", "c0ffee")
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B17", "--json", "."),
            {"type": "TASK", "name": "B17", "fields": [{"name": "STATUS", "atoms": ["implemented"]}]},
        )
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B20", "--json", "."),
            {"type": "TASK", "name": "B20", "fields": [{"name": "STATUS", "atoms": ["todo"]}]},
        )
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/oak",
            "BRIGADE_SINCE": "2026-10-01",
            "BRIGADE_PARAMS": json.dumps({"entities": "@TASK.B17,@TASK.B20"}),
        }

        # Act
        document = collect(environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document["items"],
            [
                {"type": "TASK", "name": "B17", "fields": [{"name": "STATUS", "atoms": ["implemented"]}]},
                {"type": "TASK", "name": "B20", "fields": [{"name": "STATUS", "atoms": ["todo"]}]},
            ],
        )

    def test_should_refuse_an_entity_the_corpus_does_not_define(self):
        # Arrange
        self.create_cached_tree("HEAD", "c0ffee")
        self.processes.answer(
            ("awawa", "show", "@TASK.B99", "--json", "."),
            exit_code=1,
            stderr="error: @TASK.B99 is not defined in the workspace\n",
        )
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/oak",
            "BRIGADE_SINCE": "2026-10-01",
            "BRIGADE_PARAMS": json.dumps({"entities": "@TASK.B99"}),
        }

        # Act
        with self.assertRaises(EntityNotDefined) as raised:
            collect(environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(str(raised.exception), "@TASK.B99 is not defined in the corpus of oak at HEAD")
