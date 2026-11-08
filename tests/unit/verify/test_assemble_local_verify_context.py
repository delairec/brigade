import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.parse_configuration import Configuration
from brigade.verify.assemble_local_verify_context import assemble_local_verify_context
from brigade.verify.preflight_task_branch import BranchPreflightDemand
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

HEAD = "2222222"
MILESTONE_HEAD = "1111111"
BASE = "0000000"
TASK_BRANCH = "feature/B1-empty-the-cart"
MILESTONE_BRANCH = "integration/cart"
DIFF = "--- a/brigade/cart.py\n+++ b/brigade/cart.py\n@@ -0,0 +1 @@\n+def empty_cart():\n"


def _resolve(ref: str) -> tuple[str, ...]:
    return ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")


class AssembleLocalVerifyContextTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        head_tree = self.paths.cache_root / "refs" / "shop" / HEAD
        base_tree = self.paths.cache_root / "refs" / "shop" / BASE
        (head_tree / "brigade").mkdir(parents=True)
        base_tree.mkdir(parents=True)
        self.runner = RecordingProcessRunner(
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
                ("git", "diff", BASE, HEAD): ProcessAnswer(stdout=DIFF),
                ("awawa", "show", "@TASK.B1", "--json", str(head_tree)): ProcessAnswer(
                    stdout=json.dumps({"fields": []})
                ),
                ("awawa", "diff", str(base_tree), str(head_tree), "--json"): ProcessAnswer(
                    stdout=json.dumps({"added": [], "changed": [], "removed": []})
                ),
                ("awawa", "context", "@TASK.B1", "--with-schema", "."): ProcessAnswer(stdout="TASK B1\n"),
            }
        )

    def assemble(self) -> dict:
        demand = BranchPreflightDemand(
            project=Entity(
                name="shop",
                fields=(EntityField(name="PATH", value="/srv/shop"), EntityField(name="FORGE", value="none")),
            ),
            task="B1",
            task_branch=TASK_BRANCH,
            base_branch=MILESTONE_BRANCH,
            configuration=Configuration(),
        )
        return assemble_local_verify_context(create_test_runtime(self.paths, run_process=self.runner), demand)

    def test_should_print_the_diff_of_the_task_branch_from_its_merge_base_with_the_branch_of_its_milestone(self):
        # Act
        document = self.assemble()

        # Assert
        self.assertEqual(
            document["diff"], {"command": f"git diff {BASE} {HEAD}", "exit_code": 0, "stderr": "", "output": DIFF}
        )

    def test_should_judge_the_task_with_no_pull_request(self):
        # Act
        document = self.assemble()

        # Assert
        self.assertIsNone(document["pr"])

    def test_should_print_the_checks_of_the_preflight_of_the_task_branch(self):
        # Act
        document = self.assemble()

        # Assert
        self.assertEqual(document["preflight"][0], {"name": "ancestry", "verdict": "pass", "findings": []})
