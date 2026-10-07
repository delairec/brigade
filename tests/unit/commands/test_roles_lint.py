import unittest

from brigade.commands.roles_lint import _check_role_file

VALID_ROLE = (
    "---\nname: bastien\nslot: plan\nwork: deliver\nreasoning: standard\n"
    "capabilities: read\nbudget: 10\nreturns: done\n---\nBody.\n"
)


class CheckRoleFileTest(unittest.TestCase):
    def test_should_not_record_a_first_declaration_when_the_slot_is_none(self):
        # Arrange
        text = (
            "---\nname: orphan\nwork: deliver\nreasoning: standard\n"
            "capabilities: read\nbudget: 10\nreturns: done\n---\nBody.\n"
        )
        first_declarations = {}

        # Act
        findings = _check_role_file("orphan.md", text, first_declarations)

        # Assert
        self.assertEqual(findings, [{"file": "orphan.md", "key": "slot", "problem": "is missing"}])
        self.assertEqual(first_declarations, {})

    def test_should_record_the_first_declaration_of_a_slot(self):
        # Arrange
        first_declarations = {}

        # Act
        findings = _check_role_file("bastien.md", VALID_ROLE, first_declarations)

        # Assert
        self.assertEqual(findings, [])
        self.assertEqual(first_declarations, {"plan": "bastien.md"})

    def test_should_report_a_duplicate_slot_declaration(self):
        # Arrange
        first_declarations = {"plan": "bastien.md"}

        # Act
        findings = _check_role_file("other.md", VALID_ROLE, first_declarations)

        # Assert
        self.assertEqual(
            findings,
            [{"file": "other.md", "key": "slot", "problem": "plan is also declared by bastien.md"}],
        )
