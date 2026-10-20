import unittest

from brigade.system.validate_document import DocumentInvalid
from brigade.verify.validate_verdict import validate_verdict

BROKEN_RULE = {"grade": "medium", "file": "src/tides.py", "line": 12, "broken": "@RULE.kiss"}


class ValidateVerdictTest(unittest.TestCase):
    def test_should_accept_a_verdict_whose_findings_each_name_their_grade_file_line_and_what_they_break(self):
        # Arrange
        rows = [
            ("a pass without a finding", {"verdict": "pass", "findings": []}),
            ("a pass with a finding", {"verdict": "pass", "findings": [BROKEN_RULE]}),
            ("changes with a finding", {"verdict": "changes", "findings": [BROKEN_RULE]}),
        ]
        for case, verdict in rows:
            with self.subTest(case=case):
                # Act
                outcome = validate_verdict(verdict)

                # Assert
                self.assertIsNone(outcome)

    def test_should_refuse_a_verdict_naming_what_is_wrong(self):
        # Arrange
        rows = [
            ("not an object", ["pass"], "the document is a list, not an object"),
            (
                "neither pass nor changes",
                {"verdict": "maybe", "findings": []},
                "verdict is 'maybe', not one of pass, changes",
            ),
            ("without findings", {"verdict": "pass"}, "lacks the key findings"),
            (
                "a finding of no known grade",
                {"verdict": "changes", "findings": [{**BROKEN_RULE, "grade": "blocker"}]},
                "findings[0].grade is 'blocker', not one of critical, high, medium, low",
            ),
            (
                "a finding without its file",
                {"verdict": "changes", "findings": [{"grade": "low", "line": 12, "broken": "@RULE.kiss"}]},
                "lacks the key findings[0].file",
            ),
            (
                "a finding whose line is no number",
                {"verdict": "changes", "findings": [{**BROKEN_RULE, "line": "12"}]},
                "findings[0].line is a string, not an integer",
            ),
            (
                "a finding without what it breaks",
                {"verdict": "changes", "findings": [{"grade": "low", "file": "src/tides.py", "line": 12}]},
                "lacks the key findings[0].broken",
            ),
            ("changes without a finding", {"verdict": "changes", "findings": []}, "a verdict changes names no finding"),
        ]
        for case, verdict, expected_message in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(DocumentInvalid) as raised:
                    validate_verdict(verdict)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)
