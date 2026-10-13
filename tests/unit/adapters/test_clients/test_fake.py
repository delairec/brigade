import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.test_clients.fake import answer
from brigade.errors import BrigadeError

LAUNCH_REQUEST = {
    "schema_version": 1,
    "worktree": "/srv/worktrees/b42",
    "brief": "Deliver the task B42.",
    "progress_file": "/state/brigade/runs/r1/progress.md",
    "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
    "stop_at": None,
    "role": {
        "name": "builder",
        "package": "AGENT builder",
        "package_file": "/state/brigade/runs/r1/role.md",
        "capabilities": ["read", "shell"],
        "reasoning": "standard",
        "budget": 75,
    },
    "reasoning_table": {},
    "settings": {"recordings": "/srv/recordings"},
    "home": "/home/ada",
}


class FakeProbeTest(unittest.TestCase):
    def test_should_declare_the_operations_it_replays(self):
        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": {}, "home": "/home/ada"})

        # Assert
        self.assertEqual(
            probe,
            {
                "schema_version": 1,
                "client": "fake",
                "version_argv": None,
                "operations": ["probe", "launch", "result"],
                "features": [],
                "models": {},
            },
        )


class FakeLaunchTest(unittest.TestCase):
    def test_should_print_the_recording_named_after_the_role(self):
        # Act
        launch = answer("launch-argv", LAUNCH_REQUEST)

        # Assert
        self.assertEqual(
            launch,
            {
                "schema_version": 1,
                "argv": ["cat", "--", "/srv/recordings/builder.json"],
                "environment": {},
                "stdin": None,
                "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
            },
        )

    def test_should_refuse_a_launch_when_no_recordings_directory_is_configured(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "settings": {}}

        # Act
        with self.assertRaises(BrigadeError) as raised:
            answer("launch-argv", request)

        # Assert
        self.assertEqual(
            str(raised.exception), "the fake client adapter needs recordings in the table [clients.fake] of config.toml"
        )


class FakeLaunchOfASegmentResumedFromItsProgressTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.recordings = Path(self.root.name) / "recordings"
        self.recordings.mkdir()
        (self.recordings / "builder.json").write_text("{}")
        self.progress_file = Path(self.root.name) / "progress.md"

    def tearDown(self):
        self.root.cleanup()

    def launch(self) -> dict:
        settings = {"recordings": str(self.recordings)}
        return answer("launch-argv", {**LAUNCH_REQUEST, "progress_file": str(self.progress_file), "settings": settings})

    def test_should_print_the_resumed_recording_of_the_role_when_the_progress_file_holds_something(self):
        # Arrange
        (self.recordings / "builder.resumed.json").write_text("{}")
        self.progress_file.write_text("step 1 done\n")

        # Act
        launch = self.launch()

        # Assert
        self.assertEqual(launch["argv"], ["cat", "--", f"{self.recordings}/builder.resumed.json"])

    def test_should_print_the_recording_of_the_role_on_an_empty_progress_file(self):
        # Arrange
        (self.recordings / "builder.resumed.json").write_text("{}")
        self.progress_file.write_text("")

        # Act
        launch = self.launch()

        # Assert
        self.assertEqual(launch["argv"], ["cat", "--", f"{self.recordings}/builder.json"])

    def test_should_print_the_recording_of_the_role_when_it_has_no_resumed_recording(self):
        # Arrange
        self.progress_file.write_text("step 1 done\n")

        # Act
        launch = self.launch()

        # Assert
        self.assertEqual(launch["argv"], ["cat", "--", f"{self.recordings}/builder.json"])


class FakeLaunchOfASegmentResumedFromAnAwawaProgressTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.recordings = Path(self.root.name) / "recordings"
        self.recordings.mkdir()
        (self.recordings / "builder.json").write_text("{}")
        (self.recordings / "builder.resumed.json").write_text("{}")
        self.progress_file = Path(self.root.name) / "progress.awawa"

    def tearDown(self):
        self.root.cleanup()

    def launch(self) -> dict:
        settings = {"recordings": str(self.recordings)}
        return answer("launch-argv", {**LAUNCH_REQUEST, "progress_file": str(self.progress_file), "settings": settings})

    def test_should_print_the_recording_of_the_role_on_a_progress_holding_its_schema_alone(self):
        # Arrange
        self.progress_file.write_text('SCHEMA STEP\n\tDESC "a step the run completed"\n')

        # Act
        launch = self.launch()

        # Assert
        self.assertEqual(launch["argv"], ["cat", "--", f"{self.recordings}/builder.json"])

    def test_should_print_the_resumed_recording_of_the_role_on_a_progress_holding_a_step(self):
        # Arrange
        self.progress_file.write_text('SCHEMA STEP\n\tDESC "a step the run completed"\n\nSTEP s1\n\tDONE "read"\n')

        # Act
        launch = self.launch()

        # Assert
        self.assertEqual(launch["argv"], ["cat", "--", f"{self.recordings}/builder.resumed.json"])


