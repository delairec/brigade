import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.parse_configuration import Configuration
from brigade.verify.preflight_task_branch import BranchPreflightDemand, preflight_task_branch
from tests.unit.create_recipe_answers import create_recipe_answers
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

    def create_runner(self, unit_tests: ProcessAnswer, references: tuple[dict, ...] = ()) -> RecordingProcessRunner:
        task = {
            "fields": [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {
                    "name": "SPEC",
                    "atoms": ['"empties the cart"'],
                    "fields": [{"name": "IMPL", "atoms": ['"brigade/cart.py::def empty_cart"'], "fields": []}],
                },
                *references,
            ]
        }
        return RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
                **create_recipe_answers(self.head_tree, {"acceptance": (("python3", "-m", "unittest"),)}),
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
                ),
            ),
            task="B1",
            task_branch=TASK_BRANCH,
            base_branch=MILESTONE_BRANCH,
            configuration=Configuration(),
        )

    def test_should_judge_the_task_against_the_files_its_branch_changes(self):
        # Arrange
        cart_reference = {
            "name": "REFERENCE",
            "atoms": ['"brigade/cart.py"'],
            "fields": [{"name": "COVERS", "atoms": ['"cart"'], "fields": []}],
        }
        runner = self.create_runner(ProcessAnswer(), (cart_reference,))
        runtime = create_test_runtime(self.paths, run_process=runner)

        # Act
        document = preflight_task_branch(runtime, self.create_demand())

        # Assert
        self.assertIn(
            {
                "name": "promotion",
                "result": "fail",
                "findings": [
                    (
                        "brigade/cart.py is the REFERENCE @TASK.B1 is judged against, and its branch changes it:"
                        " a task delivering its reference says so with REVISES"
                    )
                ],
            },
            document["checks"],
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
                    {"name": "ancestry", "result": "ok", "findings": []},
                    {
                        "name": "acceptance",
                        "result": "ok",
                        "findings": [],
                        "commands": [
                            {"command": "python3 -m unittest", "exit_code": 0, "duration_ms": 0, "output": ""}
                        ],
                    },
                    {
                        "name": "corpus",
                        "result": "ok",
                        "findings": [],
                        "commands": [
                            {"command": "awawa fmt --check .", "exit_code": 0, "duration_ms": 0, "output": ""},
                            {"command": "awawa lint --strict .", "exit_code": 0, "duration_ms": 0, "output": ""},
                        ],
                    },
                    {"name": "promotion", "result": "ok", "findings": []},
                    {"name": "untouched_files", "result": "ok", "findings": []},
                    {"name": "privacy", "result": "ok", "findings": []},
                    {
                        "name": "size",
                        "result": "info",
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
                "result": "fail",
                "findings": ["python3 -m unittest exited 1", "FAILED (failures=1)"],
                "commands": [
                    {
                        "command": "python3 -m unittest",
                        "exit_code": 1,
                        "duration_ms": 0,
                        "output": "FAILED (failures=1)\n",
                    }
                ],
            },
        )


class PreflightTaskBranchOfAnAreaTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.head_tree = self.paths.cache_root / "refs" / "shop" / HEAD
        self.base_tree = self.paths.cache_root / "refs" / "shop" / BASE
        (self.head_tree / "brigade").mkdir(parents=True)
        (self.base_tree / "brigade").mkdir(parents=True)

    def run_preflight(
        self, task_fields: list[dict], numstat: str = "", moved: list[dict] | None = None
    ) -> tuple[RecordingProcessRunner, dict]:
        head_area = self.head_tree / "brigade"
        fields = {"PATH": "/srv/shop", "CORPUS": "brigade", "MODE": "area"}
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": fields}),
                **create_recipe_answers(head_area, {"acceptance": (("python3", "-m", "unittest"),)}),
                _resolve(TASK_BRANCH): ProcessAnswer(stdout=f"{HEAD}\n"),
                _resolve(MILESTONE_BRANCH): ProcessAnswer(stdout=f"{MILESTONE_HEAD}\n"),
                ("git", "merge-base", "--end-of-options", MILESTONE_HEAD, HEAD): ProcessAnswer(stdout=f"{BASE}\n"),
                _resolve(HEAD): ProcessAnswer(stdout=f"{HEAD}\n"),
                _resolve(BASE): ProcessAnswer(stdout=f"{BASE}\n"),
                ("git", "diff", "--numstat", "--text", "--end-of-options", BASE, HEAD, "--"): ProcessAnswer(
                    stdout=numstat
                ),
                ("awawa", "show", "@TASK.B1", "--json", str(head_area)): ProcessAnswer(
                    stdout=json.dumps({"fields": task_fields})
                ),
                ("awawa", "diff", str(self.base_tree / "brigade"), str(head_area), "--json"): ProcessAnswer(
                    stdout=json.dumps({"added": [], "changed": moved or [], "removed": []})
                ),
                ("python3", "-m", "unittest"): ProcessAnswer(),
            }
        )
        demand = BranchPreflightDemand(
            project=Entity(
                name="shop",
                fields=(
                    EntityField(name="PATH", value="/srv/shop"),
                    EntityField(name="CORPUS", value="brigade"),
                    EntityField(name="MODE", value="area"),
                    EntityField(name="FORGE", value="none"),
                ),
            ),
            task="B1",
            task_branch=TASK_BRANCH,
            base_branch=MILESTONE_BRANCH,
            configuration=Configuration(),
        )
        return runner, preflight_task_branch(create_test_runtime(self.paths, run_process=runner), demand)

    def test_should_read_the_area_and_run_the_acceptance_at_the_root_of_the_repository(self):
        # Arrange
        implemented = [{"name": "STATUS", "atoms": ["implemented"], "fields": []}]

        # Act
        runner, _document = self.run_preflight(implemented)

        # Assert
        self.assertIn((str(self.head_tree), ("python3", "-m", "unittest")), runner.commands)
        self.assertIn((str(self.head_tree / "brigade"), ("awawa", "fmt", "--check", ".")), runner.commands)

    def test_should_match_the_files_changed_in_the_area_with_the_entities_moved_there(self):
        # Arrange
        implemented = [{"name": "STATUS", "atoms": ["implemented"], "fields": []}]

        # Act
        _runner, document = self.run_preflight(
            implemented, numstat="1\t1\tbrigade/tasks.awawa\n", moved=[{"file": "tasks.awawa"}]
        )

        # Assert
        self.assertIn({"name": "untouched_files", "result": "ok", "findings": []}, document["checks"])

    def test_should_resolve_the_anchors_of_the_task_from_the_root_of_the_repository(self):
        # Arrange
        (self.head_tree / "src").mkdir()
        (self.head_tree / "src" / "cart.py").write_text("def add_item():\n")
        anchored_outside_the_area = [
            {"name": "STATUS", "atoms": ["implemented"], "fields": []},
            {
                "name": "SPEC",
                "atoms": ['"adds an item"'],
                "fields": [{"name": "IMPL", "atoms": ['"src/cart.py::def add_item"'], "fields": []}],
            },
        ]

        # Act
        _runner, document = self.run_preflight(anchored_outside_the_area)

        # Assert
        self.assertIn({"name": "promotion", "result": "ok", "findings": []}, document["checks"])
