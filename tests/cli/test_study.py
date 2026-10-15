import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

PINNED_COMMIT_DATES = {"GIT_AUTHOR_DATE": "2026-10-12T09:00:00Z", "GIT_COMMITTER_DATE": "2026-10-12T09:00:00Z"}
QUESTION = "what changed in the shop this week?"


class StudyTestCase(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.run_init()
        self.project = TemporaryProject(
            root / "projects" / "shop", {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        )
        self.project.write("README.md", "shop\n")
        self.project.track("README.md")
        self.project.run_git("commit", "--quiet", "-m", "start the shop")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))

    def tearDown(self):
        self.root.cleanup()

    def run_study(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "study", *arguments)

    def read_studies(self) -> str:
        return (self.machine.corpus / "studies.awawa").read_text()


class BrigadeStudyNewTest(StudyTestCase):
    def test_should_record_the_study_with_the_question_verbatim(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved this week",
            "--question",
            QUESTION,
            "--project",
            "shop",
            "--collector",
            "git-log since=7d",
            "--collector",
            "shell: ls",
            "--every",
            "1d",
            "--output",
            "inbox",
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_studies(),
            "STUDY weekly\n"
            '\tTITLE "what moved this week"\n'
            '\tQUESTION "what changed in the shop this week?"\n'
            "\tPROJECT @PROJECT.shop\n"
            '\tCOLLECTOR "git-log since=7d"\n'
            '\tCOLLECTOR "shell: ls"\n'
            "\tSLOT report\n"
            '\tEVERY "1d"\n'
            '\tOUTPUT "inbox"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )

    def test_should_commit_the_study(self):
        # Act
        self.run_study(
            "new", "weekly", "--title", "what moved", "--collector", "worktrees", "--every", "1d", "--output", "inbox"
        )

        # Assert
        self.assertEqual(self.machine.read_git("log", "-1", "--format=%s"), "brigade study new: @STUDY.weekly\n")

    def test_should_record_a_scan_with_no_slot_question_nor_project(self):
        # Act
        completed = self.run_study(
            "new",
            "trees",
            "--title",
            "the worktrees",
            "--collector",
            "worktrees",
            "--slot",
            "none",
            "--every",
            "1h",
            "--output",
            "inbox",
            "--answer",
            "ANSWER",
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_studies(),
            "STUDY trees\n"
            '\tTITLE "the worktrees"\n'
            '\tCOLLECTOR "worktrees"\n'
            "\tSLOT none\n"
            '\tEVERY "1h"\n'
            '\tOUTPUT "inbox"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )

    def test_should_print_the_study_recorded(self):
        # Act
        completed = self.run_study(
            "new", "weekly", "--title", "what moved", "--collector", "worktrees", "--every", "1d", "--output", "inbox"
        )

        # Assert
        self.assertEqual(completed.stdout, "@STUDY.weekly recorded, every 1d\n")

    def test_should_exit_1_naming_an_answer_type_the_schema_does_not_declare(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "worktrees",
            "--every",
            "1d",
            "--output",
            "inbox",
            "--answer",
            "VERDICT",
        )

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade study new: the schema of the operational corpus declares no VERDICT\n"),
        )

    def test_should_exit_1_naming_a_project_that_is_not_registered(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--project",
            "cart",
            "--collector",
            "worktrees",
            "--every",
            "1d",
            "--output",
            "inbox",
        )

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr), (1, "brigade study new: @PROJECT.cart is not registered\n")
        )
