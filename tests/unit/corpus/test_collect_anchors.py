import unittest

from brigade.corpus.collect_anchors import collect_anchors


class CollectAnchorsTest(unittest.TestCase):
    def test_should_collect_the_anchors_nested_at_any_depth(self):
        # Arrange
        fields = [
            {
                "name": "SPEC",
                "atoms": ['"runs the wave"'],
                "fields": [{"name": "IMPL", "atoms": ['"brigade/cli.py::main"'], "fields": []}],
            },
            {"name": "IMPL", "atoms": ['"brigade/runtime.py::build_runtime"'], "fields": []},
            {"name": "DESC", "atoms": ['"the wave"'], "fields": []},
        ]

        # Act
        anchors = collect_anchors(fields)

        # Assert
        self.assertEqual(anchors, ["brigade/cli.py::main", "brigade/runtime.py::build_runtime"])

    def test_should_keep_in_an_anchor_the_backslash_awawa_keeps(self):
        # Arrange
        fields = [{"name": "IMPL", "atoms": ['"tests/unit/test_x.py::grep a\\.b"'], "fields": []}]

        # Act
        anchors = collect_anchors(fields)

        # Assert
        self.assertEqual(anchors, ["tests/unit/test_x.py::grep a\\.b"])
