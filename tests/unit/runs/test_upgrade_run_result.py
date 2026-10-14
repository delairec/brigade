import unittest

from brigade.runs.run_record import RunRecord
from brigade.runs.upgrade_run_result import upgrade_run_result

RUN_RECORD = RunRecord(
    run="20261013T174800Z-cb856f",
    procedure="awawa-task",
    procedure_path="built-in",
    slot="build",
    role="ada",
    role_source="built-in",
    client="claude-code",
    project="brigade",
    cwd="/home/user/brigade",
    worktree="/home/user/brigade",
    capabilities=("read",),
    budget=75,
    wall_limit_s=7200.0,
    arguments={},
)
SECOND_SEGMENT = 2


class UpgradeRunResultTest(unittest.TestCase):
    def test_should_describe_the_segment_as_run_finished_without_the_figures_of_the_client(self):
        # Arrange
        result_of_schema_1 = {
            "schema_version": 1,
            "outcome": "done",
            "steps": None,
            "usage": {
                "input_tokens": 116,
                "output_tokens": 30543,
                "cache_creation_input_tokens": 104815,
                "cache_read_input_tokens": 5853165,
            },
            "session_id": "860297f0-09d1-461e-90ed-2dbd2c4bec7b",
            "duration_ms": 700183,
            "error_class": None,
            "reset": None,
            "message": None,
        }

        # Act
        document = upgrade_run_result(result_of_schema_1, RUN_RECORD, SECOND_SEGMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "run": "20261013T174800Z-cb856f",
                "segment": 2,
                "procedure": "awawa-task",
                "slot": "build",
                "role": "ada",
                "client": "claude-code",
                "project": "brigade",
                "session": "860297f0-09d1-461e-90ed-2dbd2c4bec7b",
                "main_steps": None,
                "total_steps": None,
                "duration_ms": None,
                "usage": {
                    "input_tokens": 116,
                    "output_tokens": 30543,
                    "cache_creation_input_tokens": 104815,
                    "cache_read_input_tokens": 5853165,
                },
                "outcome": "done",
                "error_class": None,
                "exit": None,
                "wave": None,
                "task": None,
                "nulls": {
                    "main_steps": "result.json of schema 1 kept the figure of the client, not the measure of brigade",
                    "total_steps": "result.json of schema 1 kept the figure of the client, not the measure of brigade",
                    "duration_ms": "result.json of schema 1 kept the figure of the client, not the measure of brigade",
                    "error_class": "result.json of schema 1 kept no reason",
                    "exit": "result.json of schema 1 kept no reason",
                    "wave": "not launched by a wave",
                    "task": "not launched by a wave",
                },
                "reset": None,
                "message": None,
            },
        )
