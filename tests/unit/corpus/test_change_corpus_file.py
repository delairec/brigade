import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.errors import CannotWrite, CorpusLintFailed
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


def keep_unchanged(texts: tuple[str, ...]) -> None:
    return None


def append_a_task(texts: tuple[str, ...]) -> tuple[str, ...]:
    return (texts[0] + "TASK B2\n",)


class ChangeCorpusFileTestCase(unittest.TestCase):
    def setUp(self):
        self.repository = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repository)
        self.tasks = self.repository / "tasks.awawa"
        self.lint = ("awawa", "lint", "--strict", str(self.repository))
        self.staged = ("git", "diff", "--cached", "--quiet", "--", "tasks.awawa")

    def create_change(self, rewrite, file_name: str = "tasks.awawa") -> CorpusChange:
        return CorpusChange(
            repository=self.repository,
            lock=self.repository / "locks" / "corpus.lock",
            file_names=(file_name,),
            describe_message=lambda: "add @TASK.B2",
            rewrite=rewrite,
        )


class ChangeCorpusFileLeftUnchangedTest(ChangeCorpusFileTestCase):
    def test_should_answer_unchanged_and_run_nothing(self):
        # Arrange
        self.tasks.write_text("TASK B1\n")
        runner = RecordingProcessRunner()

        # Act
        changed = change_corpus_file(runner, self.create_change(keep_unchanged))

        # Assert
        self.assertEqual(changed, False)
        self.assertEqual(runner.commands, [])


class ChangeCorpusFileRewrittenTest(ChangeCorpusFileTestCase):
    def test_should_write_format_lint_and_commit_the_file(self):
        # Arrange
        self.tasks.write_text("TASK B1\n")
        runner = RecordingProcessRunner({self.staged: ProcessAnswer(exit_code=1)})

        # Act
        changed = change_corpus_file(runner, self.create_change(append_a_task))

        # Assert
        self.assertEqual(changed, True)
        self.assertEqual(self.tasks.read_text(), "TASK B1\nTASK B2\n")
        self.assertEqual(
            runner.commands,
            [
                (str(self.repository), ("awawa", "fmt", str(self.tasks))),
                (str(self.repository), self.lint),
                (str(self.repository), ("git", "add", "--", "tasks.awawa")),
                (str(self.repository), self.staged),
                (str(self.repository), ("git", "commit", "--quiet", "-m", "add @TASK.B2")),
            ],
        )

    def test_should_read_a_missing_file_as_empty(self):
        # Arrange
        runner = RecordingProcessRunner()

        # Act
        change_corpus_file(runner, self.create_change(append_a_task))

        # Assert
        self.assertEqual(self.tasks.read_text(), "TASK B2\n")


class ChangeCorpusFileRefusedByLintTest(ChangeCorpusFileTestCase):
    def test_should_restore_the_file_and_report_the_findings(self):
        # Arrange
        self.tasks.write_text("TASK B1\n")
        runner = RecordingProcessRunner(
            {
                self.lint: ProcessAnswer(exit_code=1, stdout="tasks.awawa:2: L001\n"),
                ("git", "ls-tree", "--name-only", "HEAD", "--", "tasks.awawa"): ProcessAnswer(stdout="tasks.awawa\n"),
            }
        )

        # Act
        with self.assertRaises(CorpusLintFailed) as refusal:
            change_corpus_file(runner, self.create_change(append_a_task))

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "awawa lint --strict refused the change; the corpus is restored\ntasks.awawa:2: L001",
        )
        self.assertEqual(runner.commands[-1][1], ("git", "checkout", "HEAD", "--", "tasks.awawa"))


class ChangeCorpusFileUnwritableTest(ChangeCorpusFileTestCase):
    def test_should_refuse_a_file_whose_directory_cannot_be_created(self):
        # Arrange
        (self.repository / "blocker").write_text("a file, not a directory\n")
        runner = RecordingProcessRunner()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            change_corpus_file(runner, self.create_change(append_a_task, file_name="blocker/tasks.awawa"))

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.repository}/blocker: File exists")
