import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.tick.actions import RebuildTask
from brigade.tick.build_snapshot import TaskAmendment
from brigade.tick.write_rebuild_brief import write_rebuild_brief


class WriteRebuildBriefTest(unittest.TestCase):
    def test_should_write_the_brief_naming_the_pull_request_the_base_and_the_entity_on_each_head(self):
        # Arrange
        state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, state_root)
        action = RebuildTask(
            project="shop",
            wave="shop_w1",
            base="integration/shop_w1",
            task="B1",
            pr=42,
            worktree="/srv/shop/.brigade/worktrees/B1",
            reason="the entity of the task amended on integration/shop_w1",
            amendment=TaskAmendment(
                on_pull_request=Entity(
                    name="B1",
                    fields=(
                        EntityField(name="STATUS", value="implemented"),
                        EntityField(name="SPEC", value="the cart is emptied in two clicks"),
                    ),
                ),
                on_wave=Entity(
                    name="B1",
                    fields=(
                        EntityField(name="STATUS", value="todo"),
                        EntityField(name="SPEC", value="the cart is emptied in one click"),
                    ),
                ),
            ),
        )

        # Act
        path = write_rebuild_brief(state_root, action)

        # Assert
        self.assertEqual(path, state_root / "briefs" / "shop_w1-B1-rebuild.md")
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            "Rebuild @TASK.B1 of @PROJECT.shop, in the wave shop_w1, to its entity as amended on"
            " integration/shop_w1 since its pull request #42 opened.\n"
            "\n"
            "- Pull request: #42, kept: no second one is opened.\n"
            "- Base branch: integration/shop_w1.\n"
            "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch task/shop_w1/B1, handed over as it stands,"
            " uncommitted changes included.\n"
            "\n"
            "Put the branch on the head of integration/shop_w1, by a rebase or by a reset onto that head and a new"
            " implementation, and deliver on it the entity as it stands on integration/shop_w1. Push the branch with"
            " `git push --force-with-lease` and rewrite the body of the pull request #42 to describe the head pushed,"
            " instead of opening a pull request.\n"
            "\n"
            "The entity on the head of the pull request #42:\n"
            "\n"
            "```\n"
            "TASK B1\n"
            "\tSTATUS implemented\n"
            "\tSPEC the cart is emptied in two clicks\n"
            "```\n"
            "\n"
            "The entity on integration/shop_w1:\n"
            "\n"
            "```\n"
            "TASK B1\n"
            "\tSTATUS todo\n"
            "\tSPEC the cart is emptied in one click\n"
            "```\n",
        )
