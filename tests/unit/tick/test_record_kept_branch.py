import contextlib
import io
import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.branch_kept import BranchKept
from brigade.ledger.read_ledger import read_ledger
from brigade.tick.actions import KeepBranch
from brigade.tick.record_kept_branch import record_kept_branch
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NOW = datetime(2026, 11, 14, 11, 0, tzinfo=UTC)
KEPT_SPROUT = KeepBranch(
    project="shop", branch="feature/S7-sprout", reason="a commit outside the merged pull request", head="c0ffee1"
)


class RecordKeptBranchTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def test_should_name_the_kept_branch_with_its_reason_and_its_head_on_stderr(self):
        # Arrange
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            record_kept_branch(create_test_runtime(self.paths, now=NOW), KEPT_SPROUT)

        # Assert
        self.assertEqual(
            errors.getvalue(),
            "brigade tick: the branch feature/S7-sprout of shop kept at c0ffee1:"
            " a commit outside the merged pull request\n",
        )

    def test_should_record_the_kept_branch_in_the_ledger(self):
        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            record_kept_branch(create_test_runtime(self.paths, now=NOW), KEPT_SPROUT)

        # Assert
        [entry] = read_ledger(self.paths.state_root).entries
        self.assertEqual(
            entry.event,
            BranchKept(
                project="shop",
                branch="feature/S7-sprout",
                reason="a commit outside the merged pull request",
                head="c0ffee1",
            ),
        )
