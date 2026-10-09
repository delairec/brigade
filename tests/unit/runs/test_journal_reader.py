import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.journal_reader import JournalReader

READING_LINE = (
    '{"schema_version": 1, "at": "2026-10-09T14:00:00Z", "segment": 1, "kind": "text",'
    ' "summary": "Reading the task", "cut": false}\n'
)
WRITING_LINE = (
    '{"schema_version": 1, "at": "2026-10-09T14:00:02Z", "segment": 1, "kind": "text",'
    ' "summary": "Writing the test", "cut": false}\n'
)
WRITING_LINE_START = '{"schema_version": 1, "at": "2026-10-09T1'
WRITING_LINE_END = '4:00:02Z", "segment": 1, "kind": "text", "summary": "Writing the test", "cut": false}\n'


class JournalReaderTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.journal_path = Path(self.directory.name) / "journal.jsonl"

    def tearDown(self):
        self.directory.cleanup()

    def append(self, text: str) -> None:
        with self.journal_path.open("a", encoding="utf-8") as journal:
            journal.write(text)

    def test_should_read_nothing_from_a_journal_not_written_yet(self):
        # Arrange
        reader = JournalReader(self.journal_path)

        # Act
        records = reader.read_whole_records()

        # Assert
        self.assertEqual(records, [])

    def test_should_read_the_records_of_the_journal_in_their_order(self):
        # Arrange
        self.append(READING_LINE + WRITING_LINE)
        reader = JournalReader(self.journal_path)

        # Act
        records = reader.read_whole_records()

        # Assert
        self.assertEqual(
            records,
            [
                {
                    "schema_version": 1,
                    "at": "2026-10-09T14:00:00Z",
                    "segment": 1,
                    "kind": "text",
                    "summary": "Reading the task",
                    "cut": False,
                },
                {
                    "schema_version": 1,
                    "at": "2026-10-09T14:00:02Z",
                    "segment": 1,
                    "kind": "text",
                    "summary": "Writing the test",
                    "cut": False,
                },
            ],
        )

    def test_should_read_only_the_records_appended_since_its_last_read(self):
        # Arrange
        self.append(READING_LINE)
        reader = JournalReader(self.journal_path)
        reader.read_whole_records()
        self.append(WRITING_LINE)

        # Act
        records = reader.read_whole_records()

        # Assert
        self.assertEqual(
            records,
            [
                {
                    "schema_version": 1,
                    "at": "2026-10-09T14:00:02Z",
                    "segment": 1,
                    "kind": "text",
                    "summary": "Writing the test",
                    "cut": False,
                }
            ],
        )

    def test_should_leave_a_line_not_yet_whole_out(self):
        # Arrange
        self.append(READING_LINE + WRITING_LINE_START)
        reader = JournalReader(self.journal_path)

        # Act
        records = reader.read_whole_records()

        # Assert
        self.assertEqual(
            records,
            [
                {
                    "schema_version": 1,
                    "at": "2026-10-09T14:00:00Z",
                    "segment": 1,
                    "kind": "text",
                    "summary": "Reading the task",
                    "cut": False,
                }
            ],
        )

    def test_should_read_a_line_once_it_is_whole(self):
        # Arrange
        self.append(READING_LINE + WRITING_LINE_START)
        reader = JournalReader(self.journal_path)
        reader.read_whole_records()
        self.append(WRITING_LINE_END)

        # Act
        records = reader.read_whole_records()

        # Assert
        self.assertEqual(
            records,
            [
                {
                    "schema_version": 1,
                    "at": "2026-10-09T14:00:02Z",
                    "segment": 1,
                    "kind": "text",
                    "summary": "Writing the test",
                    "cut": False,
                }
            ],
        )

    def test_should_name_the_line_of_the_journal_that_is_no_record_counting_the_lines_already_read(self):
        # Arrange
        self.append(READING_LINE + WRITING_LINE)
        reader = JournalReader(self.journal_path)
        reader.read_whole_records()
        self.append("Reading the task\n")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            reader.read_whole_records()

        # Assert
        self.assertEqual(
            str(raised.exception), f"line 3 of {self.journal_path} is not a journal record: not a JSON document"
        )
