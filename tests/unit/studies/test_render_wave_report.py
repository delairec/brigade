import unittest

from brigade.studies.render_wave_report import WaveEvidence, render_wave_report

EVENTS = [
    {
        "ts": "2026-10-04T08:00:00Z",
        "event": "wave.started",
        "wave": "oak_w2",
        "project": "oak",
        "branch": "integration/oak_w2",
        "tasks": ["B17", "B21"],
    },
    {"ts": "2026-10-04T08:05:00Z", "event": "task.state", "wave": "oak_w2", "task": "B17", "state": "running"},
    {"ts": "2026-10-04T08:05:00Z", "event": "task.state", "wave": "oak_w2", "task": "B21", "state": "running"},
    {"ts": "2026-10-04T09:00:00Z", "event": "run.finished", "wave": "oak_w2", "task": "B17", "outcome": "done"},
    {"ts": "2026-10-04T09:10:00Z", "event": "run.finished", "wave": "oak_w2", "task": "B21", "outcome": "failed"},
    {
        "ts": "2026-10-04T09:20:00Z",
        "event": "task.parked",
        "wave": "oak_w2",
        "task": "B21",
        "reason": "a question blocks it",
        "blockers": ["@OPEN_QUESTION.Q4"],
    },
    {"ts": "2026-10-04T09:20:00Z", "event": "task.state", "wave": "oak_w2", "task": "B21", "state": "parked"},
    {"ts": "2026-10-04T10:00:00Z", "event": "run.finished", "wave": "oak_w2", "task": "B17", "outcome": "done"},
    {"ts": "2026-10-04T10:30:00Z", "event": "task.state", "wave": "oak_w2", "task": "B17", "state": "merged"},
]
PULL_REQUESTS = [
    {"number": 178, "head": "task/oak_w2/B17", "state": "merged", "task": "B17"},
    {"number": 12, "head": "docs/readme", "state": "merged", "task": None},
]
TASKS = [
    {
        "type": "TASK",
        "name": "B17",
        "fields": [
            {"name": "STATUS", "atoms": ["implemented"]},
            {"name": "SPEC", "atoms": ['"the tick merges "', r'"a verified task, grep a\.b"']},
        ],
    },
    {
        "type": "TASK",
        "name": "B21",
        "fields": [
            {"name": "STATUS", "atoms": ["todo"]},
            {"name": "SPEC", "atoms": ['"the report names the wave"']},
            {"name": "AFTER", "atoms": ["@TASK.B17"]},
            {"name": "AFTER", "atoms": ["@TASK.B3"]},
        ],
    },
]
CHANGES = [
    {"path": "corpus/tasks.awawa", "insertions": 3, "deletions": 1},
    {"path": "brigade/tick/plan.py", "insertions": 10, "deletions": 0},
]


class RenderWaveReportTest(unittest.TestCase):
    def test_should_fill_the_report_of_the_wave_with_what_the_collectors_gave(self):
        # Arrange
        evidence = WaveEvidence(
            wave="oak_w2",
            project="oak",
            corpus_folder="corpus",
            events=EVENTS,
            pull_requests=PULL_REQUESTS,
            tasks=TASKS,
            changes=CHANGES,
        )

        # Act
        report = render_wave_report(evidence)

        # Assert
        self.assertEqual(
            report,
            "REPORT oak_w2\n"
            '\tWAVE "oak_w2"\n'
            '\tPROJECT "oak"\n'
            '\tTASK_ROW "B17 merged #178"\n'
            '\tTASK_ROW "B21 parked"\n'
            '\tSTATISTIC "tasks 2"\n'
            '\tSTATISTIC "merged 1"\n'
            '\tSTATISTIC "parked 1"\n'
            '\tSTATISTIC "runs 3"\n'
            '\tSTATISTIC "files 2"\n'
            '\tSTATISTIC "insertions 13"\n'
            '\tSTATISTIC "deletions 1"\n'
            '\tGRAPH "B21 after B17"\n'
            '\tMANUAL_TEST "B17: the tick merges a verified task, grep a\\\\.b"\n'
            '\tINSTRUCTIONS_CHANGE "corpus/tasks.awawa +3 -1"\n'
            '\tPARKED_QUESTION "B21 blocked by @OPEN_QUESTION.Q4"\n',
        )
