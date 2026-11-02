import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.cli.wave_rehearser import FORGE
from tests.process_launcher import ProcessLauncher

PULL_REQUEST_OF_S1 = {
    "number": 1,
    "title": "deliver S1",
    "body": "",
    "headRefName": "task/S1",
    "baseRefName": "main",
    "state": "OPEN",
    "reviewDecision": None,
    "author": "octo-build",
}


class GithubOverABareRemoteMergeTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.machine = TemporaryMachine(root)
        self.store = root / "forge"
        project = TemporaryProject(root / "shop", self.machine.describe_environment())
        project.run_git("init", "--quiet", "--bare", "--initial-branch=main", str(self.store / "remote.git"))
        project.write("cart.txt", "cart\n")
        project.track("cart.txt")
        project.run_git("commit", "--quiet", "-m", "the cart")
        project.run_git("remote", "add", "origin", str(self.store / "remote.git"))
        project.run_git("push", "--quiet", "origin", "main")
        project.run_git("switch", "--quiet", "--create", "task/S1")
        project.write("delivered-S1.txt", "S1\n")
        project.track("delivered-S1.txt")
        project.run_git("commit", "--quiet", "-m", "feat: deliver S1")
        project.run_git("push", "--quiet", "origin", "task/S1")
        (self.store / "pulls").mkdir()
        (self.store / "pulls" / "1.json").write_text(json.dumps(PULL_REQUEST_OF_S1))

    def test_should_refuse_the_merge_of_a_pull_request_whose_head_is_not_the_one_named(self):
        # Arrange
        head_read_before_a_push = "0123abc"

        # Act
        completed = ProcessLauncher.run(
            [
                sys.executable,
                str(FORGE),
                str(self.store),
                "pr",
                "merge",
                "1",
                "--rebase",
                "--match-head-commit",
                head_read_before_a_push,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=self.machine.describe_environment(),
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads((self.store / "pulls" / "1.json").read_text()), PULL_REQUEST_OF_S1)
