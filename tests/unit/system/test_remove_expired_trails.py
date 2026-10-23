import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.system.remove_expired_trails import remove_expired_trails
from tests.list_entry_names import list_entry_names
from tests.unit.create_test_paths import create_test_paths

NOW = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)


class RemoveExpiredTrailsTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.paths = create_test_paths(root)
        self.configuration = self.paths.config_root / "config.toml"
        self.ticks = self.paths.state_root / "ticks"
        self.commands = self.paths.state_root / "commands"

    def write_trails(self, *paths: Path) -> None:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")

    def configure(self, content: str) -> None:
        self.configuration.parent.mkdir(parents=True, exist_ok=True)
        self.configuration.write_text(content)


class RemoveExpiredTrailsByDefaultTest(RemoveExpiredTrailsTestCase):
    def test_should_remove_the_trails_older_than_seven_days_and_keep_the_others(self):
        # Arrange
        expired_tick = self.ticks / "20260930T115959Z.jsonl"
        kept_tick = self.ticks / "20260930T120000Z.jsonl"
        expired_command = self.commands / "20260901T000000Z-project-add.jsonl"
        kept_command = self.commands / "20261007T115900Z-doctor.jsonl"
        self.write_trails(expired_tick, kept_tick, expired_command, kept_command)

        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertEqual(list_entry_names(self.ticks), ["20260930T120000Z.jsonl"])
        self.assertEqual(list_entry_names(self.commands), ["20261007T115900Z-doctor.jsonl"])

    def test_should_keep_a_file_whose_name_carries_no_instant(self):
        # Arrange
        unnamed = self.commands / "notes.jsonl"
        self.write_trails(unnamed)

        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertTrue(unnamed.exists())

    def test_should_do_nothing_when_no_trail_was_written(self):
        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertFalse(self.paths.state_root.exists())


class RemoveExpiredTrailsOfConfiguredDaysTest(RemoveExpiredTrailsTestCase):
    def test_should_remove_the_trails_older_than_the_trail_days_of_config_toml(self):
        # Arrange
        self.configure("trail_days = 1\n")
        expired = self.ticks / "20261006T115959Z.jsonl"
        kept = self.ticks / "20261006T120000Z.jsonl"
        self.write_trails(expired, kept)

        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertEqual(list_entry_names(self.ticks), ["20261006T120000Z.jsonl"])

    def test_should_remove_the_trails_older_than_the_trail_days_whatever_another_key_holds(self):
        # Arrange
        self.configure("trail_days = 1\nclient = 1\n")
        expired = self.ticks / "20261006T115959Z.jsonl"
        kept = self.ticks / "20261006T120000Z.jsonl"
        self.write_trails(expired, kept)

        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertEqual(list_entry_names(self.ticks), ["20261006T120000Z.jsonl"])

    def test_should_keep_every_trail_when_config_toml_is_not_toml(self):
        # Arrange
        self.configure("trail_days =\n")
        expired = self.ticks / "20260901T000000Z.jsonl"
        self.write_trails(expired)

        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertTrue(expired.exists())

    def test_should_keep_every_trail_when_config_toml_cannot_be_read(self):
        # Arrange
        self.configuration.mkdir(parents=True)
        expired = self.ticks / "20260901T000000Z.jsonl"
        self.write_trails(expired)

        # Act
        remove_expired_trails(self.paths, NOW)

        # Assert
        self.assertTrue(expired.exists())

    def test_should_keep_every_trail_when_trail_days_is_no_integer_of_1_or_more(self):
        # Arrange
        rows = [
            ("zero", "trail_days = 0\n"),
            ("a string", 'trail_days = "7"\n'),
        ]
        for case, content in rows:
            with self.subTest(case=case):
                # Arrange
                self.configure(content)
                expired = self.ticks / "20260901T000000Z.jsonl"
                self.write_trails(expired)

                # Act
                remove_expired_trails(self.paths, NOW)

                # Assert
                self.assertTrue(expired.exists())
