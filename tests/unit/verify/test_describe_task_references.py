import tempfile
import unittest
from pathlib import Path

from brigade.verify.describe_task_references import describe_task_references


class DescribeTaskReferencesTest(unittest.TestCase):
    def setUp(self):
        self.captures = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_name_in_order_the_slices_brigade_build_capture_cut_for_a_covered_page(self):
        # Arrange
        (self.captures / "tides-delivered.png").write_bytes(b"png")
        (self.captures / "tides-delivered-02.png").write_bytes(b"png")
        (self.captures / "tides-delivered-01.png").write_bytes(b"png")
        (self.captures / "tides-reference.png").write_bytes(b"png")
        (self.captures / "tides-reference-01.png").write_bytes(b"png")

        # Act
        described = describe_task_references(
            [{"reference": "artifact/harbour/index.html", "covers": "tides", "revises": None, "reads": None}],
            self.captures,
        )

        # Assert
        self.assertEqual(
            described,
            [
                {
                    "reference": "artifact/harbour/index.html",
                    "covers": "tides",
                    "revises": None,
                    "reads": None,
                    "refusal": None,
                    "captures": {
                        "delivered": [
                            str(self.captures / "tides-delivered-01.png"),
                            str(self.captures / "tides-delivered-02.png"),
                        ],
                        "reference": [str(self.captures / "tides-reference-01.png")],
                    },
                }
            ],
        )

    def test_should_name_no_pair_for_a_page_brigade_build_capture_did_not_capture_whole(self):
        for side, sliced in [
            ("the delivered page alone", "tides-delivered-01.png"),
            ("the reference page alone", "tides-reference-01.png"),
        ]:
            with self.subTest(side=side):
                # Arrange
                captures = self.captures / side
                captures.mkdir()
                (captures / sliced).write_bytes(b"png")

                # Act
                described = describe_task_references(
                    [{"reference": "artifact/harbour/index.html", "covers": "tides", "revises": None, "reads": None}],
                    captures,
                )

                # Assert
                self.assertIsNone(described[0]["captures"])

    def test_should_refuse_a_reference_that_is_a_url_and_say_why(self):
        # Act
        described = describe_task_references(
            [{"reference": "https://example.org/harbour", "covers": "tides", "revises": None, "reads": None}],
            self.captures,
        )

        # Assert
        self.assertEqual(
            described[0]["refusal"],
            "a REFERENCE is a repository path: the review cannot open a URL; copy the reference into the repository",
        )
