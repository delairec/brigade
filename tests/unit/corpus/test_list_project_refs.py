import unittest

from brigade.corpus.list_project_refs import list_project_refs
from brigade.corpus.read_entity import Entity, EntityField
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

OAK = Entity(name="oak", fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="MAIN", value="main")))
WORKTREES = (
    "worktree /srv/oak\0HEAD 8885daa\0branch refs/heads/main\0\0"
    "worktree /srv/oak-b42\0HEAD de446f3\0branch refs/heads/b42\0\0"
    "worktree /srv/oak-detached\0HEAD 0be1f00\0detached\0\0"
)


class ListProjectRefsTest(unittest.TestCase):
    def test_should_list_the_main_branch_first_then_the_other_branches_then_the_linked_worktrees(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                ("git", "for-each-ref"): ProcessAnswer(stdout="b42\nfeature/x\nmain\n"),
                ("git", "worktree", "list"): ProcessAnswer(stdout=WORKTREES),
            }
        )

        # Act
        refs = list_project_refs(runner.run, OAK)

        # Assert
        self.assertEqual(refs, ["main", "b42", "feature/x", "worktree:b42"])
