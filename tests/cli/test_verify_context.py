import json
from pathlib import Path
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task import INSTRUCTIONS_SCHEMA, INSTRUCTIONS_TRIGGERS, WAVE_BRANCH
from tests.cli.test_verify_preflight import CLI_KEYS, VerifyPreflightTestCase


class VerifyContextTestCase(VerifyPreflightTestCase):
    def run_verify_context(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "verify",
            "context",
            *arguments,
            environment=self.describe_environment(),
            cwd=self.project.path,
        )

    def read_document(self) -> dict:
        completed = self.run_verify_context("42", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def read_wave_head(self) -> str:
        return self.project.run_git("rev-parse", WAVE_BRANCH).strip()


class BrigadeVerifyContextOfAPullRequestTest(VerifyContextTestCase):
    def test_should_name_the_pull_request_its_task_and_its_head(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["project"], "shop")
        self.assertEqual(document["pr"], 42)
        self.assertEqual(document["task"], "S3")
        self.assertEqual(document["head"], self.read_head())

    def test_should_print_the_awawa_context_of_the_task_at_the_head_under_its_command_line(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["context"][0],
            {"command": "awawa context @TASK.S3 --with-schema .", "exit_code": 0, "stderr": "", "output": ANY},
        )

    def test_should_print_the_task_as_the_head_of_the_pull_request_delivers_it(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertIn("\tDELIVERED_BY 42\n", document["context"][0]["output"])

    def test_should_print_the_closure_of_the_task_under_its_command_line(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["context"][1],
            {"command": "awawa lint --closure @TASK.S3 .", "exit_code": 0, "stderr": "", "output": ANY},
        )

    def test_should_print_the_diff_of_the_pull_request_against_the_head_of_its_wave(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["diff"],
            {
                "command": f"git diff {self.read_wave_head()} {self.read_head()}",
                "exit_code": 0,
                "stderr": "",
                "output": ANY,
            },
        )

    def test_should_print_the_lines_the_pull_request_adds_in_its_diff(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertIn("+def empty_cart(cart):\n", document["diff"]["output"])

    def test_should_print_the_findings_of_the_preflight(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["preflight"][0], {"name": "ancestry", "verdict": "pass", "findings": []})

    def test_should_print_the_grades_of_a_finding_the_most_serious_first(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["grades"], ["critical", "high", "medium", "low"])

    def test_should_print_no_rules_without_an_instructions_corpus(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertIsNone(document["rules"])

    def test_should_print_each_section_under_its_heading(self):
        # Act
        completed = self.run_verify_context("42")

        # Assert
        self.assertTrue(completed.stdout.startswith("# task\n$ awawa context @TASK.S3 --with-schema .\nexit 0\n"))
        self.assertIn(f"\n# diff\n$ git diff {self.read_wave_head()} {self.read_head()}\nexit 0\n", completed.stdout)
        self.assertIn("\n# preflight\npass  ancestry\n", completed.stdout)
        self.assertTrue(completed.stdout.endswith("\n# grades\ncritical\nhigh\nmedium\nlow\n"))


class BrigadeVerifyContextWithAnInstructionsCorpusTest(VerifyContextTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = Path(self.root.name).resolve() / "instructions"
        self.instructions.mkdir()
        (self.instructions / "_schema.awawa").write_text(INSTRUCTIONS_SCHEMA)
        (self.instructions / "triggers.awawa").write_text(INSTRUCTIONS_TRIGGERS)
        self.configure(keys=f'instructions = "{self.instructions}"\n{CLI_KEYS}')

    def test_should_print_the_path_triggers_whose_glob_matches_a_file_the_diff_touches(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["rules"],
            [
                {
                    "trigger": "cart_code",
                    "command": f"awawa context @TRIGGER.cart_code --depth 1 --skip reasoning {self.instructions}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": ANY,
                },
                {
                    "trigger": "billing_code",
                    "command": f"awawa context @TRIGGER.billing_code --depth 1 --skip reasoning {self.instructions}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": ANY,
                },
                {
                    "trigger": "cart_button_code",
                    "command": (
                        f"awawa context @TRIGGER.cart_button_code --depth 1 --skip reasoning {self.instructions}"
                    ),
                    "exit_code": 0,
                    "stderr": "",
                    "output": ANY,
                },
            ],
        )

    def test_should_print_the_rules_under_their_heading(self):
        # Act
        completed = self.run_verify_context("42")

        # Assert
        self.assertIn(
            f"# rules\n$ awawa context @TRIGGER.cart_code --depth 1 --skip reasoning {self.instructions}\nexit 0\n",
            completed.stdout,
        )
