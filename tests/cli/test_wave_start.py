import tempfile
import unittest
from pathlib import Path

from tests.cli.run_test_case import FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject

PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD AFTER @TASK\n\t\tREPEATABLE\n"
    "\n"
    "SCHEMA OPEN_QUESTION\n"
    '\tDESC "a fact left undecided"\n'
    "\tFIELD STATUS open|closed\n\t\tREQUIRED\n"
    "\tFIELD BLOCKS @TASK\n\t\tREPEATABLE\n\t\tCONVERSE BLOCKED_BY\n"
    "\tWHEN STATUS closed\n\t\tGATE suppressed\n"
)
MAIN_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tAFTER @TASK.S2\n\n'
    'TASK S4\n\tTITLE "Confirm before emptying the cart"\n\tSTATUS todo\n\tAFTER @TASK.S3\n\n'
    'TASK S5\n\tTITLE "Undo the emptying"\n\tSTATUS todo\n\tAFTER @TASK.S6\n\n'
    'TASK S6\n\tTITLE "Keep the emptied cart for a day"\n\tSTATUS todo\n\n'
    'TASK S7\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\n'
    'TASK S10\n\tTITLE "Show the emptied cart"\n\tSTATUS todo\n\n'
    'TASK Cleanup\n\tTITLE "Tidy the cart module"\n\tSTATUS todo\n'
)
MAIN_QUESTIONS = "OPEN_QUESTION KeepDuration\n\tSTATUS open\n\tBLOCKS @TASK.S6\n"
OPEN_WAVE = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/shop_w1", "tasks": ["S7"]}\n'
)


class WaveStartTestCase(FileWaitingTestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(
            root / "projects" / "shop", {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        )
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", MAIN_TASKS)
        self.project.write("corpus/questions.awawa", MAIN_QUESTIONS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.ledger = self.machine.state_home / "brigade" / "ledger"
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(OPEN_WAVE)

    def tearDown(self):
        self.root.cleanup()

    def run_wave_start(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", "start", *arguments)

    def use_a_github_remote(self) -> Path:
        remote = Path(self.root.name).resolve() / "remote.git"
        self.project.run_git("init", "--quiet", "--bare", str(remote))
        self.project.run_git("remote", "add", "origin", str(remote))
        self.project.run_git("push", "--quiet", "origin", "main")
        projects = self.machine.corpus / "projects.awawa"
        projects.write_text(projects.read_text().replace('\tFORGE "none"\n', '\tFORGE "github"\n'))
        return remote


class BrigadeWaveStartOnAProjectOfTheGithubForgeTest(WaveStartTestCase):
    def test_should_push_the_integration_branch(self):
        # Arrange
        self.use_a_github_remote()

        # Act
        completed = self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout),
            (0, "wave shop_w2 of @PROJECT.shop on integration/shop_w2: S3, S4, S10\n"),
        )
        self.assertIn("refs/heads/integration/shop_w2", self.project.run_git("ls-remote", "--heads", "origin"))


if __name__ == "__main__":
    unittest.main()
