import unittest

from brigade.ledger.render_wave_lines import render_wave_lines


class RenderWaveLinesTest(unittest.TestCase):
    def test_should_present_the_course_of_the_wave(self):
        # Arrange
        build_steps = {
            "runs": {"p50": 40, "p90": 52, "measured": 2, "partial": 0, "unmeasured": 0},
            "segments": {"p50": 40, "p90": 52, "measured": 2, "unmeasured": 0},
        }
        document = {
            "view": "wave",
            "wave": "tidepool_w16",
            "first": "2026-09-30T22:00:00Z",
            "last": "2026-10-01T02:30:00Z",
            "wall_time_ms": 16200000,
            "tasks": ["T7", "T8"],
            "cost_usd": 4.75,
            "usage": {
                "input_tokens": 11,
                "output_tokens": 22,
                "cache_creation_input_tokens": 33,
                "cache_read_input_tokens": 44,
            },
            "by_task": [
                {"task": "T7", "turns": 80, "partial": True, "duration_ms": 1500000, "cost_usd": 4.75},
                {"task": "T8", "turns": None, "partial": False, "duration_ms": None, "cost_usd": None},
            ],
            "pull_requests": [{"task": "T7", "pr": 42, "rounds": 2}],
            "turns": {"by_slot": {"build": build_steps}, "by_role": {}},
            "halts": [
                {"halted_at": "2026-10-01T00:15:00Z", "resumed_at": "2026-10-01T01:15:00Z", "duration_ms": 3600000},
                {"halted_at": "2026-10-01T02:00:00Z", "resumed_at": None, "duration_ms": None},
            ],
            "halted_ms": 3600000,
            "handovers": [{"task": "T7", "role": "ada", "slot": "build", "segment": 2}],
            "parked": [],
            "events": [],
        }

        # Act
        text = "\n".join(render_wave_lines(document))

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w16: 2026-09-30T22:00:00Z to 2026-10-01T02:30:00Z, wall time 4h30m\n"
            "cost: 4.75 USD\n"
            "tokens: input 11, output 22, cache creation 33, cache read 44\n"
            "tasks:\n"
            "  T7  turns 80 partial  duration 0h25m  cost 4.75 USD\n"
            "  T8  turns -  duration -  cost -\n"
            "pull requests: #42 T7 rounds 2\n"
            "turns by slot:\n"
            "  build\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "turns by role: none\n"
            "halts: 2, 1h00m in all\n"
            "  2026-10-01T00:15:00Z to 2026-10-01T01:15:00Z  1h00m\n"
            "  2026-10-01T02:00:00Z, still halted\n"
            "handovers: T7 ada build segment 2\n"
            "parked: none\n"
            "events:",
        )

    def test_should_print_none_for_what_the_wave_did_not_do(self):
        # Arrange
        document = {
            "view": "wave",
            "wave": "tidepool_w17",
            "first": "2026-10-02T09:00:00Z",
            "last": "2026-10-03T09:00:00Z",
            "wall_time_ms": 86400000,
            "tasks": [],
            "cost_usd": None,
            "usage": None,
            "by_task": [],
            "pull_requests": [],
            "turns": {"by_slot": {}, "by_role": {}},
            "halts": [{"halted_at": "2026-10-02T10:00:00Z", "resumed_at": None, "duration_ms": None}],
            "halted_ms": 0,
            "handovers": [],
            "parked": [],
            "events": [],
        }

        # Act
        text = "\n".join(render_wave_lines(document))

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w17: 2026-10-02T09:00:00Z to 2026-10-03T09:00:00Z, wall time 24h00m\n"
            "cost: none\n"
            "tokens: none\n"
            "tasks: none\n"
            "pull requests: none\n"
            "turns by slot: none\n"
            "turns by role: none\n"
            "halts: 1, 0h00m in all\n"
            "  2026-10-02T10:00:00Z, still halted\n"
            "handovers: none\n"
            "parked: none\n"
            "events:",
        )

    def test_should_present_the_steps_of_each_role_and_the_parked_tasks(self):
        # Arrange
        ada_steps = {
            "runs": {"p50": 40, "p90": 40, "measured": 1, "partial": 1, "unmeasured": 0},
            "segments": {"p50": 40, "p90": 40, "measured": 1, "unmeasured": 1},
        }
        document = {
            "view": "wave",
            "wave": "tidepool_w18",
            "first": "2026-10-04T09:00:00Z",
            "last": "2026-10-04T10:00:00Z",
            "wall_time_ms": 3600000,
            "tasks": ["TP147"],
            "cost_usd": None,
            "usage": None,
            "by_task": [{"task": "TP147", "turns": 40, "partial": False, "duration_ms": 60000, "cost_usd": None}],
            "pull_requests": [],
            "turns": {"by_slot": {}, "by_role": {"ada": ada_steps}},
            "halts": [],
            "halted_ms": 0,
            "handovers": [],
            "parked": ["TP147"],
            "events": [],
        }

        # Act
        text = "\n".join(render_wave_lines(document))

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w18: 2026-10-04T09:00:00Z to 2026-10-04T10:00:00Z, wall time 1h00m\n"
            "cost: none\n"
            "tokens: none\n"
            "tasks:\n"
            "  TP147  turns 40  duration 0h01m  cost -\n"
            "pull requests: none\n"
            "turns by slot: none\n"
            "turns by role:\n"
            "  ada\n"
            "    runs p50 40  p90 40  measured 1  partial 1  unmeasured 0\n"
            "    segments p50 40  p90 40  measured 1  unmeasured 1\n"
            "halts: 0, 0h00m in all\n"
            "handovers: none\n"
            "parked: TP147\n"
            "events:",
        )

    def test_should_list_each_event_of_the_wave_with_the_task_it_names(self):
        # Arrange
        document = {
            "view": "wave",
            "wave": "tidepool_w18",
            "first": "2026-10-04T09:00:00Z",
            "last": "2026-10-04T10:00:00Z",
            "wall_time_ms": 3600000,
            "tasks": ["T9"],
            "cost_usd": None,
            "usage": None,
            "by_task": [],
            "pull_requests": [],
            "turns": {"by_slot": {}, "by_role": {}},
            "halts": [],
            "halted_ms": 0,
            "handovers": [],
            "parked": [],
            "events": [
                {"at": "2026-10-04T09:00:00Z", "event": "wave.started", "fields": {"wave": "tidepool_w18"}},
                {"at": "2026-10-04T10:00:00Z", "event": "task.state", "fields": {"task": "T9", "state": "merged"}},
            ],
        }

        # Act
        text = "\n".join(render_wave_lines(document))

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w18: 2026-10-04T09:00:00Z to 2026-10-04T10:00:00Z, wall time 1h00m\n"
            "cost: none\n"
            "tokens: none\n"
            "tasks: none\n"
            "pull requests: none\n"
            "turns by slot: none\n"
            "turns by role: none\n"
            "halts: 0, 0h00m in all\n"
            "handovers: none\n"
            "parked: none\n"
            "events:\n"
            "  2026-10-04T09:00:00Z  wave.started\n"
            "  2026-10-04T10:00:00Z  task.state  T9",
        )
