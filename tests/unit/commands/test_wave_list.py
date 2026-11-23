import argparse
import contextlib
import io
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.wave_list import COMMAND
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

EVERY_PROJECT = None
EVERY_STATE = None
TIDES_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7", "T8"],
}
TIDES_CANCELLED = {
    "schema_version": 1,
    "ts": "2026-10-01T22:00:00Z",
    "event": "wave.cancelled",
    "wave": "tidepool_w16",
    "reason": "user",
}
GAUGES_STARTED = {
    **TIDES_STARTED,
    "ts": "2026-10-02T22:00:00Z",
    "wave": "gauges_w1",
    "project": "gauges",
    "branch": "integration/gauges_w1",
    "tasks": ["G1"],
}
TIDES_ROW = {
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "last_event": "wave.cancelled",
    "state": "ended",
    "tasks": 2,
    "started_at": "2026-09-30T22:00:00Z",
    "ended_at": "2026-10-01T22:00:00Z",
    "ended_by": "wave.cancelled",
    "task_states": [{"task": "T7", "state": None}, {"task": "T8", "state": None}],
    "halt": None,
    "rounds": 0,
    "cost_usd": None,
}
GAUGES_ROW = {
    "wave": "gauges_w1",
    "project": "gauges",
    "branch": "integration/gauges_w1",
    "last_event": "wave.started",
    "state": "open",
    "tasks": 1,
    "started_at": "2026-10-02T22:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "G1", "state": None}],
    "halt": None,
    "rounds": 0,
    "cost_usd": None,
}
OAK_STARTED = {
    **TIDES_STARTED,
    "ts": "2026-10-03T08:00:00Z",
    "wave": "oak_w2",
    "project": "oak",
    "branch": "integration/oak_w2",
    "tasks": ["B17", "B21"],
}
OAK_RUN = {
    "schema_version": 3,
    "ts": "2026-10-03T09:00:00Z",
    "event": "run.finished",
    "run": "20261003T080500Z-b17a",
    "segment": 1,
    "procedure": "build-task",
    "slot": "build",
    "role": "ada",
    "client": "fake",
    "project": "oak",
    "session": None,
    "main_turns": 12,
    "total_turns": 12,
    "duration_ms": 4200,
    "usage": None,
    "outcome": "done",
    "error_class": None,
    "exit": 0,
    "wave": "oak_w2",
    "task": "B17",
    "nulls": {},
}


def oak_event(event: str, ts: str, **fields) -> dict:
    return {"schema_version": 1, "ts": ts, "event": event, "wave": "oak_w2", **fields}


def list_oak_wave(test: unittest.TestCase, events: list[dict]) -> dict:
    root = Path(test.enterContext(tempfile.TemporaryDirectory()))
    write_ledger(root, [OAK_STARTED, *events])
    runtime = create_test_runtime(create_test_paths(root))
    return COMMAND.run(Namespace(project=EVERY_PROJECT, state=EVERY_STATE), runtime)["waves"][0]


class WaveListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_wave(self):
        # Arrange
        document = {"schema_version": 1, "waves": [GAUGES_ROW, TIDES_ROW]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave          project   branch                    state  last event      tasks\n"
            "gauges_w1     gauges    integration/gauges_w1     open   wave.started    1\n"
            "tidepool_w16  tidepool  integration/tidepool_w16  ended  wave.cancelled  2",
        )


class WaveListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "waves": []})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(project=None, state=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveListOfTheLedgerTest(unittest.TestCase):
    def test_should_list_the_waves_of_the_project_asked_the_open_waves_first(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(root, [TIDES_STARTED, TIDES_CANCELLED, GAUGES_STARTED])
        runtime = create_test_runtime(create_test_paths(root))
        rows = [
            ("every project", EVERY_PROJECT, [GAUGES_ROW, TIDES_ROW]),
            ("one project", "tidepool", [TIDES_ROW]),
        ]
        for case, project, expected_waves in rows:
            with self.subTest(case=case):
                # Act
                document = COMMAND.run(Namespace(project=project, state=EVERY_STATE), runtime)

                # Assert
                self.assertEqual(document, {"schema_version": 1, "waves": expected_waves})

    def test_should_list_no_wave_of_a_ledger_holding_none(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = create_test_runtime(create_test_paths(root))

        # Act
        document = COMMAND.run(Namespace(project=EVERY_PROJECT, state=EVERY_STATE), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "waves": []})


class WaveListOfTheDetailsOfAWaveTest(unittest.TestCase):
    def test_should_give_each_task_its_last_state_and_none_to_a_task_never_served(self):
        # Arrange
        events = [
            oak_event("task.state", "2026-10-03T08:05:00Z", task="B17", state="running", reason=None),
            oak_event("task.state", "2026-10-03T10:00:00Z", task="B17", state="merged", reason=None),
        ]

        # Act
        wave = list_oak_wave(self, events)

        # Assert
        self.assertEqual(wave["task_states"], [{"task": "B17", "state": "merged"}, {"task": "B21", "state": None}])

    def test_should_carry_the_halt_of_a_wave_halted_and_none_once_it_resumed_or_ended(self):
        # Arrange
        parked = oak_event("wave.parked", "2026-10-03T09:00:00Z", reason="forge_account")
        blocked = oak_event("wave.blocked", "2026-10-03T09:00:00Z", reason="quota", resume_at="2026-10-03T14:00:00Z")
        resumed = oak_event("wave.resumed", "2026-10-03T10:00:00Z", reason="user")
        cancelled = oak_event("wave.cancelled", "2026-10-03T10:00:00Z", reason="user")
        rows = [
            ("parked", [parked], {"reason": "forge_account", "resume_at": None}),
            ("blocked", [blocked], {"reason": "quota", "resume_at": "2026-10-03T14:00:00Z"}),
            ("resumed", [parked, resumed], None),
            ("cancelled while parked", [parked, cancelled], None),
        ]
        for case, events, expected_halt in rows:
            with self.subTest(case=case):
                # Act
                wave = list_oak_wave(self, events)

                # Assert
                self.assertEqual(wave["halt"], expected_halt)

    def test_should_carry_the_event_that_ended_a_wave_even_when_a_resume_follows_it(self):
        # Arrange
        events = [
            oak_event("wave.parked", "2026-10-03T09:00:00Z", reason="forge_account"),
            oak_event("wave.cancelled", "2026-10-03T10:00:00Z", reason="user"),
            oak_event("wave.resumed", "2026-10-03T11:00:00Z", reason="user"),
        ]

        # Act
        wave = list_oak_wave(self, events)

        # Assert
        self.assertEqual(wave["ended_by"], "wave.cancelled")

    def test_should_carry_the_most_review_rounds_one_of_its_pull_requests_took(self):
        # Arrange
        events = [
            oak_event("pr.merged", "2026-10-03T10:00:00Z", project="oak", task="B17", pr=40, rounds=1, login=None),
            oak_event("pr.merged", "2026-10-03T11:00:00Z", project="oak", task="B21", pr=41, rounds=3, login=None),
        ]

        # Act
        wave = list_oak_wave(self, events)

        # Assert
        self.assertEqual(wave["rounds"], 3)

    def test_should_sum_the_costs_its_runs_record(self):
        # Arrange
        events = [
            {**OAK_RUN, "cost_usd": 1.5},
            {**OAK_RUN, "run": "20261003T090500Z-b21a", "task": "B21"},
            {**OAK_RUN, "run": "20261003T091000Z-b21b", "task": "B21", "cost_usd": 0.25},
            {**OAK_RUN, "run": "20261003T091500Z-elm1", "wave": "elm_w1", "cost_usd": 4.0},
        ]

        # Act
        wave = list_oak_wave(self, events)

        # Assert
        self.assertEqual(wave["cost_usd"], 1.75)

    def test_should_derive_the_state_of_a_wave_from_its_events(self):
        # Arrange
        parked = oak_event("wave.parked", "2026-10-03T09:00:00Z", reason="forge_account")
        blocked = oak_event("wave.blocked", "2026-10-03T09:30:00Z", reason="quota", resume_at="2026-10-03T14:00:00Z")
        resumed = oak_event("wave.resumed", "2026-10-03T10:00:00Z", reason="user")
        closed = oak_event("wave.closed", "2026-10-03T11:00:00Z")
        cancelled = oak_event("wave.cancelled", "2026-10-03T11:00:00Z", reason="user")
        rows = [
            ("open", [], "open"),
            ("blocked", [blocked], "blocked"),
            ("parked", [parked], "parked"),
            ("blocked after its park", [parked, blocked], "blocked"),
            ("resumed", [parked, resumed], "open"),
            ("closed", [closed], "ended"),
            ("cancelled while parked", [parked, cancelled], "ended"),
        ]
        for case, events, expected_state in rows:
            with self.subTest(case=case):
                # Act
                wave = list_oak_wave(self, events)

                # Assert
                self.assertEqual(wave["state"], expected_state)


OPEN_ELM_STARTED = {**OAK_STARTED, "wave": "elm_w1", "project": "elm", "branch": "integration/elm_w1", "tasks": ["E1"]}
PARKED_ELM_STARTED = {**OPEN_ELM_STARTED, "wave": "elm_w2", "branch": "integration/elm_w2"}
PARKED_ELM = {
    "schema_version": 1,
    "ts": "2026-10-03T09:00:00Z",
    "event": "wave.parked",
    "wave": "elm_w2",
    "reason": "quota",
}
STATED_WAVES = [
    OPEN_ELM_STARTED,
    PARKED_ELM_STARTED,
    PARKED_ELM,
    OAK_STARTED,
    oak_event("wave.parked", "2026-10-03T09:00:00Z", reason="forge_account"),
    GAUGES_STARTED,
    {
        **oak_event("wave.blocked", "2026-10-03T09:00:00Z", reason="quota", resume_at="2026-10-03T14:00:00Z"),
        "wave": "gauges_w1",
    },
    TIDES_STARTED,
    TIDES_CANCELLED,
]
OPEN_ELM_ROW = {
    "wave": "elm_w1",
    "project": "elm",
    "branch": "integration/elm_w1",
    "last_event": "wave.started",
    "state": "open",
    "tasks": 1,
    "started_at": "2026-10-03T08:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "E1", "state": None}],
    "halt": None,
    "rounds": 0,
    "cost_usd": None,
}
PARKED_ELM_ROW = {
    "wave": "elm_w2",
    "project": "elm",
    "branch": "integration/elm_w2",
    "last_event": "wave.parked",
    "state": "parked",
    "tasks": 1,
    "started_at": "2026-10-03T08:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "E1", "state": None}],
    "halt": {"reason": "quota", "resume_at": None},
    "rounds": 0,
    "cost_usd": None,
}
PARKED_OAK_ROW = {
    "wave": "oak_w2",
    "project": "oak",
    "branch": "integration/oak_w2",
    "last_event": "wave.parked",
    "state": "parked",
    "tasks": 2,
    "started_at": "2026-10-03T08:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "B17", "state": None}, {"task": "B21", "state": None}],
    "halt": {"reason": "forge_account", "resume_at": None},
    "rounds": 0,
    "cost_usd": None,
}
BLOCKED_GAUGES_ROW = {
    "wave": "gauges_w1",
    "project": "gauges",
    "branch": "integration/gauges_w1",
    "last_event": "wave.blocked",
    "state": "blocked",
    "tasks": 1,
    "started_at": "2026-10-02T22:00:00Z",
    "ended_at": None,
    "ended_by": None,
    "task_states": [{"task": "G1", "state": None}],
    "halt": {"reason": "quota", "resume_at": "2026-10-03T14:00:00Z"},
    "rounds": 0,
    "cost_usd": None,
}


class WaveListOfAStateTest(unittest.TestCase):
    def test_should_keep_the_waves_in_the_state_asked_alone_or_of_the_project_asked(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(root, STATED_WAVES)
        runtime = create_test_runtime(create_test_paths(root))
        rows = [
            ("open", EVERY_PROJECT, "open", [OPEN_ELM_ROW]),
            ("blocked", EVERY_PROJECT, "blocked", [BLOCKED_GAUGES_ROW]),
            ("parked", EVERY_PROJECT, "parked", [PARKED_ELM_ROW, PARKED_OAK_ROW]),
            ("ended", EVERY_PROJECT, "ended", [TIDES_ROW]),
            ("parked of one project", "oak", "parked", [PARKED_OAK_ROW]),
            ("open of a project holding none", "oak", "open", []),
        ]
        for case, project, state, expected_waves in rows:
            with self.subTest(case=case):
                # Act
                document = COMMAND.run(Namespace(project=project, state=state), runtime)

                # Assert
                self.assertEqual(document, {"schema_version": 1, "waves": expected_waves})

    def test_should_refuse_a_state_other_than_the_four_as_a_usage_error(self):
        # Arrange
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (COMMAND,), argparse.ArgumentParser(add_help=False))
        errors = io.StringIO()

        # Act
        with self.assertRaises(SystemExit) as refusal, contextlib.redirect_stderr(errors):
            parser.parse_args(["wave", "list", "--state", "running"])

        # Assert
        self.assertEqual(refusal.exception.code, 2)
        self.assertIn("[--state {open,blocked,parked,ended}]", errors.getvalue())
        self.assertIn("argument --state: invalid choice: 'running'", errors.getvalue())
