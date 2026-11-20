import json
import unittest

from brigade.dashboard.render_waves_view import render_waves_view
from brigade.dashboard.run_routed_command import CommandAnswer

OK = 200
EVERY_STATE = None
OPEN_WAVE = {
    "wave": "oak_w5",
    "project": "oak",
    "branch": "integration/oak_w5",
    "last_event": "wave.started",
    "state": "open",
    "tasks": 3,
    "started_at": "2026-11-02T08:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [
        {"task": "B1", "state": "merged"},
        {"task": "B2", "state": "running"},
        {"task": "B3", "state": "merged"},
    ],
    "halt": None,
    "rounds": 2,
    "cost_usd": 3.5,
}
PARKED_WAVE = {
    "wave": "oak_w4",
    "project": "oak",
    "branch": "integration/oak_w4",
    "last_event": "wave.parked",
    "state": "parked",
    "tasks": 1,
    "started_at": "2026-11-01T08:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "B4", "state": "parked"}],
    "halt": {"reason": "forge_account", "resume_at": None},
    "rounds": 0,
    "cost_usd": None,
}
BLOCKED_WAVE = {
    "wave": "oak_w3",
    "project": "oak",
    "branch": "integration/oak_w3",
    "last_event": "wave.blocked",
    "state": "blocked",
    "tasks": 1,
    "started_at": "2026-11-01T06:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "B4", "state": "blocked:quota"}],
    "halt": {"reason": "quota", "resume_at": "2026-11-01T14:00:00Z"},
    "rounds": 0,
    "cost_usd": 0.5,
}
CLOSED_WAVE = {
    "wave": "oak_w2",
    "project": "oak",
    "branch": "integration/oak_w2",
    "last_event": "wave.closed",
    "state": "ended",
    "tasks": 1,
    "started_at": "2026-10-20T08:00:00Z",
    "ended_at": "2026-10-21T09:30:00Z",
    "ended_by": "wave.closed",
    "task_states": [{"task": "B5", "state": "merged"}],
    "halt": None,
    "rounds": 1,
    "cost_usd": 2.4,
}
CANCELLED_WAVE = {
    "wave": "oak_w1",
    "project": "oak",
    "branch": "integration/oak_w1",
    "last_event": "wave.cancelled",
    "state": "ended",
    "tasks": 1,
    "started_at": "2026-10-10T08:00:00Z",
    "ended_at": "2026-10-10T09:00:00Z",
    "ended_by": "wave.cancelled",
    "task_states": [{"task": "B4", "state": None}],
    "halt": None,
    "rounds": 0,
    "cost_usd": None,
}
RESUMED_AFTER_CANCEL_WAVE = {
    **CANCELLED_WAVE,
    "wave": "oak_w0",
    "last_event": "wave.resumed",
}
EVERY_WAVE = [OPEN_WAVE, PARKED_WAVE, BLOCKED_WAVE, CLOSED_WAVE, CANCELLED_WAVE]
WAVES_STARTED = {"2026-10": ["oak_w1", "oak_w2"], "2026-11": ["oak_w3", "oak_w4", "oak_w5"]}
TASK_SERVED_THRICE_HEADING = "<h2>Tasks served by three waves or more</h2>"


def create_answers(waves: list[dict], waves_started: dict) -> dict[str, CommandAnswer]:
    listing = {"schema_version": 1, "waves": waves}
    overview = {"schema_version": 1, "view": "overview", "waves_started": waves_started}
    return {
        "document": CommandAnswer(status=OK, document=json.dumps(listing)),
        "overview": CommandAnswer(status=OK, document=json.dumps(overview)),
    }


def create_narrowed_answers(narrowed: list[dict], waves: list[dict], waves_started: dict) -> dict[str, CommandAnswer]:
    answers = create_answers(narrowed, waves_started)
    every = {"schema_version": 1, "waves": waves}
    return {**answers, "every": CommandAnswer(status=OK, document=json.dumps(every))}


def create_closed_wave(wave: str, started_at: str, task_states: list[dict]) -> dict:
    return {**CLOSED_WAVE, "wave": wave, "started_at": started_at, "task_states": task_states}


