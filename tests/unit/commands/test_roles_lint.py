import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.roles_lint import COMMAND
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

AUDITOR_ROLE = """---
name: auditor
slot: review
work: reviews a pull request
reasoning: deep
capabilities: read
budget: 30
returns: the findings
---
You review the pull request.
"""
SECOND_AUDITOR_ROLE = """---
name: second-auditor
slot: review
work: reviews a pull request again
reasoning: deep
capabilities: read
budget: 30
returns: the findings
---
You review the pull request again.
"""
ROLE_WITHOUT_FRONT_MATTER = "You review the pull request.\n"


class RolesLintTextTest(unittest.TestCase):
    def test_should_name_the_file_alone_for_a_finding_on_no_key(self):
        # Arrange
        document = {
            "files": ["/srv/roles/planner.md"],
            "findings": [
                {"file": "/srv/roles/planner.md", "key": None, "problem": "has no front matter between two --- lines"}
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "/srv/roles/planner.md: has no front matter between two --- lines\n\nroles lint: 1 files, 1 finding",
        )

    def test_should_name_the_key_of_a_finding_on_a_key(self):
        # Arrange
        document = {
            "files": ["/srv/roles/auditor.md", "/srv/roles/second-auditor.md"],
            "findings": [
                {
                    "file": "/srv/roles/second-auditor.md",
                    "key": "slot",
                    "problem": "review is also declared by /srv/roles/auditor.md",
                },
                {"file": "/srv/roles/second-auditor.md", "key": "budget", "problem": "is empty"},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "/srv/roles/second-auditor.md: slot review is also declared by /srv/roles/auditor.md\n"
            "/srv/roles/second-auditor.md: budget is empty\n\n"
            "roles lint: 2 files, 2 findings",
        )

    def test_should_print_the_count_alone_when_nothing_is_found(self):
        # Arrange
        document = {"files": ["/srv/roles/planner.md", "/srv/roles/builder.md"], "findings": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "roles lint: 2 files, 0 findings")


class RolesLintExitCodeTest(unittest.TestCase):
    def test_should_fail_on_a_finding_only(self):
        # Arrange
        rows = [
            ("no finding", [], 0),
            ("one finding", [{"file": "/srv/roles/planner.md", "key": None, "problem": "is unreadable"}], 1),
        ]
        for case, findings, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code({"files": [], "findings": findings})

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


class RolesLintRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RolesLintOfTheMachineRolesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.roles = self.root / "config" / "roles"
        self.roles.mkdir(parents=True)

    def test_should_report_an_unreadable_file_and_a_slot_declared_twice(self):
        # Arrange
        (self.roles / "auditor.md").write_text(AUDITOR_ROLE, encoding="utf-8")
        (self.roles / "broken.md").write_text(ROLE_WITHOUT_FRONT_MATTER, encoding="utf-8")
        (self.roles / "second-auditor.md").write_text(SECOND_AUDITOR_ROLE, encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(), create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document["findings"],
            [
                {
                    "file": f"{self.roles}/broken.md",
                    "key": None,
                    "problem": "has no front matter between two --- lines",
                },
                {
                    "file": f"{self.roles}/second-auditor.md",
                    "key": "slot",
                    "problem": f"review is also declared by {self.roles}/auditor.md",
                },
            ],
        )

    def test_should_report_a_role_declaring_no_slot(self):
        # Arrange
        (self.roles / "auditor.md").write_text(AUDITOR_ROLE.replace("slot: review\n", ""), encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(), create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document["findings"], [{"file": f"{self.roles}/auditor.md", "key": "slot", "problem": "is missing"}]
        )

    def test_should_list_the_machine_files_after_the_built_in_ones(self):
        # Arrange
        (self.roles / "auditor.md").write_text(AUDITOR_ROLE, encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(), create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(document["files"][-1], f"{self.roles}/auditor.md")
