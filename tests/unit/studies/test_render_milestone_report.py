import unittest

from brigade.studies.render_milestone_report import ReportEvidence, render_milestone_report

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
    {"ts": "2026-10-05T08:00:00Z", "event": "wave.started", "wave": "oak_w3", "project": "oak", "tasks": ["B22"]},
    {"ts": "2026-10-05T08:05:00Z", "event": "task.state", "wave": "oak_w3", "task": "B22", "state": "running"},
    {"ts": "2026-10-05T09:00:00Z", "event": "run.finished", "wave": "oak_w3", "task": "B22", "outcome": "done"},
    {"ts": "2026-10-05T09:30:00Z", "event": "task.state", "wave": "oak_w3", "task": "B22", "state": "merged"},
]
PULL_REQUESTS = [
    {"number": 178, "head": "feature/B17-merge-a-verified-task", "state": "merged", "task": "B17"},
    {"number": 181, "head": "fix/B22-report-across-waves", "state": "merged", "task": "B22"},
    {"number": 12, "head": "docs/readme", "state": "merged", "task": None},
]
TASKS = [
    {
        "type": "TASK",
        "name": "B17",
        "fields": [
            {"name": "STATUS", "atoms": ["implemented"]},
            {"name": "MILESTONE", "atoms": ["@MILESTONE.M3"]},
            {"name": "SPEC", "atoms": ['"the tick merges "', r'"a verified task, grep a\.b"']},
        ],
    },
    {
        "type": "TASK",
        "name": "B21",
        "fields": [
            {"name": "STATUS", "atoms": ["todo"]},
            {"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]},
            {"name": "SPEC", "atoms": ['"the report names the wave"']},
            {"name": "AFTER", "atoms": ["@TASK.B17"]},
            {"name": "AFTER", "atoms": ["@TASK.B3"]},
        ],
    },
    {
        "type": "TASK",
        "name": "B22",
        "fields": [
            {"name": "STATUS", "atoms": ["implemented"]},
            {"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]},
            {"name": "SPEC", "atoms": ['"the report spans the waves"']},
            {"name": "AFTER", "atoms": ["@TASK.B21"]},
        ],
    },
]
CHANGES = [
    {"path": "corpus/tasks.awawa", "insertions": 3, "deletions": 1},
    {"path": "brigade/tick/plan.py", "insertions": 10, "deletions": 0},
]
NO_REQUEST_FROM_A_PATTERN = []


NO_EVENT = []
NO_PULL_REQUEST = []
NO_TASK = []
NO_CHANGE = []


class RenderMilestoneReportTest(unittest.TestCase):
    def test_should_name_the_report_of_a_task_after_its_task(self):
        # Arrange
        evidence = ReportEvidence(
            subject_field="TASK",
            subject="B46",
            project="oak",
            corpus_folder="corpus",
            events=NO_EVENT,
            pull_requests=NO_PULL_REQUEST,
            tasks=NO_TASK,
            changes=NO_CHANGE,
            origins=NO_REQUEST_FROM_A_PATTERN,
        )

        # Act
        report = render_milestone_report(evidence)

        # Assert
        self.assertEqual(
            report,
            "REPORT oak_B46\n"
            '\tTASK "B46"\n'
            '\tPROJECT "oak"\n'
            '\tSTATISTIC "tasks 0"\n'
            '\tSTATISTIC "merged 0"\n'
            '\tSTATISTIC "parked 0"\n'
            '\tSTATISTIC "runs 0"\n'
            '\tSTATISTIC "files 0"\n'
            '\tSTATISTIC "insertions 0"\n'
            '\tSTATISTIC "deletions 0"\n',
        )

    def test_should_fill_the_report_of_the_milestone_with_what_the_collectors_of_its_waves_gave(self):
        # Arrange
        evidence = ReportEvidence(
            subject_field="MILESTONE",
            subject="M4",
            project="oak",
            corpus_folder="corpus",
            events=EVENTS,
            pull_requests=PULL_REQUESTS,
            tasks=TASKS,
            changes=CHANGES,
            origins=NO_REQUEST_FROM_A_PATTERN,
        )

        # Act
        report = render_milestone_report(evidence)

        # Assert
        self.assertEqual(
            report,
            "REPORT oak_M4\n"
            '\tMILESTONE "M4"\n'
            '\tPROJECT "oak"\n'
            '\tTASK_ROW "B17 merged #178"\n'
            '\tTASK_ROW "B21 parked"\n'
            '\tTASK_ROW "B22 merged #181"\n'
            '\tSTATISTIC "tasks 3"\n'
            '\tSTATISTIC "merged 2"\n'
            '\tSTATISTIC "parked 1"\n'
            '\tSTATISTIC "runs 4"\n'
            '\tSTATISTIC "files 2"\n'
            '\tSTATISTIC "insertions 13"\n'
            '\tSTATISTIC "deletions 1"\n'
            '\tGRAPH "B21 after B17"\n'
            '\tGRAPH "B22 after B21"\n'
            '\tMANUAL_TEST "B17: the tick merges a verified task, grep a\\\\.b"\n'
            '\tMANUAL_TEST "B22: the report spans the waves"\n'
            '\tINSTRUCTIONS_CHANGE "corpus/tasks.awawa +3 -1"\n'
            '\tPARKED_QUESTION "B21 blocked by @OPEN_QUESTION.Q4"\n',
        )

    def test_should_list_each_task_whose_request_comes_from_a_pattern_with_its_constraint_and_its_reason(self):
        # Arrange
        evidence = ReportEvidence(
            subject_field="MILESTONE",
            subject="M4",
            project="oak",
            corpus_folder="corpus",
            events=EVENTS,
            pull_requests=PULL_REQUESTS,
            tasks=TASKS,
            changes=CHANGES,
            origins=[
                {
                    "milestone": "M3",
                    "pattern": "CartTimeouts",
                    "constraint": "CartTimeouts",
                    "reason": "the cart tests fail on a timeout",
                },
                {"milestone": "M4", "pattern": "SlowCheckout", "constraint": None, "reason": "the checkout is slow"},
                {"milestone": "M9", "pattern": "Elsewhere", "constraint": None, "reason": "another wave"},
            ],
        )

        # Act
        report = render_milestone_report(evidence)

        # Assert
        self.assertEqual(
            report,
            "REPORT oak_M4\n"
            '\tMILESTONE "M4"\n'
            '\tPROJECT "oak"\n'
            '\tTASK_ROW "B17 merged #178"\n'
            '\tTASK_ROW "B21 parked"\n'
            '\tTASK_ROW "B22 merged #181"\n'
            '\tSTATISTIC "tasks 3"\n'
            '\tSTATISTIC "merged 2"\n'
            '\tSTATISTIC "parked 1"\n'
            '\tSTATISTIC "runs 4"\n'
            '\tSTATISTIC "files 2"\n'
            '\tSTATISTIC "insertions 13"\n'
            '\tSTATISTIC "deletions 1"\n'
            '\tGRAPH "B21 after B17"\n'
            '\tGRAPH "B22 after B21"\n'
            '\tMANUAL_TEST "B17: the tick merges a verified task, grep a\\\\.b"\n'
            '\tMANUAL_TEST "B22: the report spans the waves"\n'
            '\tINSTRUCTIONS_CHANGE "corpus/tasks.awawa +3 -1"\n'
            '\tPARKED_QUESTION "B21 blocked by @OPEN_QUESTION.Q4"\n'
            '\tPATTERN_TASK "B17 from @PATTERN.CartTimeouts with @CONSTRAINT.CartTimeouts: the cart tests fail on a timeout"\n'
            '\tPATTERN_TASK "B21 from @PATTERN.SlowCheckout: the checkout is slow"\n'
            '\tPATTERN_TASK "B22 from @PATTERN.SlowCheckout: the checkout is slow"\n',
        )

    def test_should_list_no_task_without_milestone_from_a_request_still_planning(self):
        # Arrange
        evidence = ReportEvidence(
            subject_field="MILESTONE",
            subject="M4",
            project="oak",
            corpus_folder="corpus",
            events=EVENTS,
            pull_requests=PULL_REQUESTS,
            tasks=[{"type": "TASK", "name": "B17", "fields": []}],
            changes=CHANGES,
            origins=[
                {
                    "milestone": None,
                    "pattern": "CartTimeouts",
                    "constraint": None,
                    "reason": "the cart tests fail on a timeout",
                },
            ],
        )

        # Act
        report = render_milestone_report(evidence)

        # Assert
        self.assertEqual(
            report,
            "REPORT oak_M4\n"
            '\tMILESTONE "M4"\n'
            '\tPROJECT "oak"\n'
            '\tTASK_ROW "B17 merged #178"\n'
            '\tTASK_ROW "B21 parked"\n'
            '\tTASK_ROW "B22 merged #181"\n'
            '\tSTATISTIC "tasks 3"\n'
            '\tSTATISTIC "merged 2"\n'
            '\tSTATISTIC "parked 1"\n'
            '\tSTATISTIC "runs 4"\n'
            '\tSTATISTIC "files 2"\n'
            '\tSTATISTIC "insertions 13"\n'
            '\tSTATISTIC "deletions 1"\n'
            '\tINSTRUCTIONS_CHANGE "corpus/tasks.awawa +3 -1"\n'
            '\tPARKED_QUESTION "B21 blocked by @OPEN_QUESTION.Q4"\n',
        )
