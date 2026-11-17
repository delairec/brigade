import unittest

from tests.guards.list_schema_words import list_schema_words


class ListSchemaWordsTest(unittest.TestCase):
    def test_should_name_each_entity_and_each_field_after_its_entity(self):
        # Arrange
        schema = (
            "// Schema of the registry\n"
            "SCHEMA *\n"
            '\tDESC "fields legal on every entity"\n'
            "\tFIELD DESC string\n"
            "\t\tREPEATABLE\n"
            "\n"
            "SCHEMA ANSWER\n"
            '\tDESC "the answer of one run of a study"\n'
            "\tFIELD RUN string\n"
            "\t\tREQUIRED\n"
            "\tFIELD COLLECTED string\n"
            '\t\tDESC "one per collector"\n'
            "\t\tFIELD SUMMARY string\n"
            "\t\t\tREQUIRED\n"
            "\tWHEN STATUS archived\n"
            "\t\tGATE suppressed\n"
        )

        # Act
        words = list_schema_words(schema)

        # Assert
        self.assertEqual(words, ["DESC", "ANSWER", "ANSWER.RUN", "ANSWER.COLLECTED", "ANSWER.COLLECTED.SUMMARY"])
