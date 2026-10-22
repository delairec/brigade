import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.read_policy_field import read_policy_field

AUTO_MERGE_FIELD = "AUTO_MERGE"
INTEGRATION_NEUTRAL = "integration"


def _create_policy(name: str, *fields: tuple[str, str]) -> Entity:
    return Entity(name=name, fields=tuple(EntityField(name=field, value=value) for field, value in fields))


class ReadPolicyFieldTest(unittest.TestCase):
    def test_should_read_the_value_the_first_policy_of_the_project_sets(self):
        # Arrange
        policies = [
            _create_policy("elm_merge", ("PROJECT", "@PROJECT.elm"), (AUTO_MERGE_FIELD, "integration")),
            _create_policy("oak_review", ("PROJECT", "@PROJECT.oak"), ("REVIEW", "approval")),
            _create_policy("oak_merge", ("PROJECT", "@PROJECT.oak"), (AUTO_MERGE_FIELD, "none")),
            _create_policy("oak_later", ("PROJECT", "@PROJECT.oak"), (AUTO_MERGE_FIELD, "integration")),
        ]

        # Act
        auto_merge = read_policy_field(policies, "oak", AUTO_MERGE_FIELD, INTEGRATION_NEUTRAL)

        # Assert
        self.assertEqual(auto_merge, "none")

    def test_should_fall_back_on_the_neutral_value_when_no_policy_of_the_project_sets_the_field(self):
        # Arrange
        policies = [
            _create_policy("elm_merge", ("PROJECT", "@PROJECT.elm"), (AUTO_MERGE_FIELD, "none")),
            _create_policy("oak_review", ("PROJECT", "@PROJECT.oak"), ("REVIEW", "approval")),
        ]

        # Act
        auto_merge = read_policy_field(policies, "oak", AUTO_MERGE_FIELD, INTEGRATION_NEUTRAL)

        # Assert
        self.assertEqual(auto_merge, "integration")
