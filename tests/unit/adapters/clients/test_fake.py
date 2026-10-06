import unittest

from brigade.adapters.clients.fake import answer
from brigade.errors import BrigadeError

LAUNCH_REQUEST = {
    "schema_version": 1,
    "worktree": "/srv/worktrees/b42",
    "brief": "Deliver the task B42.",
    "role": {
        "name": "bastien",
        "package": "AGENT bastien",
        "capabilities": ["read", "shell"],
        "reasoning": "standard",
        "budget": 75,
    },
    "reasoning_table": {},
    "settings": {"recordings": "/srv/recordings"},
    "home": "/home/ada",
}


class FakeProbe(unittest.TestCase):
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


class FakeLaunch(unittest.TestCase):
    def test_should_print_the_recording_named_after_the_role(self):
        # Act
        launch = answer("launch-argv", LAUNCH_REQUEST)

        # Assert
        self.assertEqual(
            launch,
            {
                "schema_version": 1,
                "argv": ["cat", "--", "/srv/recordings/bastien.json"],
                "environment": {},
                "stdin": None,
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


class FakeProbeOfDeclaredFeatures(unittest.TestCase):
    def test_should_declare_the_features_its_settings_name(self):
        # Arrange
        settings = {"features": "step_count,tool_grants"}

        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": settings, "home": "/home/ada"})

        # Assert
        self.assertEqual(probe["features"], ["step_count", "tool_grants"])


class FakeLaunchOfASlowClientWritingProgress(unittest.TestCase):
    def test_should_wait_append_the_progress_line_then_print_the_recording(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "settings": {"recordings": "/srv/recordings", "delay": "5", "progress": "step 1 done"}}

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
                    'sleep "$1"; if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi; cat -- "$3"',
                    "fake",
                    "5",
                    "step 1 done",
                    "/srv/recordings/bastien.json",
                ],
                "environment": {},
                "stdin": None,
            },
        )


class FakeResult(unittest.TestCase):
    def test_should_answer_the_recorded_result_document_as_it_is(self):
        # Arrange
        recording = (
            '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": null, "session_id": "fake-session",'
            ' "duration_ms": 61000, "error_class": null, "reset": null, "message": null}'
        )

        # Act
        result = answer(
            "parse-result",
            {"schema_version": 1, "exit_code": 0, "stdout": recording, "stderr": "", "reasoning_table": {}, "settings": {}, "home": "/home/ada"},
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
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )


class FakeUnsupportedOperations(unittest.TestCase):
    def test_should_refuse_the_operations_it_does_not_replay(self):
        rows = ["resume-argv", "transcripts"]
        for operation in rows:
            with self.subTest(operation=operation):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    answer(operation, LAUNCH_REQUEST)

                # Assert
                self.assertEqual(str(raised.exception), f"the fake client adapter does not answer {operation}")
