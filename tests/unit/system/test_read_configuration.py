import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_configuration import Configuration, ReasoningRow, read_configuration


class ReadConfigurationTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "config.toml"

    def tearDown(self):
        self.directory.cleanup()


class ReadConfigurationWhenEveryKeyIsCommentedOut(ReadConfigurationTestCase):
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
                forge_account=None,
                instructions=None,
                ide_link=None,
                reasoning={},
                clients={},
            ),
        )


class ReadConfigurationWhenEveryKeyIsSet(ReadConfigurationTestCase):
    def test_should_answer_a_record_of_every_key(self):
        # Arrange
        self.path.write_text(
            'client = "claude-code"\n'
            'scheduler = "cron"\n'
            'forge_account = "octo-bot"\n'
            'instructions = "/home/ada/.ai"\n'
            'ide_link = "idea://open?file={path}&line={line}"\n'
            "[reasoning.deep]\n"
            'model = "opus"\n'
            'effort = "max"\n'
            "[clients.fake]\n"
            'recordings = "/srv/recordings"\n'
        )

        # Act
        configuration = read_configuration(self.path)

        # Assert
        self.assertEqual(
            configuration,
            Configuration(
                client="claude-code",
                scheduler="cron",
                forge_account="octo-bot",
                instructions="/home/ada/.ai",
                ide_link="idea://open?file={path}&line={line}",
                reasoning={"deep": ReasoningRow(model="opus", effort="max")},
                clients={"fake": {"recordings": "/srv/recordings"}},
            ),
        )


class ReadConfigurationWhenTheFileIsAbsent(ReadConfigurationTestCase):
    def test_should_refuse_naming_the_file_and_brigade_init(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_configuration(self.path)

        # Assert
        self.assertEqual(str(raised.exception), f"no configuration at {self.path}; run brigade init")


class ReadConfigurationWhenAKeyIsWrong(ReadConfigurationTestCase):
    def test_should_refuse_naming_the_key_and_the_file(self):
        rows = [
            ("an unknown key", "frobnicate = 1\n", "unknown key frobnicate"),
            ("an unknown reasoning level", '[reasoning.ultra]\nmodel = "opus"\neffort = "max"\n', "unknown key reasoning.ultra"),
            (
                "an unknown key in a reasoning row",
                '[reasoning.deep]\nmodel = "opus"\neffort = "max"\ntemperature = 1\n',
                "unknown key reasoning.deep.temperature",
            ),
            ("a client of the wrong type", "client = 1\n", "client is an integer, not a string,"),
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
