import unittest

from brigade.verify.check_body import check_body


class CheckBodyTest(unittest.TestCase):
    def test_should_pass_a_body_with_every_placeholder_filled(self):
        # Act
        check = check_body("feat(cart): empty the cart\n\nDelivers @TASK.S3.\n")

        # Assert
        self.assertEqual(check, {"name": "body", "verdict": "pass", "findings": []})

    def test_should_fail_a_body_keeping_a_placeholder_of_its_template(self):
        # Act
        check = check_body("feat(cart): ${title}\n\n$specs\n")

        # Assert
        self.assertEqual(
            check,
            {
                "name": "body",
                "verdict": "fail",
                "findings": ["the body keeps the placeholder $title", "the body keeps the placeholder $specs"],
            },
        )
