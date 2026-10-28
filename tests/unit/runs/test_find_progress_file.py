import tempfile
import unittest
from pathlib import Path

from brigade.runs.find_progress_file import find_progress_file


class FindProgressFileTest(unittest.TestCase):
    def setUp(self):
        self.run_directory = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_find_the_progress_file_the_run_wrote_in_either_form(self):
        # Arrange
        rows = [("a Markdown progress", "progress.md"), ("an awawa progress", "progress.awawa")]
        for case, name in rows:
            with self.subTest(case=case):
                # Arrange
                run_directory = self.run_directory / name
                run_directory.mkdir()
                (run_directory / name).write_text("", encoding="utf-8")

                # Act
                progress_file = find_progress_file(run_directory)

                # Assert
                self.assertEqual(progress_file, run_directory / name)

    def test_should_find_none_in_a_run_that_wrote_no_progress(self):
        # Arrange
        (self.run_directory / "brief.md").write_text("Deliver the task.\n", encoding="utf-8")

        # Act
        progress_file = find_progress_file(self.run_directory)

        # Assert
        self.assertIsNone(progress_file)
