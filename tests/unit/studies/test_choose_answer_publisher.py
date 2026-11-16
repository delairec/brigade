import unittest

from brigade.studies.choose_answer_publisher import choose_answer_publisher
from brigade.studies.write_answer_to_pull_request import write_answer_to_pull_request


class ChooseAnswerPublisherTest(unittest.TestCase):
    def test_should_commit_on_the_pull_request_the_answer_of_an_output_naming_a_pull_request_file(self):
        # Act
        publisher = choose_answer_publisher("pr-file:12:docs/usage-reports/12.md")

        # Assert
        self.assertIs(publisher, write_answer_to_pull_request)
