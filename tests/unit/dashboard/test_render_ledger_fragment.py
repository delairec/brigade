import json
import unittest

from brigade.dashboard.render_ledger_fragment import render_ledger_fragment
from brigade.dashboard.run_routed_command import CommandAnswer

OVERVIEW = {
    "schema_version": 1,
    "view": "overview",
    "first": "2026-09-30T22:00:00Z",
    "last": "2026-10-20T09:00:00Z",
    "waves_started": {"2026-10": ["w1", "<b>w2</b>"]},
}
BUDGETS = {
    "schema_version": 1,
    "last": 20,
    "procedures": {
        "build-task": {
            "runs": {"measured": 3, "unmeasured": 0, "p50": 40, "p90": 70, "partial": 0},
            "segments": {"measured": 3, "unmeasured": 0, "p50": 40, "p90": 70},
            "estimate": True,
        },
        "<i>review</i>": {
            "runs": {"measured": 0, "unmeasured": 6, "p50": None, "p90": None, "partial": 0},
            "segments": {"measured": 0, "unmeasured": 6, "p50": None, "p90": None},
            "estimate": False,
        },
    },
}
STEPS_SECTION = (
    "<section><h2>Steps by procedure</h2>"
    "<table><thead><tr><th>procedure</th><th>runs</th><th>p50</th><th>p90</th><th>estimate</th></tr></thead>"
    "<tbody><tr><td>build-task</td><td>3</td><td>40</td><td>70</td><td>yes</td></tr>"
    "<tr><td>&lt;i&gt;review&lt;/i&gt;</td><td>0</td><td>-</td><td>-</td><td>no</td></tr></tbody></table></section>"
)
MONTHS_SECTION = (
    "<section><h2>Waves started by month</h2>"
    "<table><thead><tr><th>month</th><th>waves</th><th>started</th><th>baseline</th></tr></thead>"
    "<tbody><tr><td>2026-10</td><td>2</td>"
    '<td><a href="#ledger?wave=w1">w1</a> <a href="#ledger?wave=%3Cb%3Ew2%3C%2Fb%3E">&lt;b&gt;w2&lt;/b&gt;</a></td>'
    '<td><a href="#ledger?range=2026-09-30..2026-09-30&amp;range=2026-10-01..2026-10-20">compare before 2026-10-01</a>'
    "</td></tr></tbody></table></section>"
)


def answer_with(document: dict) -> CommandAnswer:
    return CommandAnswer(status=200, document=json.dumps(document))


class RenderLedgerFragmentTest(unittest.TestCase):
    def test_should_render_the_steps_by_procedure_and_the_waves_started_by_month(self):
        # Arrange
        answers = {"overview": answer_with(OVERVIEW), "budgets": answer_with(BUDGETS)}

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertEqual(fragment, STEPS_SECTION + MONTHS_SECTION)

    def test_should_render_the_steps_by_role_and_the_pauses_of_the_wave_asked(self):
        # Arrange
        wave = {
            "schema_version": 1,
            "view": "wave",
            "wave": "<b>w2</b>",
            "steps": {
                "by_slot": {},
                "by_role": {
                    "<i>ada</i>": {"runs": {"measured": 2, "unmeasured": 1, "p50": 30, "p90": 50, "partial": 0}}
                },
            },
            "pauses": [
                {
                    "paused_at": "<i>2026-10-02T10:00:00Z</i>",
                    "resumed_at": "<i>2026-10-02T11:05:00Z</i>",
                    "duration_ms": 3900000,
                },
                {"paused_at": "<i>2026-10-03T10:00:00Z</i>", "resumed_at": None, "duration_ms": None},
            ],
        }
        answers = {"overview": answer_with(OVERVIEW), "budgets": answer_with(BUDGETS), "wave": answer_with(wave)}

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertEqual(
            fragment,
            STEPS_SECTION
            + MONTHS_SECTION
            + "<section><h2>Steps by role and pauses of the wave</h2><p>wave &lt;b&gt;w2&lt;/b&gt;</p>"
            "<table><thead><tr><th>role</th><th>runs</th><th>p50</th><th>p90</th></tr></thead>"
            "<tbody><tr><td>&lt;i&gt;ada&lt;/i&gt;</td><td>2</td><td>30</td><td>50</td></tr></tbody></table>"
            "<table><thead><tr><th>paused at</th><th>resumed at</th><th>minutes</th></tr></thead>"
            "<tbody><tr><td>&lt;i&gt;2026-10-02T10:00:00Z&lt;/i&gt;</td><td>&lt;i&gt;2026-10-02T11:05:00Z&lt;/i&gt;</td>"
            "<td>65</td></tr>"
            "<tr><td>&lt;i&gt;2026-10-03T10:00:00Z&lt;/i&gt;</td><td>still paused</td><td>-</td></tr></tbody></table></section>",
        )

    def test_should_render_the_comparison_of_the_two_ranges_asked(self):
        # Arrange
        comparison = {
            "schema_version": 1,
            "ranges": [
                {
                    "start": "<i>2026-09-01</i>",
                    "end": "2026-09-30",
                    "runs": 4,
                    "segments": 5,
                    "steps": {"runs": {"p50": 40, "p90": 80}},
                    "steps_to_first_edit": {"runs": {"p50": 6, "p90": 9}},
                    "oversized_output_steps": None,
                },
                {
                    "start": "2026-10-01",
                    "end": "2026-10-31",
                    "runs": 2,
                    "segments": 2,
                    "steps": {"runs": {"p50": 30, "p90": 45}},
                    "steps_to_first_edit": None,
                    "oversized_output_steps": None,
                },
            ],
            "reference": {},
        }
        answers = {
            "overview": answer_with(OVERVIEW),
            "budgets": answer_with(BUDGETS),
            "comparison": answer_with(comparison),
        }

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertEqual(
            fragment,
            STEPS_SECTION + MONTHS_SECTION + "<section><h2>Baseline comparison</h2>"
            "<p>4 runs from &lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30, 2 runs from 2026-10-01 to 2026-10-31</p>"
            "<table><thead><tr><th>measure</th>"
            "<th>p50 &lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30</th><th>p90 &lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30</th>"
            "<th>p50 2026-10-01 to 2026-10-31</th><th>p90 2026-10-01 to 2026-10-31</th></tr></thead><tbody>"
            "<tr><td>steps</td><td>40</td><td>80</td><td>30</td><td>45</td></tr>"
            "<tr><td>steps to first edit</td><td>6</td><td>9</td><td>-</td><td>-</td></tr>"
            "<tr><td>oversized output steps</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
            "</tbody></table></section>",
        )

    def test_should_render_the_error_of_a_comparison_the_ledger_refused(self):
        # Arrange
        refused = CommandAnswer(status=500, document='{"error": "no run finished from 2026-09-30 to 2026-09-30\\n"}')
        answers = {"overview": answer_with(OVERVIEW), "budgets": answer_with(BUDGETS), "comparison": refused}

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertEqual(
            fragment,
            STEPS_SECTION + MONTHS_SECTION + "<section><h2>Baseline comparison</h2>"
            "<dl><dt>error</dt><dd>no run finished from 2026-09-30 to 2026-09-30\n</dd></dl></section>",
        )
