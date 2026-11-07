import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.parse_configuration import Configuration
from brigade.verify.preflight_task_branch import BranchPreflightDemand, preflight_task_branch
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

HEAD = "2222222"
MILESTONE_HEAD = "1111111"
BASE = "0000000"
TASK_BRANCH = "feature/B1-empty-the-cart"
MILESTONE_BRANCH = "integration/cart"


def _resolve(ref: str) -> tuple[str, ...]:
    return ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")


class PreflightTaskBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.head_tree = self.paths.cache_root / "refs" / "shop" / HEAD
        self.base_tree = self.paths.cache_root / "refs" / "shop" / BASE
        (self.head_tree / "brigade").mkdir(parents=True)
        (self.head_tree / "brigade" / "cart.py").write_text("def empty_cart():\n")
        self.base_tree.mkdir(parents=True)

    def create_runner(self, unit_tests: ProcessAnswer) -> RecordingProcessRunner:
        task = {
            "fields": [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {
                    "name": "SPEC",
                    "atoms": ['"empties the cart"'],
                    "fields": [{"name": "IMPL", "atoms": ['"brigade/cart.py::def empty_cart"'], "fields": []}],
                },
            ]
        }
        return RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
                _resolve(TASK_BRANCH): ProcessAnswer(stdout=f"{HEAD}\n"),
                _resolve(MILESTONE_BRANCH): ProcessAnswer(stdout=f"{MILESTONE_HEAD}\n"),
                ("git", "merge-base", "--end-of-options", MILESTONE_HEAD, HEAD): ProcessAnswer(stdout=f"{BASE}\n"),
                _resolve(HEAD): ProcessAnswer(stdout=f"{HEAD}\n"),
                _resolve(BASE): ProcessAnswer(stdout=f"{BASE}\n"),
                ("git", "diff", "--numstat", "--text", "--end-of-options", BASE, HEAD, "--"): ProcessAnswer(
                    stdout="1\t0\tbrigade/cart.py\n"
                ),
                ("awawa", "show", "@TASK.B1", "--json", str(self.head_tree)): ProcessAnswer(stdout=json.dumps(task)),
                ("awawa", "diff", str(self.base_tree), str(self.head_tree), "--json"): ProcessAnswer(
                    stdout=json.dumps({"added": [], "changed": [], "removed": []})
                ),
                ("python3", "-m", "unittest"): unit_tests,
            }
        )

    def create_demand(self) -> BranchPreflightDemand:
        return BranchPreflightDemand(
            project=Entity(
                name="shop",
                fields=(
                    EntityField(name="PATH", value="/srv/shop"),
                    EntityField(name="FORGE", value="none"),
                    EntityField(name="ACCEPTANCE", value="python3 -m unittest"),
                ),
            ),
            task="B1",
            task_branch=TASK_BRANCH,
            base_branch=MILESTONE_BRANCH,
            configuration=Configuration(),
        )

    def test_should_run_the_acceptance_commands_on_the_head_of_the_task_branch_in_place_of_the_check_runs(self):
        # Arrange
        passing_unit_tests = ProcessAnswer()
        runtime = create_test_runtime(self.paths, run_process=self.create_runner(passing_unit_tests))

        # Act
        document = preflight_task_branch(runtime, self.create_demand())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "shop",
                "task": "B1",
                "head": HEAD,
                "checks": [
                    {"name": "ancestry", "verdict": "pass", "findings": []},
                    {
                        "name": "acceptance",
                        "verdict": "pass",
                        "findings": [],
                        "commands": [{"command": "python3 -m unittest", "exit_code": 0}],
                    },
                    {"name": "corpus", "verdict": "pass", "findings": []},
                    {"name": "promotion", "verdict": "pass", "findings": []},
                    {"name": "untouched_files", "verdict": "pass", "findings": []},
                    {"name": "privacy", "verdict": "pass", "findings": []},
                    {
                        "name": "size",
                        "verdict": "info",
                        "findings": ["1 files", "1 lines", "1 packages: brigade", "0 layers"],
                    },
                ],
            },
        )

    def test_should_fail_the_acceptance_of_the_task_on_a_failing_command(self):
        # Arrange
        failing_unit_tests = ProcessAnswer(exit_code=1, stdout="FAILED (failures=1)\n")
        runtime = create_test_runtime(self.paths, run_process=self.create_runner(failing_unit_tests))

        # Act
        document = preflight_task_branch(runtime, self.create_demand())

        # Assert
        self.assertEqual(
            document["checks"][1],
            {
                "name": "acceptance",
                "verdict": "fail",
                "findings": ["python3 -m unittest exited 1", "FAILED (failures=1)"],
                "commands": [{"command": "python3 -m unittest", "exit_code": 1}],
            },
        )
