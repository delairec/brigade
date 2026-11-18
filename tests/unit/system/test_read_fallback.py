import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Fallback, ReasoningRow, parse_configuration
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class ReadFallbackTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "config.toml"

    def tearDown(self):
        self.directory.cleanup()


class ReadFallbackWhenItIsDeclaredTest(ReadFallbackTestCase):
    def test_should_answer_the_client_and_the_model_and_effort_of_each_level_it_binds(self):
        # Arrange
        self.path.write_text(
            'client = "claude-code"\n'
            "[fallback]\n"
            'client = "vibe"\n'
            "[fallback.reasoning.standard]\n"
            'model = "devstral"\n'
            'effort = "high"\n'
            "[fallback.reasoning.light]\n"
            'model = "devstral-small"\n'
            'effort = "medium"\n'
        )

        # Act
        configuration = parse_configuration(self.path)

        # Assert
        self.assertEqual(
            configuration.fallback,
            Fallback(
                client="vibe",
                reasoning={
                    "standard": ReasoningRow(model="devstral", effort="high"),
                    "light": ReasoningRow(model="devstral-small", effort="medium"),
                },
            ),
        )


class ReadFallbackWhenItIsAbsentTest(ReadFallbackTestCase):
    def test_should_answer_no_fallback(self):
        # Arrange
        self.path.write_text('client = "claude-code"\n')

        # Act
        configuration = parse_configuration(self.path)

        # Assert
        self.assertIsNone(configuration.fallback)


class ReadFallbackWhenAKeyIsWrongTest(ReadFallbackTestCase):
    def test_should_refuse_naming_the_key_and_the_file(self):
        for case, text, message in [
            (
                "an unknown level",
                '[fallback]\nclient = "vibe"\n[fallback.reasoning.ultra]\nmodel = "devstral"\neffort = "high"\n',
                "unknown key fallback.reasoning.ultra",
            ),
            (
                "a row lacking its model",
                '[fallback]\nclient = "vibe"\n[fallback.reasoning.deep]\neffort = "high"\n',
                "fallback.reasoning.deep lacks model",
            ),
            (
                "a row lacking its effort",
                '[fallback]\nclient = "vibe"\n[fallback.reasoning.deep]\nmodel = "devstral"\n',
                "fallback.reasoning.deep lacks effort",
            ),
            ("a fallback naming no client", "[fallback]\n[fallback.reasoning]\n", "fallback lacks client"),
            (
                "an unknown key in the fallback",
                '[fallback]\nclient = "vibe"\nmodel = "devstral"\n',
                "unknown key fallback.model",
            ),
            ("a fallback of the wrong type", 'fallback = "vibe"\n', "fallback is a string, not a table,"),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.path.write_text(text)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    parse_configuration(self.path)

                # Assert
                self.assertEqual(str(raised.exception), f"{message} in {self.path}")


class ReadFallbackWhenItsClientIsFoundNowhereTest(unittest.TestCase):
    def test_should_refuse_naming_the_key_the_client_and_the_file(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        paths = create_test_paths(root)
        paths.configuration_file.parent.mkdir(parents=True, exist_ok=True)
        paths.configuration_file.write_text('client = "fake"\n[fallback]\nclient = "nowhere"\n')

        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_configuration(create_test_runtime(paths), CONFIGURATION_REQUIRED)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"fallback.client names nowhere, a client adapter found nowhere, in {paths.configuration_file}",
        )

    def test_should_read_a_fallback_naming_a_client_adapter_brigade_finds(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        paths = create_test_paths(root)
        paths.configuration_file.parent.mkdir(parents=True, exist_ok=True)
        paths.configuration_file.write_text('client = "fake"\n[fallback]\nclient = "fake"\n')

        # Act
        configuration = read_configuration(create_test_runtime(paths), CONFIGURATION_REQUIRED)

        # Assert
        self.assertEqual(configuration.fallback, Fallback(client="fake", reasoning={}))
