import unittest
from unittest import mock

from brigade.corpus.read_entities import Entity, EntityField
from brigade.runs.read_handovers import HANDOVERS_BY_DEFAULT, read_handovers


def make_policy(project: str, handovers: str) -> Entity:
    return Entity(
        name="policy1",
        fields=(
            EntityField(name="PROJECT", value=f"@PROJECT.{project}"),
            EntityField(name="HANDOVERS", value=handovers),
        ),
    )


class ReadHandoversTest(unittest.TestCase):
    def test_should_return_the_default_when_no_project_is_given(self):
        # Arrange
        runtime = mock.Mock()

        # Act
        handovers = read_handovers(runtime, None)

        # Assert
        self.assertEqual(handovers, HANDOVERS_BY_DEFAULT)

    def test_should_return_the_default_when_no_policy_matches_the_project(self):
        # Arrange
        runtime = mock.Mock()
        runtime.run_process = mock.Mock()
        runtime.paths.config_root = mock.Mock()
        policy = make_policy("other", "5")
        with mock.patch("brigade.runs.read_handovers.read_entities", return_value=(policy,)):
            # Act
            handovers = read_handovers(runtime, "alpha")

        # Assert
        self.assertEqual(handovers, HANDOVERS_BY_DEFAULT)

    def test_should_return_the_handovers_of_the_matching_policy(self):
        # Arrange
        runtime = mock.Mock()
        runtime.run_process = mock.Mock()
        runtime.paths.config_root = mock.Mock()
        policy = make_policy("alpha", "5")
        with mock.patch("brigade.runs.read_handovers.read_entities", return_value=(policy,)):
            # Act
            handovers = read_handovers(runtime, "alpha")

        # Assert
        self.assertEqual(handovers, 5)