class FakeProbeOfDeclaredFeaturesTest(unittest.TestCase):
    def test_should_declare_the_features_its_settings_name(self):
        # Arrange
        settings = {"features": "step_count,tool_grants"}

        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": settings, "home": "/home/ada"})

        # Assert
        self.assertEqual(probe["features"], ["step_count", "tool_grants"])


class FakeLaunchOfASlowClientWritingProgressTest(unittest.TestCase):
    def test_should_wait_append_the_progress_line_then_print_the_recording(self):
        # Arrange
        request = {
            **LAUNCH_REQUEST,
            "settings": {"recordings": "/srv/recordings", "delay": "5", "progress": "step 1 done"},
        }

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(
            launch,
            {
                "schema_version": 1,
                "argv": [
                    "sh",
                    "-c",
                    (
                        'sleep "$1"; until [ "$(date -u +%s)" -ge "$5" ]; do sleep 0.1; done;'
                        ' if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi;'
                        ' while IFS= read -r line || [ -n "$line" ]; do printf "%s\\n" "$line"; sleep "$4"; done < "$3"'
                    ),
                    "fake",
                    "5",
                    "step 1 done",
                    "/srv/recordings/builder.json",
                    "0",
                    "0",
                ],
                "environment": {},
                "stdin": None,
                "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
            },
        )


class FakeLaunchOfAClientStoppingAtItsSoftLimitTest(unittest.TestCase):
    def test_should_print_the_recording_once_the_stop_at_has_passed_when_it_declares_graceful_stop(self):
        # Arrange
        request = {
            **LAUNCH_REQUEST,
            "settings": {"recordings": "/srv/recordings", "features": "graceful_stop"},
            "stop_at": "2026-10-07T09:23:00Z",
        }

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(
            launch["argv"],
            [
                "sh",
                "-c",
                (
                    'sleep "$1"; until [ "$(date -u +%s)" -ge "$5" ]; do sleep 0.1; done;'
                    ' if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi;'
                    ' while IFS= read -r line || [ -n "$line" ]; do printf "%s\\n" "$line"; sleep "$4"; done < "$3"'
                ),
                "fake",
                "0",
                "",
                "/srv/recordings/builder.json",
                "0",
                "1791364980",
            ],
        )

    def test_should_ignore_the_stop_at_when_it_declares_no_graceful_stop(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "stop_at": "2026-10-07T09:23:00Z"}

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(launch["argv"], ["cat", "--", "/srv/recordings/builder.json"])


class FakeResultTest(unittest.TestCase):
    def test_should_answer_the_recorded_result_document_as_it_is(self):
        # Arrange
        recording = (
            '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": null, "session_id": "fake-session",'
            ' "duration_ms": 61000, "cost_usd": null, "error_class": null, "reset": null, "message": null}'
        )

        # Act
        result = answer(
            "parse-result",
            {
                "schema_version": 1,
                "exit_code": 0,
                "stdout": recording,
                "stderr": "",
                "reasoning_table": {},
                "settings": {},
                "home": "/home/ada",
            },
        )

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 12,
                "usage": None,
                "session_id": "fake-session",
                "duration_ms": 61000,
                "cost_usd": None,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_report_a_recording_that_holds_no_json_document(self):
        # Act
        result = answer(
            "parse-result",
            {
                "schema_version": 1,
                "exit_code": 1,
                "stdout": "",
                "stderr": "cat: /srv/recordings/builder.json: No such file or directory\n",
                "reasoning_table": {},
                "settings": {},
                "home": "/home/ada",
            },
        )

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "failed",
                "steps": None,
                "usage": None,
                "session_id": None,
                "duration_ms": None,
                "cost_usd": None,
                "error_class": "unreadable_output",
                "reset": None,
                "message": "cat: /srv/recordings/builder.json: No such file or directory",
            },
        )


