import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.wave_show import COMMAND
from brigade.errors import BrigadeError
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.commands.command_runtime import create_machine_double, write_ledger, write_operational_corpus
from tests.unit.commands.run_directories import create_run_record, create_run_result, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7", "T8"],
}
T7_RUNNING = {
    "schema_version": 1,
    "ts": "2026-10-01T09:00:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "running",
}
T7_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-01T21:00:00Z",
    "event": "task.pr_opened",
    "project": "tidepool",
    "task": "T7",
    "wave": "tidepool_w16",
    "branch": "task/tidepool_w16/T7",
    "pr": 42,
    "login": "tidepool-bot",
}
T7_RUN_FINISHED = {
    **create_run_result("20261001T090000Z-a1", "done", "2026-10-01T21:30:00Z"),
    "wave": "tidepool_w16",
    "task": "T7",
}
T7_PR_OPEN = {**T7_RUNNING, "ts": "2026-10-01T22:00:00Z", "state": "pr_open"}
T8_QUEUED = {**T7_RUNNING, "task": "T8", "state": "queued"}
T8_PARKED = {
    "schema_version": 1,
    "ts": "2026-10-01T10:00:00Z",
    "event": "task.parked",
    "wave": "tidepool_w16",
    "task": "T8",
    "reason": "blocked",
    "blockers": ["OPEN_QUESTION.Undecided"],
}

WAVE_BLOCKED = {
    "schema_version": 1,
    "ts": "2026-10-02T08:00:00Z",
    "event": "wave.blocked",
    "wave": "tidepool_w16",
    "reason": "quota",
    "resume_at": "2026-10-02T13:00:00Z",
}
WAVE_PARKED = {
    "schema_version": 1,
    "ts": "2026-10-02T08:30:00Z",
    "event": "wave.parked",
    "wave": "tidepool_w16",
    "reason": "forge_account",
}
WAVE_RESUMED = {
    "schema_version": 1,
    "ts": "2026-10-02T08:40:00Z",
    "event": "wave.resumed",
    "wave": "tidepool_w16",
    "reason": "forge_account",
}
WAVE_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-02T09:00:00Z",
    "event": "wave.pr_opened",
    "wave": "tidepool_w16",
    "pr": 77,
    "login": "tidepool-cli",
}


