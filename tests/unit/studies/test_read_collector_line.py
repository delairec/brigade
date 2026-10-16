import unittest

from brigade.errors import BrigadeError
from brigade.studies.read_collector_line import read_collector_line


class ReadCollectorLineTest(unittest.TestCase):
    def test_should_read_the_collector_and_its_parameters(self):
        # Arrange
        rows = [
            ("git-log since=7d", ("git-log", {"since": "7d"})),
            ("corpus", ("corpus", {})),
            ("ledger window=week kind=run", ("ledger", {"window": "week", "kind": "run"})),
            ("shell: ls -1 src", ("shell", {"command": "ls -1 src"})),
            ("shell: grep -c a=b notes", ("shell", {"command": "grep -c a=b notes"})),
        ]
        for line, expected in rows:
            with self.subTest(line=line):
                # Act
                read = read_collector_line(line)

                # Assert
                self.assertEqual(read, expected)

    def test_should_refuse_a_shell_command_it_cannot_split(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_collector_line("shell: printf 'oak")

        # Assert
        self.assertIn("printf 'oak", str(refusal.exception))
