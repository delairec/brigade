import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import PreparedWorktree
from brigade.tick.write_build_brief import write_build_brief

ACTION = LaunchTask(
    project="shop",
    wave="shop_w1",
    branch="integration/shop_w1",
    task="B1",
    task_branch="feature/B1-task",
    pull_request_checks=None,
)


class WriteBuildBriefTest(unittest.TestCase):
    def test_should_write_the_brief_of_the_task_naming_its_worktree_and_branch(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        action = LaunchTask(
            project="shop",
            wave="shop_w1",
            branch="integration/shop_w1",
            task="B1",
            task_branch="feature/B1-task",
            pull_request_checks=None,
        )
        prepared = PreparedWorktree(
            worktree=BranchWorktree(
                path=Path("/srv/shop/.brigade/worktrees/B1"), branch="feature/B1-task", start="integration/shop_w1"
            ),
            conflicted=False,
            on_start=True,
        )
        no_task_ruled_on_the_wave_branch = None

        # Act
        path = write_build_brief(state_root, action, prepared, no_task_ruled_on_the_wave_branch)

        # Assert
        self.assertEqual(path, state_root / "briefs" / "shop_w1-B1.md")
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Deliver @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
            "\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch feature/B1-task,"
            " cut from the head of integration/shop_w1.\n",
        )

    def test_should_tell_the_build_of_a_rebased_branch_that_it_was_put_on_the_head_of_its_base(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        prepared = PreparedWorktree(
            worktree=BranchWorktree(
                path=Path("/srv/shop/.brigade/worktrees/B1"), branch="feature/B1-task", start="integration/shop_w1"
            ),
            conflicted=False,
            on_start=True,
            rebased=True,
        )
        no_task_ruled_on_the_wave_branch = None

        # Act
        path = write_build_brief(state_root, ACTION, prepared, no_task_ruled_on_the_wave_branch)

        # Assert
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Deliver @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
            "\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch feature/B1-task,"
            " put on the head of integration/shop_w1.\n",
        )

    def test_should_tell_the_build_of_a_red_branch_to_repair_the_commands_that_failed_first_without_rebasing_it(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        prepared = PreparedWorktree(
            worktree=BranchWorktree(
                path=Path("/srv/shop/.brigade/worktrees/B1"), branch="feature/B1-task", start="integration/shop_w1"
            ),
            conflicted=False,
            on_start=False,
            failed_commands=("make test", "make lint"),
        )
        no_task_ruled_on_the_wave_branch = None

        # Act
        path = write_build_brief(state_root, ACTION, prepared, no_task_ruled_on_the_wave_branch)

        # Assert
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Deliver @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
            "\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch feature/B1-task,"
            " left as it stands, off the head of integration/shop_w1: its head failed `make test`, `make lint`;"
            " repair those failures first, and do not rebase the branch.\n",
        )

    def test_should_give_the_build_the_task_as_it_reads_on_the_wave_branch_as_prevailing_over_its_worktree(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        action = LaunchTask(
            project="shop",
            wave="shop_w1",
            branch="integration/shop_w1",
            task="B1",
            task_branch="feature/B1-task",
            pull_request_checks=None,
        )
        prepared = PreparedWorktree(
            worktree=BranchWorktree(
                path=Path("/srv/shop/.brigade/worktrees/B1"),
                branch="feature/B1-task",
                start="origin/integration/shop_w1",
            ),
            conflicted=False,
            on_start=False,
            failed_commands=("make test",),
        )
        ruled_task = Entity(
            name="B1",
            fields=(
                EntityField(name="STATUS", value="todo"),
                EntityField(name="SPEC", value="the cart keeps its items"),
            ),
        )

        # Act
        path = write_build_brief(state_root, action, prepared, ruled_task)

        # Assert
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Deliver @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
            "\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch feature/B1-task,"
            " left as it stands, off the head of integration/shop_w1: its head failed `make test`;"
            " repair those failures first, and do not rebase the branch.\n"
            "\n"
            "@TASK.B1 reads differently on origin/integration/shop_w1 than in the corpus of the worktree;"
            " that reading is more recent and prevails:\n"
            "\n"
            "```\n"
            "TASK B1\n"
            "\tSTATUS todo\n"
            "\tSPEC the cart keeps its items\n"
            "```\n",
        )