class WaveShowTextTest(unittest.TestCase):
    def test_should_print_the_wave_and_one_row_per_task(self):
        # Arrange
        document = {
            "schema_version": 1,
            "wave": "tidepool_w16",
            "project": "tidepool",
            "branch": "integration/tidepool_w16",
            "started_at": "2026-09-30T22:00:00Z",
            "last_event": "wave.started",
            "merge_command": None,
            "task_merge_commands": [],
            "pull_request": 77,
            "halt": None,
            "tasks": [
                {"task": "T7", "state": "pr_open", "pull_request": 42, "run": "20261001T090000Z-a1", "reason": None},
                {
                    "task": "T8",
                    "state": "parked",
                    "pull_request": None,
                    "run": None,
                    "reason": "run 20261001T120000Z-b2 blocked: Keep the guard?",
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w16 of @PROJECT.tidepool on integration/tidepool_w16,"
            " started 2026-09-30T22:00:00Z, last event wave.started, pull request 77\n"
            "task  state    pull request  run                  reason\n"
            "T7    pr_open  42            20261001T090000Z-a1  -\n"
            "T8    parked   -             -                    run 20261001T120000Z-b2 blocked: Keep the guard?",
        )


class WaveShowExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(wave="tidepool_w16", events=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


def read_no_live_blocker(run_process, root: Path, task: str) -> tuple[str, ...]:
    return ()


class WaveShowOfTheLedgerTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(
                CORPUS_OF_TWO_INDEPENDENT_TASKS, {**MACHINE_OUTPUTS, **NOTHING_IMPLEMENTED}
            ),
            read_live_blockers=read_no_live_blocker,
        )

    def test_should_show_each_task_with_its_last_state_its_pull_request_and_its_run(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, T7_RUNNING, T7_PR_OPENED, T7_RUN_FINISHED, T7_PR_OPEN])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "wave": "tidepool_w16",
                "project": "tidepool",
                "branch": "integration/tidepool_w16",
                "started_at": "2026-09-30T22:00:00Z",
                "last_event": "wave.started",
                "pull_request": None,
                "merge_command": None,
                "task_merge_commands": [],
                "halt": None,
                "tasks": [
                    {
                        "task": "T7",
                        "state": "pr_open",
                        "pull_request": 42,
                        "run": "20261001T090000Z-a1",
                        "reason": None,
                    },
                    {"task": "T8", "state": None, "pull_request": None, "run": None, "reason": None},
                ],
            },
        )

    def test_should_carry_the_halt_of_a_wave_blocked_or_parked_since_its_last_resume(self):
        for case, events, expected in [
            (
                "blocked",
                [WAVE_STARTED, WAVE_PARKED, WAVE_RESUMED, WAVE_BLOCKED],
                {"reason": "quota", "resume_at": "2026-10-02T13:00:00Z"},
            ),
            ("parked", [WAVE_STARTED, WAVE_BLOCKED, WAVE_PARKED], {"reason": "forge_account", "resume_at": None}),
            ("resumed", [WAVE_STARTED, WAVE_PARKED, WAVE_RESUMED], None),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, events)

                # Act
                document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

                # Assert
                self.assertEqual(document["halt"], expected)

    def test_should_print_the_line_of_a_halted_wave(self):
        for case, events, expected_line in [
            (
                "blocked",
                [WAVE_STARTED, WAVE_BLOCKED],
                "wave tidepool_w16 blocked until 2026-10-02T13:00:00Z: quota",
            ),
            (
                "parked",
                [WAVE_STARTED, WAVE_PARKED],
                "wave tidepool_w16 parked: forge_account; it waits for brigade wave resume tidepool_w16",
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, events)
                document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text.splitlines()[1], expected_line)

    def test_should_show_the_integration_pull_request_the_tick_opened(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, T7_PR_OPEN, WAVE_PR_OPENED])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

        # Assert
        self.assertEqual(document["pull_request"], 77)

    def test_should_show_a_task_its_blockers_parked_as_parked(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, T8_QUEUED, T8_PARKED])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {"task": "T7", "state": None, "pull_request": None, "run": None, "reason": None},
                {"task": "T8", "state": "parked", "pull_request": None, "run": None, "reason": "blocked"},
            ],
        )

    def test_should_name_no_cause_for_a_queued_task_of_a_closed_wave(self):
        # Arrange
        closed = {"schema_version": 1, "ts": "2026-10-03T09:00:00Z", "event": "wave.closed", "wave": "tidepool_w16"}
        write_ledger(self.root, [WAVE_STARTED, T8_QUEUED, closed])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

        # Assert
        self.assertEqual(
            document["tasks"][1], {"task": "T8", "state": "queued", "pull_request": None, "run": None, "reason": None}
        )

    def test_should_name_the_amendment_of_its_entity_as_the_reason_a_task_is_fixing(self):
        # Arrange
        rebuilt = {
            **T7_PR_OPEN,
            "state": "fixing",
            "reason": "the entity of the task amended on integration/tidepool_w16",
        }
        write_ledger(self.root, [WAVE_STARTED, T7_PR_OPEN, rebuilt])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

        # Assert
        self.assertEqual(
            document["tasks"][0],
            {
                "task": "T7",
                "state": "fixing",
                "pull_request": None,
                "run": None,
                "reason": "the entity of the task amended on integration/tidepool_w16",
            },
        )

    def test_should_show_no_reason_for_a_task_sent_back_to_its_preflight_by_a_requeue(self):
        # Arrange
        requeued = {**T7_PR_OPEN, "ts": "2026-10-02T11:00:00Z", "reason": "brigade wave requeue"}
        write_ledger(self.root, [WAVE_STARTED, T7_PR_OPEN, requeued])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", events=False), self.runtime)

        # Assert
        self.assertEqual(
            document["tasks"][0], {"task": "T7", "state": "pr_open", "pull_request": None, "run": None, "reason": None}
        )

    def test_should_refuse_a_wave_no_wave_started_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w17", events=False), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no wave.started names the wave tidepool_w17")