class RenderWavesViewTest(unittest.TestCase):
    def test_should_open_on_the_count_of_the_open_the_parked_and_the_blocked_waves(self):
        # Arrange
        answers = create_answers(EVERY_WAVE, WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn('<p class="status-sentence">Waves open: 3, parked: 1, blocked: 1.</p>', fragment)

    def test_should_sum_up_the_waves_in_four_tiles(self):
        # Arrange
        answers = create_answers(EVERY_WAVE, WAVES_STARTED)
        rows = [
            (
                "open now",
                (
                    '<div class="stat-tile"><span class="stat-value">3</span><span class="stat-label">open now</span>'
                    '<span class="stat-perimeter">1 parked, 1 blocked</span></div>'
                ),
            ),
            (
                "started",
                (
                    '<div class="stat-tile"><span class="stat-value">5</span><span class="stat-label">started</span>'
                    '<span class="stat-perimeter">by month: 2026-10 2, 2026-11 3</span></div>'
                ),
            ),
            (
                "closed",
                (
                    '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">closed</span>'
                    '<span class="stat-perimeter">1 cancelled</span></div>'
                ),
            ),
            (
                "tasks merged",
                (
                    '<div class="stat-tile"><span class="stat-value">3 of 7</span>'
                    '<span class="stat-label">tasks merged</span>'
                    '<span class="stat-perimeter">over the last 12 waves, 3 merged nothing</span></div>'
                ),
            ),
        ]
        for case, expected_tile in rows:
            with self.subTest(tile=case):
                # Act
                fragment = render_waves_view(answers, EVERY_STATE)

                # Assert
                self.assertIn(expected_tile, fragment)

    def test_should_count_by_month_the_waves_listed_alone(self):
        # Arrange
        answers = create_answers([OPEN_WAVE], {"2026-11": ["elm_w9", "oak_w5"]})

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn('<span class="stat-perimeter">by month: 2026-11 1</span>', fragment)

    def test_should_count_the_tasks_merged_over_the_last_12_waves_started(self):
        # Arrange
        merged = [{"task": "B9", "state": "merged"}]
        unmerged = [{"task": "B8", "state": "parked"}]
        waves = [
            create_closed_wave("w13", "2026-10-13T08:00:00Z", unmerged),
            create_closed_wave("w12", "2026-10-12T08:00:00Z", merged),
            create_closed_wave("w11", "2026-10-11T08:00:00Z", merged),
            create_closed_wave("w10", "2026-10-10T08:00:00Z", merged),
            create_closed_wave("w9", "2026-10-09T08:00:00Z", merged),
            create_closed_wave("w8", "2026-10-08T08:00:00Z", merged),
            create_closed_wave("w7", "2026-10-07T08:00:00Z", merged),
            create_closed_wave("w6", "2026-10-06T08:00:00Z", merged),
            create_closed_wave("w5", "2026-10-05T08:00:00Z", merged),
            create_closed_wave("w4", "2026-10-04T08:00:00Z", merged),
            create_closed_wave("w3", "2026-10-03T08:00:00Z", merged),
            create_closed_wave("w2", "2026-10-02T08:00:00Z", merged),
            create_closed_wave("w1", "2026-10-01T08:00:00Z", merged),
        ]
        answers = create_answers(waves, WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn(
            '<span class="stat-value">11 of 12</span><span class="stat-label">tasks merged</span>'
            '<span class="stat-perimeter">over the last 12 waves, 1 merged nothing</span>',
            fragment,
        )

    def test_should_show_the_state_of_each_wave_its_list_names_as_a_pill(self):
        # Arrange
        rows = [
            ("open", OPEN_WAVE, "tone-work", "●", "open"),
            ("parked", PARKED_WAVE, "tone-you", "▲", "parked"),
            ("blocked", BLOCKED_WAVE, "tone-you", "▲", "blocked"),
            ("closed", CLOSED_WAVE, "tone-done", "✓", "ended"),
            ("cancelled", CANCELLED_WAVE, "tone-done", "✓", "ended"),
        ]
        for case, wave, tone, shape, word in rows:
            with self.subTest(wave=case):
                # Arrange
                answers = create_answers([wave], WAVES_STARTED)

                # Act
                fragment = render_waves_view(answers, EVERY_STATE)

                # Assert
                self.assertIn(
                    f'<td><span class="pill"><span class="tone {tone}">'
                    f'<span class="tone-shape" aria-hidden="true">{shape}</span>{word}</span></span></td>',
                    fragment,
                )

    def test_should_count_a_wave_resumed_after_its_cancel_out_of_the_open_waves(self):
        # Arrange
        answers = create_answers([RESUMED_AFTER_CANCEL_WAVE], {"2026-10": ["oak_w0"]})

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn('<p class="status-sentence">Waves open: 0, parked: 0, blocked: 0.</p>', fragment)

    def test_should_count_a_wave_resumed_after_its_cancel_among_the_cancelled(self):
        # Arrange
        answers = create_answers([RESUMED_AFTER_CANCEL_WAVE], {"2026-10": ["oak_w0"]})

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn('<span class="stat-label">closed</span><span class="stat-perimeter">1 cancelled</span>', fragment)

    def test_should_draw_the_tasks_of_a_wave_of_mixed_states_as_a_stacked_bar(self):
        # Arrange
        answers = create_answers([OPEN_WAVE], WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn(
            '<td><svg class="segment-strip" viewBox="0 0 100 8" role="img" aria-label="3 tasks">'
            '<rect class="segment tone-done" x="0" width="66.6667" height="8"><title>2 merged</title></rect>'
            '<rect class="segment tone-work" x="66.6667" width="33.3333" height="8"><title>1 running</title></rect>'
            "</svg></td>",
            fragment,
        )

    def test_should_count_a_task_without_state_as_queued(self):
        # Arrange
        answers = create_answers([CANCELLED_WAVE], WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn(
            '<rect class="segment tone-faint" x="0" width="100" height="8"><title>1 queued</title></rect>', fragment
        )

    def test_should_link_the_page_of_the_wave_and_show_its_dates_its_rounds_and_its_cost_as_a_floor(self):
        # Arrange
        rows = [
            (
                "ended with a cost",
                CLOSED_WAVE,
                "<td>2026-10-20T08:00:00Z</td><td>2026-10-21T09:30:00Z</td><td>1</td><td>at least 2.40 USD</td>",
            ),
            ("open without a cost", PARKED_WAVE, "<td>2026-11-01T08:00:00Z</td><td>-</td><td>0</td><td>-</td>"),
        ]
        for case, wave, expected_cells in rows:
            with self.subTest(wave=case):
                # Arrange
                answers = create_answers([wave], WAVES_STARTED)

                # Act
                fragment = render_waves_view(answers, EVERY_STATE)

                # Assert
                self.assertIn(f'<tr><td><a href="#waves/{wave["wave"]}">{wave["wave"]}</a></td>', fragment)
                self.assertIn(f"{expected_cells}</tr>", fragment)

    def test_should_name_the_tasks_served_by_three_waves_or_more_with_their_count(self):
        # Arrange
        answers = create_answers(EVERY_WAVE, WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn(f"<section>{TASK_SERVED_THRICE_HEADING}<ul><li>B4 of oak, 3 waves</li></ul></section>", fragment)

    def test_should_leave_out_the_heading_of_the_tasks_served_again_when_none_was_served_thrice(self):
        # Arrange
        answers = create_answers([OPEN_WAVE, PARKED_WAVE, BLOCKED_WAVE], WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertNotIn(TASK_SERVED_THRICE_HEADING, fragment)

    def test_should_escape_a_wave_name_holding_markup(self):
        # Arrange
        answers = create_answers([{**OPEN_WAVE, "wave": "<b>w</b>"}], WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn('<a href="#waves/%3Cb%3Ew%3C%2Fb%3E">&lt;b&gt;w&lt;/b&gt;</a>', fragment)
        self.assertNotIn("<b>w</b>", fragment)


class RenderWavesViewOfAStateTest(unittest.TestCase):
    def test_should_offer_one_chip_per_state_and_mark_the_one_in_force(self):
        # Arrange
        answers = create_answers([PARKED_WAVE], WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, "parked")

        # Assert
        self.assertIn(
            '<nav class="chips"><a class="chip" href="#waves">every state</a>'
            '<a class="chip" href="#waves?state=open">open</a>'
            '<a class="chip" href="#waves?state=blocked">blocked</a>'
            '<a class="chip" href="#waves?state=parked" aria-current="true">parked</a>'
            '<a class="chip" href="#waves?state=ended">ended</a></nav>',
            fragment,
        )

    def test_should_count_the_sentence_and_the_tiles_over_every_wave_while_a_state_narrows_the_list(self):
        # Arrange
        answers = create_narrowed_answers([CLOSED_WAVE, CANCELLED_WAVE], EVERY_WAVE, WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, "ended")

        # Assert
        self.assertIn('<p class="status-sentence">Waves open: 3, parked: 1, blocked: 1.</p>', fragment)
        self.assertIn(
            '<span class="stat-value">3</span><span class="stat-label">open now</span>'
            '<span class="stat-perimeter">1 parked, 1 blocked</span>',
            fragment,
        )
        self.assertIn('<span class="stat-perimeter">by month: 2026-10 2, 2026-11 3</span>', fragment)
        self.assertIn('<a href="#waves/oak_w2">oak_w2</a>', fragment)
        self.assertNotIn('<a href="#waves/oak_w5">oak_w5</a>', fragment)

    def test_should_mark_every_state_in_force_when_no_state_is_asked(self):
        # Arrange
        answers = create_answers([PARKED_WAVE], WAVES_STARTED)

        # Act
        fragment = render_waves_view(answers, EVERY_STATE)

        # Assert
        self.assertIn('<a class="chip" href="#waves" aria-current="true">every state</a>', fragment)
