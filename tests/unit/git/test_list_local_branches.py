import unittest
from pathlib import Path

from brigade.git.list_local_branches import list_local_branches
from tests.unit.scripted_processes import ScriptedProcesses


class ListLocalBranchesTest(unittest.TestCase):
    def test_should_list_the_local_branches_by_their_full_name(self):
        # Arrange
        processes = ScriptedProcesses()
        processes.answer(
            ("git", "for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads"), stdout="main\ntask/w1/B1\n"
        )

        # Act
        branches = list_local_branches(processes, Path("/srv/oak"))

        # Assert
        self.assertEqual(branches, ("main", "task/w1/B1"))