REPOSITORY = "/srv/tidepool"
WAVE_HEAD = "8885daa"
RUN = "20261018T120000Z-a1b2c3"
FORGELESS_WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-10-18T09:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "tasks": ["T7"],
}
CUT = {
    "schema_version": 1,
    "ts": "2026-10-18T08:00:00Z",
    "event": "milestone.branch_cut",
    "project": "tidepool",
    "milestone": "M4",
    "branch": "integration/tides",
    "login": None,
}
REPORTED = {
    "schema_version": 1,
    "ts": "2026-10-18T12:00:00Z",
    "event": "milestone.reported",
    "project": "tidepool",
    "milestone": "M4",
    "run": RUN,
    "login": None,
}
REPORT_DONE = {
    "schema_version": 1,
    "ts": "2026-10-18T12:05:00Z",
    "event": "order.done",
    "project": "tidepool",
    "kind": "study",
    "order": None,
    "run": RUN,
}
OTHER_REPORTED = {**REPORTED, "project": "elsewhere"}
MACHINE_OUTPUTS = {
    ("git", "rev-parse", "--verify"): f"{WAVE_HEAD}\n",
    ("git", "worktree", "list"): "",
}
FORGE_MACHINE_OUTPUTS = {**MACHINE_OUTPUTS, ("git", "ls-remote"): "", ("git", "fetch"): ""}
FORGE = object()


def resolve_forge(kind: str, name: str, **places):
    return FORGE


