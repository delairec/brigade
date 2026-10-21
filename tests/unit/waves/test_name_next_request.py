import unittest

from brigade.waves.name_next_request import name_next_request


class NameNextRequestTest(unittest.TestCase):
    def test_should_number_the_next_request_of_the_project_after_its_highest(self):
        # Arrange
        text = "REQUEST oak_r2\n\tSTATUS planned\n\nREQUEST oak_r9\n\tSTATUS planning\n\nREQUEST elm_r14\n"

        # Act
        name = name_next_request(text, "oak")

        # Assert
        self.assertEqual(name, "oak_r10")

    def test_should_number_the_first_request_of_a_project_one(self):
        # Arrange
        no_requests = ""

        # Act
        name = name_next_request(no_requests, "oak")

        # Assert
        self.assertEqual(name, "oak_r1")
