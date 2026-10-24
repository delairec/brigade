import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT, TemporaryMachine

BUILT_IN_ROLES = REPOSITORY_ROOT / "brigade" / "roles" / "data"


class RolesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))

    def tearDown(self):
        self.root.cleanup()

    def run_roles(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "roles", *arguments)


class BrigadeRolesListOnAMachineThatConfiguresNoRoleTest(RolesTestCase):
    def test_should_print_the_slots_as_a_table_under_its_header(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_roles("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "slot       role        source    model",
                "plan       planner     built-in  fable",
                "build      builder     built-in  opus",
                "review     reviewer    built-in  fable",
                "remediate  remediator  built-in  opus",
                "rebase     rebaser     built-in  sonnet",
                "report     reporter    built-in  opus",
                "triage     triager     built-in  opus",
                "rules      rulewriter  built-in  fable",
                "explore    explorer    built-in  sonnet",
                "answers for claude-code",
            ],
        )
        self.assertEqual(completed.stderr, "")


class BrigadeRolesShowOfABuiltInRoleTest(RolesTestCase):
    def test_should_print_the_shipped_role_file(self):
        # Act
        completed = self.run_roles("show", "plan")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, (BUILT_IN_ROLES / "planner.md").read_text())
        self.assertEqual(completed.stderr, "")


class BrigadeRolesLintTest(RolesTestCase):
    def test_should_find_the_built_in_role_files_clean(self):
        # Act
        completed = self.run_roles("lint", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "files": [
                    "brigade/roles/data/builder.md",
                    "brigade/roles/data/explorer.md",
                    "brigade/roles/data/planner.md",
                    "brigade/roles/data/rebaser.md",
                    "brigade/roles/data/remediator.md",
                    "brigade/roles/data/reporter.md",
                    "brigade/roles/data/reviewer.md",
                    "brigade/roles/data/rulewriter.md",
                    "brigade/roles/data/triager.md",
                ],
                "findings": [],
            },
        )
        self.assertEqual(completed.stderr, "")
