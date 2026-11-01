import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

ENVIRONMENT_OF_OAK = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "1970-01-01", "BRIGADE_PARAMS": "{}"}
LOCAL_BRANCHES_LISTING = ("git", "for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads")


def create_forge(pull_requests: list[dict]) -> ForgeDouble:
    return ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": pull_requests}})


def create_equipment(forge: ForgeDouble | None) -> CollectorEquipment:
    return CollectorEquipment(configuration=Configuration(), forge=forge, forge_name="github")


class ScanCollectorTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)

    def register_oak(self, *fields: tuple[str, str]) -> None:
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"), *fields)}
        )

    def create_cached_tree_of_main(self) -> Path:
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"), stdout="c0ffee\n"
        )
        tree = self.root / "cache" / "refs" / "oak" / "c0ffee"
        tree.mkdir(parents=True)
        return tree