CORPUS = {
    "PROJECT": {"tidepool": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", "none"))},
    "TASK": {"T7": (("TITLE", "Tide table"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"))},
    "POLICY": {},
}
CORPUS_WITH_A_TASK_OF_ANOTHER_MILESTONE = {
    **CORPUS,
    "TASK": {
        "T7": (("TITLE", "Tide table"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4")),
        "T9": (("TITLE", "Tide almanac"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M5")),
    },
}


CORPUS_OF_NO_AUTO_MERGE = {
    **CORPUS,
    "POLICY": {"tidepool_policy": (("PROJECT", "@PROJECT.tidepool"), ("AUTO_MERGE", "none"))},
}
CORPUS_ON_A_FORGE = {
    **CORPUS_OF_NO_AUTO_MERGE,
    "PROJECT": {"tidepool": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", "github"))},
}
CORPUS_OF_A_TASK_OF_NO_MILESTONE = {**CORPUS, "TASK": {"T7": (("TITLE", "Tide table"), ("TYPE", "feat"))}}
CORPUS_OF_A_TASK_OF_NO_MILESTONE_UNDER_NO_AUTO_MERGE = {
    **CORPUS_OF_NO_AUTO_MERGE,
    "TASK": CORPUS_OF_A_TASK_OF_NO_MILESTONE["TASK"],
}
CORPUS_OF_A_TASK_OF_NO_MILESTONE_ON_A_FORGE = {
    **CORPUS_ON_A_FORGE,
    "TASK": CORPUS_OF_A_TASK_OF_NO_MILESTONE["TASK"],
}
TASK_VERIFIED = {
    "schema_version": 1,
    "ts": "2026-10-18T11:00:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "verified",
}
TASK_MERGED = {**TASK_VERIFIED, "state": "merged"}
BRANCH_CUT_UNDER_THE_FIRST_TITLE = {
    "schema_version": 1,
    "ts": "2026-10-18T09:30:00Z",
    "event": "task.branch_cut",
    "project": "tidepool",
    "task": "T7",
    "branch": "feature/T7-tidal-chart",
}


class WaveShowOfAProjectWithoutAForgeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(CORPUS, MACHINE_OUTPUTS),
            read_live_blockers=read_no_live_blocker,
        )

    def _show(self, events: list[dict]) -> dict:
        write_ledger(self.root, events)
        return COMMAND.run(Namespace(wave="tidepool_w16", events=False, json=True), self.runtime)

    def test_should_print_the_command_merging_the_milestone_of_the_wave_once_its_report_is_committed(self):
        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, REPORTED, REPORT_DONE])

        # Assert
        self.assertEqual(document["merge_command"], "git -C /srv/tidepool merge integration/tides")
        self.assertIn(
            "to merge: git -C /srv/tidepool merge integration/tides", COMMAND.render_text(document).splitlines()
        )

    def test_should_read_the_milestone_from_the_tasks_of_the_wave_alone(self):
        # Arrange
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(CORPUS_WITH_A_TASK_OF_ANOTHER_MILESTONE, MACHINE_OUTPUTS),
            read_live_blockers=read_no_live_blocker,
        )

        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, REPORTED, REPORT_DONE])

        # Assert
        self.assertEqual(document["merge_command"], "git -C /srv/tidepool merge integration/tides")

    def test_should_print_the_command_merging_a_verified_task_into_its_milestone_under_no_auto_merge(self):
        # Arrange
        self.runtime = create_test_runtime(
            create_test_paths(self.root), run_process=create_machine_double(CORPUS_OF_NO_AUTO_MERGE, MACHINE_OUTPUTS)
        )

        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, TASK_VERIFIED])

        # Assert
        worktree = "/srv/tidepool/.brigade/worktrees/integration-tides"
        command = f"git -C {worktree} merge feature/T7-tide-table"
        self.assertEqual(document["task_merge_commands"], [command])
        self.assertIn(f"to merge: {command}", COMMAND.render_text(document).splitlines())

    def test_should_name_the_branch_a_retitled_task_was_first_cut_on_in_its_merge_command(self):
        # Arrange
        self.runtime = create_test_runtime(
            create_test_paths(self.root), run_process=create_machine_double(CORPUS_OF_NO_AUTO_MERGE, MACHINE_OUTPUTS)
        )

        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, BRANCH_CUT_UNDER_THE_FIRST_TITLE, TASK_VERIFIED])

        # Assert
        self.assertEqual(
            document["task_merge_commands"],
            ["git -C /srv/tidepool/.brigade/worktrees/integration-tides merge feature/T7-tidal-chart"],
        )

    def test_should_name_a_task_merge_only_for_a_verified_task_under_no_auto_merge(self):
        for case, corpus, state in [
            ("under the policy that merges", CORPUS, TASK_VERIFIED),
            ("once merged", CORPUS_OF_NO_AUTO_MERGE, TASK_MERGED),
            ("on a forge", CORPUS_ON_A_FORGE, TASK_VERIFIED),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.runtime = create_test_runtime(
                    create_test_paths(self.root),
                    run_process=create_machine_double(corpus, FORGE_MACHINE_OUTPUTS),
                    resolve_plugin=resolve_forge,
                )

                # Act
                document = self._show([CUT, FORGELESS_WAVE_STARTED, state])

                # Assert
                self.assertEqual(document["task_merge_commands"], [])

    def test_should_print_the_command_merging_a_verified_task_of_no_milestone_at_the_clone(self):
        for case, corpus in [
            ("under the policy that merges", CORPUS_OF_A_TASK_OF_NO_MILESTONE),
            ("under no auto merge", CORPUS_OF_A_TASK_OF_NO_MILESTONE_UNDER_NO_AUTO_MERGE),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.runtime = create_test_runtime(
                    create_test_paths(self.root), run_process=create_machine_double(corpus, MACHINE_OUTPUTS)
                )

                # Act
                document = self._show([FORGELESS_WAVE_STARTED, TASK_VERIFIED])

                # Assert
                command = "git -C /srv/tidepool merge feature/T7-tide-table"
                self.assertEqual(document["task_merge_commands"], [command])
                self.assertIn(f"to merge: {command}", COMMAND.render_text(document).splitlines())

    def test_should_name_no_task_merge_for_a_task_of_no_milestone_on_a_forge(self):
        # Arrange
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(CORPUS_OF_A_TASK_OF_NO_MILESTONE_ON_A_FORGE, FORGE_MACHINE_OUTPUTS),
            resolve_plugin=resolve_forge,
        )

        # Act
        document = self._show([FORGELESS_WAVE_STARTED, TASK_VERIFIED])

        # Assert
        self.assertEqual(document["task_merge_commands"], [])

    def test_should_name_the_milestone_the_tasks_of_the_wave_name(self):
        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED])

        # Assert
        self.assertEqual(document["milestone"], "M4")

    def test_should_name_no_milestone_for_a_wave_of_tasks_naming_none(self):
        # Arrange
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(CORPUS_OF_A_TASK_OF_NO_MILESTONE, MACHINE_OUTPUTS),
            read_live_blockers=read_no_live_blocker,
        )

        # Act
        document = self._show([FORGELESS_WAVE_STARTED])

        # Assert
        self.assertIsNone(document["milestone"])

    def test_should_name_the_report_of_the_milestone_of_the_wave_once_reported(self):
        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, REPORTED, REPORT_DONE])

        # Assert
        self.assertEqual(document["milestone_report"], "tidepool_M4")

    def test_should_name_no_report_of_a_milestone_whose_report_is_not_committed(self):
        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, REPORTED])

        # Assert
        self.assertIsNone(document["milestone_report"])

    def test_should_name_no_report_of_a_milestone_reported_for_another_project_or_milestone(self):
        for case, reported in [
            ("another project", OTHER_REPORTED),
            ("another milestone", {**REPORTED, "milestone": "M5"}),
        ]:
            with self.subTest(case=case):
                # Act
                document = self._show([CUT, FORGELESS_WAVE_STARTED, reported, REPORT_DONE])

                # Assert
                self.assertIsNone(document["milestone_report"])

    def test_should_print_no_command_before_the_report_of_the_milestone(self):
        # Act
        document = self._show([CUT, FORGELESS_WAVE_STARTED, OTHER_REPORTED])

        # Assert
        self.assertIsNone(document["merge_command"])
        self.assertNotIn("to merge", COMMAND.render_text(document))


