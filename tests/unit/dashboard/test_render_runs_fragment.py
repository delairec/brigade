import unittest

from brigade.dashboard.render_runs_fragment import render_runs_fragment


class RenderRunsFragmentTest(unittest.TestCase):
    def test_should_link_each_run_to_its_view_inside_or_outside_a_wave_and_escape_its_strings(self):
        # Arrange
        document = {
            "schema_version": 1,
            "runs": [
                {
                    "run": "r1",
                    "procedure": "build-task",
                    "slot": "build",
                    "role": "ada",
                    "project": "oak",
                    "worktree": "/srv/oak/B94",
                    "state": "finished",
                    "outcome": "done",
                    "wave": "oak_w4",
                    "task": "B94",
                },
                {
                    "run": "<i>r2</i>",
                    "procedure": "<b>vibe</b>",
                    "slot": None,
                    "role": None,
                    "project": None,
                    "worktree": None,
                    "state": "running",
                    "outcome": None,
                    "wave": None,
                    "task": None,
                },
            ],
            "skipped": [],
        }

        # Act
        fragment = render_runs_fragment(document)

        # Assert
        self.assertEqual(
            fragment,
            "<table><thead><tr><th>run</th><th>procedure</th><th>project</th><th>wave</th><th>task</th>"
            "<th>state</th><th>outcome</th></tr></thead><tbody>"
            '<tr><td><a href="#runs/r1">r1</a></td><td>build-task</td><td>oak</td><td>oak_w4</td><td>B94</td>'
            "<td>finished</td><td>done</td></tr>"
            '<tr><td><a href="#runs/%3Ci%3Er2%3C%2Fi%3E">&lt;i&gt;r2&lt;/i&gt;</a></td>'
            "<td>&lt;b&gt;vibe&lt;/b&gt;</td><td>-</td><td>-</td><td>-</td><td>running</td><td>-</td></tr>"
            "</tbody></table>",
        )

    def test_should_say_there_is_no_run(self):
        # Arrange
        document = {"schema_version": 1, "runs": [], "skipped": []}

        # Act
        fragment = render_runs_fragment(document)

        # Assert
        self.assertEqual(fragment, "<p>no run</p>")
