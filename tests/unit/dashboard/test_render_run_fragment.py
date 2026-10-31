import unittest

from brigade.dashboard.render_run_fragment import render_run_fragment

RUNNING_RUN = {
    "run": "r1",
    "procedure": "build-task",
    "slot": "build",
    "role": "ada",
    "project": "oak",
    "worktree": "/srv/oak/B94",
    "state": "running",
    "outcome": None,
    "wave": "oak_w4",
    "task": "B94",
    "message": None,
}
FIRST_SEGMENT_HANDED_OVER = {"segment": 1, "outcome": "handed_over", "steps": 75, "duration_ms": 754000}
SECOND_SEGMENT_RUNNING = {"segment": 2, "outcome": None, "steps": None, "duration_ms": None}


class RenderRunFragmentTest(unittest.TestCase):
    def test_should_show_the_run_its_segments_and_its_progress(self):
        # Arrange
        document = {
            "schema_version": 1,
            "run": RUNNING_RUN,
            "segments": [FIRST_SEGMENT_HANDED_OVER, SECOND_SEGMENT_RUNNING],
            "journal": None,
            "progress": {"text": 'STEP s1\n\tDONE "read the package"\n', "entities": None},
        }

        # Act
        fragment = render_run_fragment(document)

        # Assert
        self.assertEqual(
            fragment,
            "<h2>Run r1</h2><dl>"
            "<dt>procedure</dt><dd>build-task</dd><dt>slot</dt><dd>build</dd><dt>role</dt><dd>ada</dd>"
            "<dt>project</dt><dd>oak</dd><dt>wave</dt><dd>oak_w4</dd><dt>task</dt><dd>B94</dd>"
            "<dt>worktree</dt><dd>/srv/oak/B94</dd><dt>state</dt><dd>running</dd><dt>outcome</dt><dd>-</dd>"
            "<dt>message</dt><dd>-</dd></dl>"
            "<h3>Segments</h3><table><thead><tr><th>segment</th><th>outcome</th><th>steps</th><th>duration</th>"
            "</tr></thead><tbody><tr><td>1</td><td>handed_over</td><td>75</td><td>12m34s</td></tr>"
            "<tr><td>2</td><td>-</td><td>-</td><td>-</td></tr></tbody></table>"
            "<h3>Progress</h3><pre>STEP s1\n\tDONE &quot;read the package&quot;\n</pre>",
        )

    def test_should_show_no_progress_section_for_a_run_that_wrote_none(self):
        # Arrange
        no_segment = []
        document = {"schema_version": 1, "run": RUNNING_RUN, "segments": no_segment, "journal": None, "progress": None}

        # Act
        fragment = render_run_fragment(document)

        # Assert
        self.assertNotIn("Progress", fragment)
        self.assertIn("<h3>Segments</h3><p>no segment</p>", fragment)

    def test_should_escape_every_string_of_the_run_and_of_its_progress(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        document = {
            "schema_version": 1,
            "run": {**RUNNING_RUN, "run": markup, "procedure": markup, "message": markup, "outcome": markup},
            "segments": [{**FIRST_SEGMENT_HANDED_OVER, "outcome": markup}],
            "journal": None,
            "progress": {"text": markup, "entities": None},
        }

        # Act
        fragment = render_run_fragment(document)

        # Assert
        self.assertNotIn("<script>", fragment)
