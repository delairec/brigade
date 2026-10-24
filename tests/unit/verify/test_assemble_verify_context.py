import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.parse_configuration import Configuration
from brigade.verify.assemble_verify_context import assemble_verify_context
from brigade.verify.preflight_pull_request import PreflightDemand
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers
from tests.unit.verify.test_preflight_pull_request import BASE, HEAD, WAVE_HEAD, ForgeDescribingThePullRequestDouble

DIFF = "--- a/brigade/cart.py\n+++ b/brigade/cart.py\n@@ -0,0 +1 @@\n+def empty_cart():\n"
INSTRUCTIONS = "/srv/instructions"


class AssembleVerifyContextTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.head_tree = self.paths.cache_root / "refs" / "shop" / HEAD
        (self.head_tree / "brigade").mkdir(parents=True)
        (self.paths.cache_root / "refs" / "shop" / BASE).mkdir(parents=True)
        self.answers = {
            **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
            (
                "git",
                "rev-parse",
                "--verify",
                "--quiet",
                "--end-of-options",
                "refs/remotes/origin/integration/w1^{commit}",
            ): ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
            ("git", "merge-base", "--end-of-options", WAVE_HEAD, HEAD): ProcessAnswer(stdout=f"{BASE}\n"),
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{HEAD}^{{commit}}"): ProcessAnswer(
                stdout=f"{HEAD}\n"
            ),
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{BASE}^{{commit}}"): ProcessAnswer(
                stdout=f"{BASE}\n"
            ),
            ("git", "diff", "--numstat", "--text", "--end-of-options", BASE, HEAD, "--"): ProcessAnswer(
                stdout="1\t0\tbrigade/cart.py\n"
            ),
            ("git", "diff", BASE, HEAD): ProcessAnswer(stdout=DIFF),
            ("awawa", "show", "@TASK.B1", "--json", str(self.head_tree)): ProcessAnswer(
                stdout=json.dumps({"fields": []})
            ),
            ("awawa", "diff", str(self.paths.cache_root / "refs" / "shop" / BASE), str(self.head_tree), "--json"): (
                ProcessAnswer(stdout=json.dumps({"added": [], "changed": [], "removed": []}))
            ),
            ("awawa", "context", "@TASK.B1", "--with-schema", "."): ProcessAnswer(stdout="TASK B1\n"),
            ("awawa", "status", "TRIGGER", "--where", "KIND==path", "--json", INSTRUCTIONS): ProcessAnswer(
                stdout=json.dumps({"entities": []})
            ),
        }
        self.runner = RecordingProcessRunner(self.answers)

    def assemble(self, configuration: Configuration) -> dict:
        demand = PreflightDemand(
            project=Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),)),
            task="B1",
            wave_branch="integration/w1",
            pr=160,
            forge=ForgeDescribingThePullRequestDouble(),
            environment={},
            configuration=configuration,
        )
        return assemble_verify_context(create_test_runtime(self.paths, run_process=self.runner), demand)

    def test_should_print_the_diff_from_the_merge_base_of_the_wave_to_the_head(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(
            document["diff"], {"command": f"git diff {BASE} {HEAD}", "exit_code": 0, "stderr": "", "output": DIFF}
        )

    def test_should_print_the_context_of_the_task_read_in_the_tree_of_the_head(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(
            document["context"][0],
            {"command": "awawa context @TASK.B1 --with-schema .", "exit_code": 0, "stderr": "", "output": "TASK B1\n"},
        )

    def test_should_print_no_rules_without_an_instructions_corpus(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertIsNone(document["rules"])

    def test_should_print_the_rules_of_the_path_triggers_of_the_instructions_corpus(self):
        # Arrange
        no_path_trigger = []

        # Act
        document = self.assemble(Configuration(instructions=INSTRUCTIONS))

        # Assert
        self.assertEqual(document["rules"], no_path_trigger)

    def test_should_print_the_grades_of_a_finding(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(document["grades"], ["critical", "high", "medium", "low"])

    def test_should_name_the_project_the_pull_request_its_task_and_its_head(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(document["project"], "shop")
        self.assertEqual(document["pr"], 160)
        self.assertEqual(document["task"], "B1")
        self.assertEqual(document["head"], HEAD)

    def test_should_print_the_closure_of_the_task_read_in_the_tree_of_the_head(self):
        # Arrange
        self.answers[("awawa", "lint", "--closure", "@TASK.B1", ".")] = ProcessAnswer(stdout="closure of B1\n")

        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(
            document["context"][1],
            {"command": "awawa lint --closure @TASK.B1 .", "exit_code": 0, "stderr": "", "output": "closure of B1\n"},
        )

    def test_should_print_the_findings_of_the_preflight(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(document["preflight"][0], {"name": "ancestry", "verdict": "pass", "findings": []})

    def test_should_print_the_rules_of_the_path_triggers_matching_a_file_of_the_diff_in_their_order(self):
        # Arrange
        self.answers[("awawa", "status", "TRIGGER", "--where", "KIND==path", "--json", INSTRUCTIONS)] = ProcessAnswer(
            stdout=json.dumps(
                {
                    "entities": [
                        {"name": "python_code", "file": "triggers.awawa", "line": 9},
                        {"name": "cart_code", "file": "triggers.awawa", "line": 3},
                        {"name": "docs_file", "file": "triggers.awawa", "line": 6},
                    ]
                }
            )
        )
        self.answers[("awawa", "show", "@TRIGGER.python_code", "--json", INSTRUCTIONS)] = ProcessAnswer(
            stdout=json.dumps(
                {"fields": [{"name": "GLOB", "atoms": ['"docs/**"']}, {"name": "GLOB", "atoms": ['"**/*.py"']}]}
            )
        )
        self.answers[("awawa", "show", "@TRIGGER.cart_code", "--json", INSTRUCTIONS)] = ProcessAnswer(
            stdout=json.dumps({"fields": [{"name": "GLOB", "atoms": ['"brigade/cart.py"']}]})
        )
        self.answers[("awawa", "show", "@TRIGGER.docs_file", "--json", INSTRUCTIONS)] = ProcessAnswer(
            stdout=json.dumps({"fields": [{"name": "GLOB", "atoms": ['"docs/**"']}]})
        )
        self.answers[
            ("awawa", "context", "@TRIGGER.cart_code", "--depth", "1", "--skip", "reasoning", INSTRUCTIONS)
        ] = ProcessAnswer(stdout="RULE cart\n")
        self.answers[
            ("awawa", "context", "@TRIGGER.python_code", "--depth", "1", "--skip", "reasoning", INSTRUCTIONS)
        ] = ProcessAnswer(stdout="RULE python\n")

        # Act
        document = self.assemble(Configuration(instructions=INSTRUCTIONS))

        # Assert
        self.assertEqual(
            document["rules"],
            [
                {
                    "trigger": "cart_code",
                    "command": f"awawa context @TRIGGER.cart_code --depth 1 --skip reasoning {INSTRUCTIONS}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": "RULE cart\n",
                },
                {
                    "trigger": "python_code",
                    "command": f"awawa context @TRIGGER.python_code --depth 1 --skip reasoning {INSTRUCTIONS}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": "RULE python\n",
                },
            ],
        )
