import unittest

from brigade.corpus.decode_entity import decode_entity
from brigade.corpus.entity import Entity, EntityField


class DecodeEntityTest(unittest.TestCase):
    def test_should_give_each_top_level_field_of_a_shown_entity_its_decoded_value(self):
        # Arrange
        shown = {
            "fields": [
                {"name": "TITLE", "atoms": ['"Empty the \\"cart\\""'], "fields": []},
                {
                    "name": "SPEC",
                    "atoms": ['"the cart empties"'],
                    "fields": [{"name": "IMPL", "atoms": ['"src/cart.py::def empty"'], "fields": []}],
                },
                {"name": "MILESTONE", "atoms": ["@MILESTONE.M1"], "fields": []},
            ]
        }

        # Act
        entity = decode_entity("T7", shown)

        # Assert
        self.assertEqual(
            entity,
            Entity(
                name="T7",
                fields=(
                    EntityField(name="TITLE", value='Empty the "cart"'),
                    EntityField(name="SPEC", value="the cart empties"),
                    EntityField(name="MILESTONE", value="@MILESTONE.M1"),
                ),
            ),
        )
