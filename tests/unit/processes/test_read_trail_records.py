from brigade.errors import BrigadeError
from brigade.processes.read_trail_records import read_trail_records
from tests.unit.processes.state_with_trails import EXITED_ONE, SUCCEEDED, StateWithTrailsTestCase


class ReadTrailRecordsTest(StateWithTrailsTestCase):
    def test_should_read_the_whole_lines_and_leave_out_a_line_still_being_written(self):
        # Arrange
        trail = self.write_trail("ticks/20261011T100000Z.jsonl", SUCCEEDED + EXITED_ONE + '{"outcome": "exi')

        # Act
        records = read_trail_records(trail)

        # Assert
        self.assertEqual(records, [{"outcome": "exited", "exit": 0}, {"outcome": "exited", "exit": 1}])

    def test_should_refuse_a_line_that_is_not_json_naming_it(self):
        # Arrange
        trail = self.write_trail("ticks/20261011T100000Z.jsonl", SUCCEEDED + "not json\n")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_trail_records(trail)

        # Assert
        self.assertEqual(str(refusal.exception), f"line 2 of {trail} is not a process record: not a JSON document")
