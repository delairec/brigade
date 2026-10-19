import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.roles.list_machine_role_files import list_machine_role_files


class ListMachineRoleFilesTest(unittest.TestCase):
    def setUp(self):
        self.config_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.config_root)

    def test_should_list_the_role_files_of_the_machine_in_name_order(self):
        # Arrange
        roles = self.config_root / "roles"
        roles.mkdir()
        (roles / "reviewer.md").write_text("---\n")
        (roles / "builder.md").write_text("---\n")
        (roles / "notes.txt").write_text("not a role\n")

        # Act
        role_files = list_machine_role_files(self.config_root)

        # Assert
        self.assertEqual(role_files, (roles / "builder.md", roles / "reviewer.md"))

    def test_should_list_nothing_without_a_roles_directory(self):
        # Act
        role_files = list_machine_role_files(self.config_root)

        # Assert
        self.assertEqual(role_files, ())
