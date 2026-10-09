import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_configuration import Configuration, ConfigurationMissing, ReasoningRow, read_configuration


class ReadConfigurationTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "config.toml"

    def tearDown(self):
        self.directory.cleanup()


class ReadConfigurationWhenEveryKeyIsCommentedOutTest(ReadConfigurationTestCase):
    def test_should_answer_the_defaults(self):
        # Arrange
        self.path.write_text('# client = "claude-code"\n')

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(
            configuration,
            Configuration(
                client=None,
                scheduler=None,
                instructions=None,
                refs_cache_mb=1024,
                reasoning={},
                clients={},
                slots={},
            ),
        )


class ReadConfigurationWhenEveryKeyIsSetTest(ReadConfigurationTestCase):
    def test_should_answer_a_record_of_every_key(self):
        # Arrange
        self.path.write_text(
            'client = "claude-code"\n'
            'scheduler = "cron"\n'
            'forge_account = "octo-bot"\n'
            'instructions = "/home/ada/.ai"\n'
            'ide_link = "idea://open?file={path}&line={line}"\n'
            "refs_cache_mb = 2048\n"
            "[reasoning.deep]\n"
            'model = "opus"\n'
            'effort = "max"\n'
            "[clients.fake]\n"
            'recordings = "/srv/recordings"\n'
            "[slots]\n"
            'plan = "charlie"\n'
        )

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(
            configuration,
            Configuration(
                client="claude-code",
                scheduler="cron",
                instructions="/home/ada/.ai",
                refs_cache_mb=2048,
                reasoning={"deep": ReasoningRow(model="opus", effort="max")},
                clients={"fake": {"recordings": "/srv/recordings"}},
                slots={"plan": "charlie"},
            ),
        )


class ReadConfigurationWhenTheFileIsAbsentTest(ReadConfigurationTestCase):
    def test_should_refuse_naming_the_file_and_brigade_init(self):
        # Act
        with self.assertRaises(ConfigurationMissing) as raised:
            read_configuration(self.path)

        # Assert
        self.assertEqual(str(raised.exception), f"no configuration at {self.path}; run brigade init")


class ReadConfigurationWhenAKeyIsWrongTest(ReadConfigurationTestCase):
    def test_should_refuse_naming_the_key_and_the_file(self):
        rows = [
            ("an unknown key", "frobnicate = 1\n", "unknown key frobnicate"),
            (
                "an unknown reasoning level",
                '[reasoning.ultra]\nmodel = "opus"\neffort = "max"\n',
                "unknown key reasoning.ultra",
            ),
            (
                "an unknown key in a reasoning row",
                '[reasoning.deep]\nmodel = "opus"\neffort = "max"\ntemperature = 1\n',
                "unknown key reasoning.deep.temperature",
            ),
            ("a client of the wrong type", "client = 1\n", "client is an integer, not a string,"),
            ("a forge account of the wrong type", "forge_account = 1\n", "forge_account is an integer, not a string,"),
            ("an IDE link of the wrong type", "ide_link = true\n", "ide_link is a boolean, not a string,"),
            ("a reasoning table of the wrong type", 'reasoning = "deep"\n', "reasoning is a string, not a table,"),
            (
                "a model of the wrong type",
                '[reasoning.deep]\nmodel = 1\neffort = "max"\n',
                "reasoning.deep.model is an integer, not a string,",
            ),
            ("a reasoning row lacking its effort", '[reasoning.deep]\nmodel = "opus"\n', "reasoning.deep lacks effort"),
            (
                "a client setting of the wrong type",
                "[clients.fake]\nrecordings = true\n",
                "clients.fake.recordings is a boolean, not a string,",
            ),
            ("an unknown slot", '[slots]\ncook = "charlie"\n', "unknown key slots.cook"),
            ("a slot bound to no string", "[slots]\nplan = 1\n", "slots.plan is an integer, not a string,"),
            (
                "a cache bound of the wrong type",
                'refs_cache_mb = "1024"\n',
                "refs_cache_mb is a string, not an integer,",
            ),
            (
                "a cache bound that is a boolean",
                "refs_cache_mb = true\n",
                "refs_cache_mb is a boolean, not an integer,",
            ),
            ("a negative cache bound", "refs_cache_mb = -1\n", "refs_cache_mb is -1, not 0 or more,"),
        ]
        for case, content, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.path.write_text(content)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_configuration(self.path)

                # Assert
                self.assertEqual(str(raised.exception), f"{expected_problem} in {self.path}")

    def test_should_refuse_a_file_that_is_not_toml_naming_the_file(self):
        # Arrange
        self.path.write_text("client = \n")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_configuration(self.path)

        # Assert
        self.assertIn(f"{self.path} is not valid TOML: ", str(raised.exception))


class ReadConfigurationOfTheSecondsPerStepTest(ReadConfigurationTestCase):
    def test_should_answer_30_when_the_key_is_absent(self):
        # Arrange
        self.path.write_text('client = "fake"\n')

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(configuration.seconds_per_step, 30)

    def test_should_answer_the_number_the_key_sets(self):
        # Arrange
        self.path.write_text("seconds_per_step = 0.5\n")

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(configuration.seconds_per_step, 0.5)

    def test_should_refuse_a_value_that_is_no_positive_number_naming_the_key_and_the_file(self):
        rows = [
            ("a string", 'seconds_per_step = "30"\n', "seconds_per_step is a string, not a number,"),
            ("zero", "seconds_per_step = 0\n", "seconds_per_step is 0, not a positive number,"),
            ("a boolean", "seconds_per_step = true\n", "seconds_per_step is a boolean, not a number,"),
        ]
        for case, content, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.path.write_text(content)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_configuration(self.path)

                # Assert
                self.assertEqual(str(raised.exception), f"{expected_problem} in {self.path}")


class ReadConfigurationOfTheTrailDaysTest(ReadConfigurationTestCase):
    def test_should_answer_the_days_the_key_sets(self):
        # Arrange
        self.path.write_text("trail_days = 30\n")

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(configuration.trail_days, 30)


class ReadConfigurationOfTheJournalPollTest(ReadConfigurationTestCase):
    def test_should_answer_2_and_no_finding_when_the_key_is_absent(self):
        # Arrange
        self.path.write_text('client = "fake"\n')

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual((configuration.journal_poll_s, configuration.findings), (2, ()))

    def test_should_answer_the_seconds_the_key_sets(self):
        # Arrange
        self.path.write_text("journal_poll_s = 0.5\n")

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(configuration.journal_poll_s, 0.5)

    def test_should_keep_the_default_and_record_a_finding_naming_the_key_and_the_file(self):
        rows = [
            ("a string", 'journal_poll_s = "2"\n', "journal_poll_s is a string, not a positive number,"),
            ("zero", "journal_poll_s = 0\n", "journal_poll_s is 0, not a positive number,"),
            ("a boolean", "journal_poll_s = true\n", "journal_poll_s is a boolean, not a positive number,"),
        ]
        for case, content, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.path.write_text(content)

                # Act
                configuration = read_configuration(self.path)

                # Assert
                self.assertEqual(
                    (configuration.journal_poll_s, configuration.findings),
                    (2, (f"{expected_problem} in {self.path}; the default of 2 s holds",)),
                )