class FakeUnsupportedOperationsTest(unittest.TestCase):
    def test_should_refuse_the_operations_it_does_not_replay(self):
        # Arrange
        rows = ["resume-argv", "transcripts", "actions"]
        for operation in rows:
            with self.subTest(operation=operation):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    answer(operation, LAUNCH_REQUEST)

                # Assert
                self.assertEqual(str(raised.exception), f"the fake client adapter does not answer {operation}")


class FakeProbeOfDeclaredOperationsTest(unittest.TestCase):
    def test_should_declare_the_operations_its_settings_name_beside_those_it_replays(self):
        # Arrange
        settings = {"operations": "actions"}

        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": settings, "home": "/home/ada"})

        # Assert
        self.assertEqual(probe["operations"], ["probe", "launch", "result", "actions"])


class FakeLaunchOfAClientWritingItsLinesAtIntervalsTest(unittest.TestCase):
    def test_should_print_each_line_of_the_recording_then_wait_the_interval(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "settings": {"recordings": "/srv/recordings", "interval": "1"}}

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(
            launch["argv"],
            [
                "sh",
                "-c",
                (
                    'sleep "$1"; until [ "$(date -u +%s)" -ge "$5" ]; do sleep 0.1; done;'
                    ' if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi;'
                    ' while IFS= read -r line || [ -n "$line" ]; do printf "%s\\n" "$line"; sleep "$4"; done < "$3"'
                ),
                "fake",
                "0",
                "",
                "/srv/recordings/builder.json",
                "1",
                "0",
            ],
        )


class FakeResultOfARecordingOfSeveralLinesTest(unittest.TestCase):
    def test_should_answer_the_result_document_of_its_last_line(self):
        # Arrange
        recording = (
            "Reading the task\n"
            '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": null, "session_id": "fake-session",'
            ' "duration_ms": 61000, "cost_usd": null, "error_class": null, "reset": null, "message": null}\n'
        )

        # Act
        result = answer(
            "parse-result",
            {
                "schema_version": 1,
                "exit_code": 0,
                "stdout": recording,
                "stderr": "",
                "reasoning_table": {},
                "settings": {},
                "home": "/home/ada",
            },
        )

        # Assert
        self.assertEqual(result["outcome"], "done")


class FakeActionsTest(unittest.TestCase):
    def test_should_read_a_text_per_line_and_the_outcome_of_a_result_document(self):
        # Arrange
        output = (
            "Reading the task\n"
            "\n"
            '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": null, "session_id": "fake-session",'
            ' "duration_ms": 61000, "cost_usd": null, "error_class": null, "reset": null, "message": null}\n'
        )

        # Act
        actions = answer(
            "actions",
            {
                "schema_version": 1,
                "output": output,
                "reasoning_table": {},
                "settings": {"operations": "actions"},
                "home": "/home/ada",
            },
        )

        # Assert
        self.assertEqual(
            actions,
            {
                "schema_version": 1,
                "actions": [{"kind": "text", "summary": "Reading the task"}, {"kind": "result", "summary": "done"}],
            },
        )


class FakeTranscriptsTest(unittest.TestCase):
    def setUp(self):
        self.recordings = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.recordings)

    def test_should_answer_the_transcripts_recorded_for_the_session(self):
        # Arrange
        recorded = {
            "schema_version": 1,
            "messages": [
                {"role": "assistant", "timestamp": None, "content": "Done.", "tool_calls": 0, "id": None, "usage": None}
            ],
            "subagents": [],
        }
        (self.recordings / "fake-session.transcripts.json").write_text(json.dumps(recorded))

        # Act
        transcripts = answer(
            "transcripts",
            {
                "schema_version": 1,
                "session_id": "fake-session",
                "worktree": "/srv/worktrees/b83",
                "reasoning_table": {},
                "settings": {"operations": "transcripts", "recordings": str(self.recordings)},
                "home": "/home/ada",
            },
        )

        # Assert
        self.assertEqual(
            transcripts,
            {
                "schema_version": 1,
                "messages": [
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": "Done.",
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    }
                ],
                "subagents": [],
            },
        )