MILESTONE_LOOKUP = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/tides")
MILESTONE_FETCH = ("git", "fetch", "--quiet", "origin", "integration/tides")


class WaveShowOfAProjectOnAForgeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.argvs = []
        run_machine = create_machine_double(CORPUS_ON_A_FORGE, MACHINE_OUTPUTS)

        def run_process(request):
            self.argvs.append(request.argv)
            return run_machine(request)

        self.runtime = create_test_runtime(
            create_test_paths(self.root), run_process=run_process, read_live_blockers=read_no_live_blocker
        )

    def _show_as_json(self) -> dict:
        write_ledger(self.root, [CUT, FORGELESS_WAVE_STARTED])
        return COMMAND.run(Namespace(wave="tidepool_w16", events=False, json=True), self.runtime)

    def test_should_name_the_milestone_of_the_wave_its_tasks_name_on_the_forge(self):
        # Act
        document = self._show_as_json()

        # Assert
        self.assertEqual(document["milestone"], "M4")

    def test_should_look_up_no_branch_of_the_forge_to_name_the_milestone(self):
        # Act
        self._show_as_json()

        # Assert
        self.assertNotIn(MILESTONE_LOOKUP, self.argvs)

    def test_should_fetch_no_branch_of_the_forge_to_name_the_milestone(self):
        # Act
        self._show_as_json()

        # Assert
        self.assertNotIn(MILESTONE_FETCH, self.argvs)


