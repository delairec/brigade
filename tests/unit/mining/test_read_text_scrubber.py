import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.mining.read_text_scrubber import read_text_scrubber
from tests.unit.scripted_processes import ScriptedProcesses

CONFIG_ROOT = Path("/srv/config/brigade")


class ReadTextScrubberTest(unittest.TestCase):
    def test_should_replace_each_token_by_the_kind_of_its_shape(self):
        # Arrange
        processes = ScriptedProcesses()
        no_project = {}
        processes.answer_entities(CONFIG_ROOT, "PROJECT", no_project)
        scrub = read_text_scrubber(processes, CONFIG_ROOT)

        # Act
        scrubbed = scrub("ghp_fixture1 gho_fixture2 ghs_fixture3 github_pat_fixture_4 sk-ant-fixture-5")

        # Assert
        self.assertEqual(scrubbed, "[GitHub token] [GitHub token] [GitHub token] [GitHub token] [Anthropic API key]")

    def test_should_refuse_a_private_pattern_that_is_no_regular_expression(self):
        # Arrange
        processes = ScriptedProcesses()
        processes.answer_entities(CONFIG_ROOT, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("PRIVATE", "Acme("))})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_text_scrubber(processes, CONFIG_ROOT)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the PRIVATE pattern Acme( of the project oak is no regular expression: "
            "missing ), unterminated subpattern at position 4",
        )

    def test_should_refuse_a_public_pattern_that_is_no_regular_expression(self):
        # Arrange
        processes = ScriptedProcesses()
        processes.answer_entities(
            CONFIG_ROOT, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("PRIVATE", "Acme"), ("PUBLIC", "Acme("))}
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_text_scrubber(processes, CONFIG_ROOT)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the PUBLIC pattern Acme( of the project oak is no regular expression: "
            "missing ), unterminated subpattern at position 4",
        )
