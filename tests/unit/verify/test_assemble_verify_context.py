import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.parse_configuration import Configuration
from brigade.verify.assemble_verify_context import assemble_verify_context
from brigade.verify.preflight_pull_request import PreflightDemand
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers
from tests.unit.verify.test_preflight_pull_request import BASE, HEAD, WAVE_HEAD, ForgeDescribingThePullRequestDouble

DIFF = "--- a/brigade/cart.py\n+++ b/brigade/cart.py\n@@ -0,0 +1 @@\n+def empty_cart():\n"
INSTRUCTIONS = "/srv/instructions"
JUDGED_HEAD = "1a2b3c4"
REPAIR = "--- a/brigade/cart.py\n+++ b/brigade/cart.py\n@@ -1 +1 @@\n-def cart():\n+def empty_cart():\n"
VERDICT_CHANGES = {
    "schema_version": 1,
    "ts": "2026-10-18T13:00:00Z",
    "event": "task.verdict",
    "project": "shop",
    "wave": "shop_w1",
    "task": "B1",
    "pr": 160,
    "head": JUDGED_HEAD,
    "verdict": "changes",
    "findings": [
        {
            "grade": "low",
            "file": "brigade/cart.py",
            "line": 1,
            "broken": "@RULE.function_named_after_verb",
            "summary": "cart names no action",
        }
    ],
    "login": None,
}


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
        self.assertEqual(
            document["preflight"],
            [
                {"name": "ancestry", "verdict": "pass", "findings": []},
                {"name": "checks", "verdict": "pass", "findings": []},
                {"name": "corpus", "verdict": "pass", "findings": []},
                {
                    "name": "promotion",
                    "verdict": "fail",
                    "findings": [
                        "@TASK.B1 is STATUS None, not implemented",
                        "@TASK.B1 is delivered by no pull request, not by #160",
                    ],
                },
                {"name": "untouched_files", "verdict": "pass", "findings": []},
                {"name": "privacy", "verdict": "pass", "findings": []},
                {"name": "body", "verdict": "pass", "findings": []},
                {
                    "name": "size",
                    "verdict": "info",
                    "findings": ["1 files", "1 lines", "1 packages: brigade", "0 layers"],
                },
            ],
        )

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

    def test_should_hold_neither_a_previous_verdict_nor_a_repair_diff_when_no_verdict_is_recorded(self):
        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertIsNone(document["previous"])
        self.assertIsNone(document["repair"])

    def test_should_hold_the_previous_verdict_of_the_task_at_the_pull_request(self):
        # Arrange
        write_ledger(self.root, [VERDICT_CHANGES])

        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(
            document["previous"],
            {
                "head": JUDGED_HEAD,
                "verdict": "changes",
                "findings": [
                    {
                        "id": "1",
                        "grade": "low",
                        "file": "brigade/cart.py",
                        "line": 1,
                        "broken": "@RULE.function_named_after_verb",
                        "summary": "cart names no action",
                        "answer": None,
                    }
                ],
            },
        )

    def test_should_hold_the_repair_diff_from_the_head_the_previous_verdict_judged(self):
        # Arrange
        write_ledger(self.root, [VERDICT_CHANGES])
        self.answers[("git", "diff", JUDGED_HEAD, HEAD)] = ProcessAnswer(stdout=REPAIR)

        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(
            document["repair"],
            {"command": f"git diff {JUDGED_HEAD} {HEAD}", "exit_code": 0, "stderr": "", "output": REPAIR},
        )

    def test_should_range_diff_on_the_base_of_the_wave_when_the_judged_head_was_rebased_away(self):
        # Arrange
        write_ledger(self.root, [VERDICT_CHANGES])
        self.answers[("git", "merge-base", "--is-ancestor", JUDGED_HEAD, HEAD)] = ProcessAnswer(exit_code=1)
        self.answers[("git", "merge-base", "--end-of-options", WAVE_HEAD, JUDGED_HEAD)] = ProcessAnswer(
            stdout="9999999\n"
        )

        # Act
        document = self.assemble(Configuration())

        # Assert
        self.assertEqual(document["repair"]["command"], f"git range-diff 9999999..{JUDGED_HEAD} {BASE}..{HEAD}")