QUEUED_WAVE_STARTED = {**FORGELESS_WAVE_STARTED, "tasks": ["T7", "T8"]}
T8_WAITING = {
    "schema_version": 1,
    "ts": "2026-10-18T09:10:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T8",
    "state": "queued",
}
T8_PARKED_ON_ITS_RUN = {
    "schema_version": 1,
    "ts": "2026-10-18T09:20:00Z",
    "event": "task.parked",
    "wave": "tidepool_w16",
    "task": "T8",
    "reason": "run r1 blocked: Which tide?",
    "blockers": [],
}
T8_WAITING_AGAIN = {**T8_WAITING, "ts": "2026-10-18T09:30:00Z"}
QUEUED_WAVE_BLOCKED = {
    "schema_version": 1,
    "ts": "2026-10-18T09:40:00Z",
    "event": "wave.blocked",
    "wave": "tidepool_w16",
    "reason": "quota",
    "resume_at": "2026-10-18T13:00:00Z",
}
TIDE_TABLE = (("TITLE", "Tide table"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"))
TIDE_CLOCK = (("TITLE", "Tide clock"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"))
TIDE_ALMANAC = (("TITLE", "Tide almanac"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"))
T7_RUNNING_IN_THE_ROUND = {**T8_WAITING, "ts": "2026-10-18T09:01:00Z", "task": "T7", "state": "running"}
CORPUS_OF_A_TASK_AFTER_ANOTHER = {
    **CORPUS,
    "TASK": {"T7": TIDE_TABLE, "T8": (*TIDE_CLOCK, ("AFTER", "@TASK.T7"))},
}
CORPUS_OF_TWO_INDEPENDENT_TASKS = {**CORPUS, "TASK": {"T7": TIDE_TABLE, "T8": TIDE_CLOCK}}
CORPUS_OF_ONE_BUILD_SLOT = {
    **CORPUS_OF_TWO_INDEPENDENT_TASKS,
    "PROJECT": {"tidepool": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", "none"), ("SLOTS", "1"))},
}
CORPUS_OF_TWO_BUILD_SLOTS = {
    **CORPUS_OF_TWO_INDEPENDENT_TASKS,
    "PROJECT": {"tidepool": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", "none"), ("SLOTS", "2"))},
}
CORPUS_OF_AN_EARLIER_TASK = {
    **CORPUS_OF_ONE_BUILD_SLOT,
    "TASK": {**CORPUS_OF_ONE_BUILD_SLOT["TASK"], "T5": TIDE_ALMANAC},
}
EARLIER_WAVE_STARTED = {**FORGELESS_WAVE_STARTED, "ts": "2026-10-18T08:30:00Z", "wave": "tidepool_w15", "tasks": ["T5"]}
T5_RUNNING = {**T8_WAITING, "ts": "2026-10-18T08:35:00Z", "wave": "tidepool_w15", "task": "T5", "state": "running"}
T5_STOPPED_BY_LOGIN = {
    **create_run_result("20261018T083500Z-a1b2c3", "error", "2026-10-18T08:50:00Z"),
    "error_class": "authentication",
    "wave": "tidepool_w15",
    "task": "T5",
}
BUILD_RUN_AFTER_THE_REBASE = "20261018T090000Z-d4e5f6"
NOTHING_IMPLEMENTED = {
    ("awawa", "status", "TASK", "--where", "STATUS==implemented"): '{"entities": []}',
}
LIVE_BUILD_RUN = "20261018T091500Z-e1f2a3"
FINISHED_BUILD_RUN = "20261018T080000Z-b4c5d6"
LIVE_RUN_ELSEWHERE = "20261018T091600Z-f7a8b9"
LIVE_REVIEW_RUN = "20261018T091700Z-c1d2e3"
TIDEPOOL = {"project": "tidepool"}
ELSEWHERE = {"project": "elsewhere"}
REVIEW = {"project": "tidepool", "slot": "review"}
FINISHED = create_run_result(FINISHED_BUILD_RUN, "done", "2026-10-18T08:30:00Z")


def read_an_undecided_question(run_process, root: Path, task: str) -> tuple[str, ...]:
    return {"T8": ("OPEN_QUESTION.Undecided",)}.get(task, ())


class WaveShowOfAQueuedTaskTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)

    def _show(
        self,
        corpus: dict,
        events: list[dict],
        implemented: dict = NOTHING_IMPLEMENTED,
        read_live_blockers=read_no_live_blocker,
    ) -> dict:
        write_ledger(self.root, events)
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **implemented}),
            read_live_blockers=read_live_blockers,
        )
        return COMMAND.run(Namespace(wave="tidepool_w16", events=False), runtime)

    def test_should_name_the_earlier_task_a_queued_task_waits_after(self):
        # Act
        document = self._show(CORPUS_OF_A_TASK_AFTER_ANOTHER, [QUEUED_WAVE_STARTED, T8_WAITING])

        # Assert
        self.assertEqual(
            document["tasks"][1],
            {"task": "T8", "state": "queued", "pull_request": None, "run": None, "reason": "after T7"},
        )

    def test_should_name_the_earlier_task_a_task_never_launched_waits_after(self):
        # Act
        document = self._show(CORPUS_OF_A_TASK_AFTER_ANOTHER, [QUEUED_WAVE_STARTED])

        # Assert
        self.assertEqual(
            document["tasks"][1],
            {"task": "T8", "state": None, "pull_request": None, "run": None, "reason": "after T7"},
        )

    def test_should_name_no_cause_for_a_task_after_an_earlier_task_implemented_at_the_tree_of_its_wave(self):
        # Arrange
        t7_implemented = {
            (
                "awawa",
                "status",
                "TASK",
                "--where",
                "STATUS==implemented",
            ): '{"entities": [{"type": "TASK", "name": "T7"}]}',
        }

        # Act
        document = self._show(CORPUS_OF_A_TASK_AFTER_ANOTHER, [QUEUED_WAVE_STARTED, T8_WAITING], t7_implemented)

        # Assert
        self.assertEqual(
            document["tasks"][1], {"task": "T8", "state": "queued", "pull_request": None, "run": None, "reason": None}
        )

    def test_should_name_the_live_blocker_holding_a_queued_task(self):
        # Act
        document = self._show(
            CORPUS_OF_TWO_INDEPENDENT_TASKS,
            [QUEUED_WAVE_STARTED, T8_WAITING],
            read_live_blockers=read_an_undecided_question,
        )

        # Assert
        self.assertEqual(document["tasks"][1]["reason"], "blocked by OPEN_QUESTION.Undecided")

    def test_should_name_the_halt_of_its_wave_as_the_cause_a_queued_task_waits(self):
        # Act
        document = self._show(CORPUS_OF_TWO_INDEPENDENT_TASKS, [QUEUED_WAVE_STARTED, T8_WAITING, QUEUED_WAVE_BLOCKED])

        # Assert
        self.assertEqual(
            document["tasks"][1]["reason"],
            "wave tidepool_w16 blocked until 2026-10-18T13:00:00Z: quota",
        )

    def test_should_name_the_build_slots_all_used_as_the_cause_a_queued_task_waits(self):
        # Arrange
        state_root = self.root / "state"
        record_run_pid(
            write_run(state_root, create_run_record(LIVE_BUILD_RUN, "tidepool_w16", "T7") | TIDEPOOL, None), os.getpid()
        )
        write_run(state_root, create_run_record(FINISHED_BUILD_RUN, None, None) | TIDEPOOL, FINISHED)
        record_run_pid(
            write_run(state_root, create_run_record(LIVE_RUN_ELSEWHERE, None, None) | ELSEWHERE, None), os.getpid()
        )
        record_run_pid(
            write_run(state_root, create_run_record(LIVE_REVIEW_RUN, None, None) | REVIEW, None), os.getpid()
        )

        # Act
        document = self._show(CORPUS_OF_ONE_BUILD_SLOT, [QUEUED_WAVE_STARTED, T8_WAITING])

        # Assert
        self.assertEqual(document["tasks"][1]["reason"], "no free build slot: 1 used of SLOTS 1")

    def test_should_name_the_build_slot_an_earlier_task_takes_in_the_round_as_the_cause_a_queued_task_waits(self):
        # Act
        document = self._show(CORPUS_OF_ONE_BUILD_SLOT, [QUEUED_WAVE_STARTED, T8_WAITING])

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {"task": "T7", "state": None, "pull_request": None, "run": None, "reason": None},
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_name_the_build_slot_a_task_of_an_earlier_open_wave_takes_as_the_cause_a_queued_task_waits(self):
        # Act
        document = self._show(CORPUS_OF_AN_EARLIER_TASK, [EARLIER_WAVE_STARTED, QUEUED_WAVE_STARTED, T8_WAITING])

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {
                    "task": "T7",
                    "state": None,
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_take_no_build_slot_for_a_task_of_an_open_wave_of_another_project(self):
        # Arrange
        wave_elsewhere = {
            **FORGELESS_WAVE_STARTED,
            "ts": "2026-10-18T08:30:00Z",
            "wave": "elsewhere_w3",
            "project": "elsewhere",
            "tasks": ["E1"],
        }

        # Act
        document = self._show(CORPUS_OF_ONE_BUILD_SLOT, [wave_elsewhere, QUEUED_WAVE_STARTED, T8_WAITING])

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {"task": "T7", "state": None, "pull_request": None, "run": None, "reason": None},
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_name_the_build_slot_a_running_task_relaunched_after_its_rebase_takes_as_the_cause(self):
        # Arrange
        rebase = {"slot": "rebase"}
        rebase_finished = {
            **create_run_result(FINISHED_BUILD_RUN, "done", "2026-10-18T09:05:00Z"),
            **rebase,
            "wave": "tidepool_w16",
            "task": "T7",
        }
        write_run(
            self.root / "state",
            create_run_record(FINISHED_BUILD_RUN, "tidepool_w16", "T7") | TIDEPOOL | rebase,
            rebase_finished,
        )

        # Act
        document = self._show(
            CORPUS_OF_ONE_BUILD_SLOT, [QUEUED_WAVE_STARTED, T7_RUNNING_IN_THE_ROUND, rebase_finished, T8_WAITING]
        )

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {"task": "T7", "state": "running", "pull_request": None, "run": FINISHED_BUILD_RUN, "reason": None},
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_name_the_build_slot_a_task_of_an_earlier_wave_relaunched_after_a_lost_login_takes(self):
        # Act
        document = self._show(
            CORPUS_OF_AN_EARLIER_TASK,
            [EARLIER_WAVE_STARTED, T5_RUNNING, T5_STOPPED_BY_LOGIN, QUEUED_WAVE_STARTED, T8_WAITING],
        )

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {
                    "task": "T7",
                    "state": None,
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_take_no_build_slot_for_a_task_of_an_earlier_closed_wave(self):
        # Arrange
        earlier_wave_closed = {
            "schema_version": 1,
            "ts": "2026-10-18T08:40:00Z",
            "event": "wave.closed",
            "wave": "tidepool_w15",
        }

        # Act
        document = self._show(
            CORPUS_OF_AN_EARLIER_TASK, [EARLIER_WAVE_STARTED, earlier_wave_closed, QUEUED_WAVE_STARTED, T8_WAITING]
        )

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {"task": "T7", "state": None, "pull_request": None, "run": None, "reason": None},
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_take_no_build_slot_for_a_running_task_of_an_earlier_open_wave(self):
        # Act
        document = self._show(
            CORPUS_OF_AN_EARLIER_TASK, [EARLIER_WAVE_STARTED, T5_RUNNING, QUEUED_WAVE_STARTED, T8_WAITING]
        )

        # Assert
        self.assertEqual(
            document["tasks"],
            [
                {"task": "T7", "state": None, "pull_request": None, "run": None, "reason": None},
                {
                    "task": "T8",
                    "state": "queued",
                    "pull_request": None,
                    "run": None,
                    "reason": "no free build slot: 1 used of SLOTS 1",
                },
            ],
        )

    def test_should_take_no_second_build_slot_for_a_task_stopped_by_a_lost_login_already_running_live(self):
        # Arrange
        t7_stopped_by_login = {**T5_STOPPED_BY_LOGIN, "wave": "tidepool_w16", "task": "T7"}
        record_run_pid(
            write_run(self.root / "state", create_run_record(LIVE_BUILD_RUN, "tidepool_w16", "T7") | TIDEPOOL, None),
            os.getpid(),
        )

        # Act
        document = self._show(
            CORPUS_OF_TWO_BUILD_SLOTS,
            [QUEUED_WAVE_STARTED, T7_RUNNING_IN_THE_ROUND, t7_stopped_by_login, T8_WAITING],
        )

        # Assert
        self.assertEqual(
            document["tasks"][1], {"task": "T8", "state": "queued", "pull_request": None, "run": None, "reason": None}
        )

    def test_should_take_no_build_slot_for_a_running_task_whose_last_run_follows_its_rebase(self):
        # Arrange
        rebase = {"slot": "rebase"}
        rebase_finished = {
            **create_run_result(FINISHED_BUILD_RUN, "done", "2026-10-18T08:30:00Z"),
            **rebase,
            "wave": "tidepool_w16",
            "task": "T7",
        }
        build_finished = {
            **create_run_result(BUILD_RUN_AFTER_THE_REBASE, "done", "2026-10-18T09:05:00Z"),
            "wave": "tidepool_w16",
            "task": "T7",
        }
        state_root = self.root / "state"
        write_run(
            state_root, create_run_record(FINISHED_BUILD_RUN, "tidepool_w16", "T7") | TIDEPOOL | rebase, rebase_finished
        )
        write_run(
            state_root, create_run_record(BUILD_RUN_AFTER_THE_REBASE, "tidepool_w16", "T7") | TIDEPOOL, build_finished
        )

        # Act
        document = self._show(
            CORPUS_OF_ONE_BUILD_SLOT,
            [QUEUED_WAVE_STARTED, T7_RUNNING_IN_THE_ROUND, rebase_finished, build_finished, T8_WAITING],
        )

        # Assert
        self.assertEqual(
            document["tasks"][1], {"task": "T8", "state": "queued", "pull_request": None, "run": None, "reason": None}
        )

    def test_should_show_no_reason_for_a_task_queued_again_after_its_park(self):
        # Act
        document = self._show(
            CORPUS_OF_TWO_INDEPENDENT_TASKS, [QUEUED_WAVE_STARTED, T8_WAITING, T8_PARKED_ON_ITS_RUN, T8_WAITING_AGAIN]
        )

        # Assert
        self.assertEqual(
            document["tasks"][1], {"task": "T8", "state": "queued", "pull_request": None, "run": None, "reason": None}
        )
