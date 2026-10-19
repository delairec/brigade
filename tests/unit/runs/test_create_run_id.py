import unittest
from datetime import datetime, timedelta, timezone

from brigade.runs.create_run_id import create_run_id


class CreateRunIdTest(unittest.TestCase):
    def test_should_name_the_run_by_its_utc_instant_and_a_random_suffix(self):
        # Arrange
        paris_summer = timezone(timedelta(hours=2))

        # Act
        run_id = create_run_id(datetime(2026, 10, 19, 11, 0, tzinfo=paris_summer))

        # Assert
        self.assertRegex(run_id, r"^20261019T090000Z-[0-9a-f]{6}$")
