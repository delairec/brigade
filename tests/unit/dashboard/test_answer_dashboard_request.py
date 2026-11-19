import functools
import json
import sys
import unittest

from brigade.dashboard.answer_dashboard_request import answer_dashboard_request
from brigade.dashboard.awawa_addon_supervisor import AwawaAddonSupervisor
from brigade.dashboard.dashboard_exchange import Dashboard, DashboardResponse, IncomingRequest
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.dashboard.addon_child_double import ChildStarterDouble, PipedChildDouble, answer_with_the_message

PYTHON = sys.executable
ENTRY_POINT = "/srv/brigade/bin/brigade"
ISSUED_CREDENTIAL = "t0k3n"
ANSWER_TIMEOUT_S = 5.0


def refuse_to_start_the_addon():
    raise AssertionError("the awawa addon should not be started")


DASHBOARD = Dashboard(
    port=8470, token=ISSUED_CREDENTIAL, addon=AwawaAddonSupervisor(lambda: frozenset(), refuse_to_start_the_addon, 1.0)
)
LOOPBACK_HOST = "127.0.0.1:8470"
LOOPBACK_ORIGIN = "http://127.0.0.1:8470"
JSON = "application/json"
WAVE_LIST = (PYTHON, ENTRY_POINT, "wave", "list", "--json")
PROJECT_LIST = (PYTHON, ENTRY_POINT, "project", "list", "--json")
NO_WAVE = '{"schema_version": 1, "waves": []}\n'
WAVE_W4_LISTED = (
    '{"schema_version": 1, "waves": [{"wave": "w4", "project": "oak", "branch": "integration/w4",'
    ' "last_event": "wave.started", "tasks": 2}]}\n'
)
NO_PROJECT = '{"schema_version": 1, "projects": []}\n'
LEDGER_OVERVIEW = (PYTHON, ENTRY_POINT, "ledger", "--json")
NO_WAVE_STARTED = '{"schema_version": 1, "view": "overview", "waves_started": {}}\n'


def answer_get(target: str, runtime) -> DashboardResponse:
    return answer_dashboard_request(
        IncomingRequest(method="GET", target=target, host=LOOPBACK_HOST), DASHBOARD, runtime
    )


class AnswerDashboardRequestOfAForeignHostTest(unittest.TestCase):
    def test_should_refuse_the_request_before_any_routing(self):
        # Arrange
        rows = [
            ("a rebound name", "attacker.example:8470"),
            ("another port", "127.0.0.1:9000"),
            ("a name of the loopback", "localhost:8470"),
            ("no host", None),
        ]
        runtime = create_test_runtime()
        for case, host in rows:
            with self.subTest(case=case):
                incoming = IncomingRequest(method="GET", target="/api/waves", host=host)

                # Act
                response = answer_dashboard_request(incoming, DASHBOARD, runtime)

                # Assert
                self.assertEqual(response.status, 400)


class AnswerDashboardRequestOfAnUnguardedPostTest(unittest.TestCase):
    def test_should_refuse_the_request_before_any_routing(self):
        # Arrange
        rows = [
            ("no token", None, LOOPBACK_ORIGIN),
            ("another token", "guessed", LOOPBACK_ORIGIN),
            ("no origin", ISSUED_CREDENTIAL, None),
            ("a foreign origin", ISSUED_CREDENTIAL, "http://attacker.example"),
        ]
        runtime = create_test_runtime()
        for case, token, origin in rows:
            with self.subTest(case=case):
                incoming = IncomingRequest(
                    method="POST", target="/api/waves", host=LOOPBACK_HOST, origin=origin, token=token
                )

                # Act
                response = answer_dashboard_request(incoming, DASHBOARD, runtime)

                # Assert
                self.assertEqual(response.status, 403)


class AnswerDashboardRequestOfAGuardedPostTest(unittest.TestCase):
    def test_should_route_it_and_find_no_route_that_changes_state(self):
        # Arrange
        incoming = IncomingRequest(
            method="POST", target="/api/waves", host=LOOPBACK_HOST, origin=LOOPBACK_ORIGIN, token=ISSUED_CREDENTIAL
        )

        # Act
        response = answer_dashboard_request(incoming, DASHBOARD, create_test_runtime())

        # Assert
        self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfAnotherMethodTest(unittest.TestCase):
    def test_should_answer_not_found_and_run_nothing(self):
        # Arrange
        incoming = IncomingRequest(method="DELETE", target="/api/inbox/dismiss/FlakyTests", host=LOOPBACK_HOST)

        # Act
        response = answer_dashboard_request(incoming, DASHBOARD, create_test_runtime())

        # Assert
        self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfAnApiRouteTest(unittest.TestCase):
    def test_should_serve_the_json_of_the_command_the_route_runs(self):
        # Arrange
        rows = [
            ("/api/waves", ("wave", "list", "--json")),
            ("/api/waves/w4", ("wave", "show", "--json", "w4")),
            ("/api/inbox/disk_r2", ("inbox", "show", "--json", "disk_r2")),
            ("/api/inbox", ("inbox", "list", "--json")),
            ("/api/ledger", ("ledger", "--json")),
            ("/api/status", ("status", "--json")),
            ("/api/corpus/oak?ref=main", ("corpus", "--ref=main", "--json", "oak")),
            ("/api/corpus/oak", ("corpus", "--json", "oak")),
            ("/api/corpus/oak?ref=main&type=&field=", ("corpus", "--ref=main", "--json", "oak")),
            (
                "/api/corpus/oak?ref=main&type=TASK&field=STATUS&entity=@TASK.B30",
                ("corpus", "--ref=main", "--type=TASK", "--field=STATUS", "--entity=@TASK.B30", "--json", "oak"),
            ),
            ("/api/corpus", ("project", "list", "--json")),
            ("/api/reports", ("report", "list", "--json")),
            ("/api/reports/oak_w3", ("report", "show", "--json", "oak_w3")),
            ("/api/runs", ("run", "list", "--json")),
            ("/api/runs/20261031T135554Z-513a4f", ("run", "show", "--json", "20261031T135554Z-513a4f")),
        ]
        for target, arguments in rows:
            with self.subTest(target=target):
                runner = ScriptedProcessRunner({(PYTHON, ENTRY_POINT, *arguments): ProcessAnswer(stdout='{"a": 1}\n')})

                # Act
                response = answer_get(target, create_test_runtime(run_process=runner.run))

                # Assert
                self.assertEqual(response, DashboardResponse(status=200, content_type=JSON, body=b'{"a": 1}\n'))


class AnswerDashboardRequestOfAWaveTheLedgerDoesNotKnowTest(unittest.TestCase):
    def test_should_answer_not_found_with_the_standard_error_of_the_command(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "wave", "show"): ProcessAnswer(
                    exit_code=1, stderr="brigade wave show: no wave.started names the wave w9\n"
                ),
                WAVE_LIST: ProcessAnswer(stdout=NO_WAVE),
            }
        )

        # Act
        response = answer_get("/api/waves/w9", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)
        self.assertEqual(json.loads(response.body), {"error": "brigade wave show: no wave.started names the wave w9\n"})


class AnswerDashboardRequestOfAProjectNotRegisteredTest(unittest.TestCase):
    def test_should_answer_not_found(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "corpus"): ProcessAnswer(
                    exit_code=1, stderr="brigade corpus: @PROJECT.elm is not registered\n"
                ),
                PROJECT_LIST: ProcessAnswer(stdout=NO_PROJECT),
            }
        )

        # Act
        response = answer_get("/api/corpus/elm?ref=main", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfAKnownWaveWhoseCommandFailsTest(unittest.TestCase):
    def test_should_answer_a_server_error_with_the_standard_error_of_the_command(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "wave", "show"): ProcessAnswer(exit_code=1, stderr="the ledger is unreadable\n"),
                WAVE_LIST: ProcessAnswer(stdout=WAVE_W4_LISTED),
            }
        )

        # Act
        response = answer_get("/api/waves/w4", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(status=500, content_type=JSON, body=b'{"error": "the ledger is unreadable\\n"}'),
        )


class AnswerDashboardRequestOfAWaveWhoseListingFailsTest(unittest.TestCase):
    def test_should_answer_a_server_error(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "wave", "show"): ProcessAnswer(exit_code=1, stderr="the ledger is unreadable\n"),
                WAVE_LIST: ProcessAnswer(exit_code=1, stderr="the ledger is unreadable\n"),
            }
        )

        # Act
        response = answer_get("/api/waves/w4", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 500)


class AnswerDashboardRequestOfARouteWithoutIdWhoseCommandFailsTest(unittest.TestCase):
    def test_should_answer_a_server_error(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {(PYTHON, ENTRY_POINT, "inbox", "list"): ProcessAnswer(exit_code=1, stderr="the inbox is unreadable\n")}
        )

        # Act
        response = answer_get("/api/inbox", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 500)


class AnswerDashboardRequestOfAPathNoRouteServesTest(unittest.TestCase):
    def test_should_answer_not_found_and_run_nothing(self):
        # Arrange
        rows = [
            "/api/waves/w4/tasks",
            "/api/waves/",
            "/api/waves/--help",
            "/api/corpus/-h?ref=main",
            "/nowhere",
            "/api/runs/--help",
            "/views/nowhere",
            "/views/runs/--help",
            "/api/projects/oak/pause",
        ]
        runtime = create_test_runtime()
        for target in rows:
            with self.subTest(target=target):
                # Act
                response = answer_get(target, runtime)

                # Assert
                self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfThePageTest(unittest.TestCase):
    def test_should_write_the_token_of_the_server_into_the_page(self):
        # Act
        response = answer_get("/", create_test_runtime())

        # Assert
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "text/html; charset=utf-8")
        self.assertIn(b'<meta name="brigade-token" content="t0k3n">', response.body)

    def test_should_serve_the_script_and_the_stylesheet_of_the_page(self):
        # Arrange
        rows = [("/dashboard.js", "text/javascript; charset=utf-8"), ("/dashboard.css", "text/css; charset=utf-8")]
        runtime = create_test_runtime()
        for target, content_type in rows:
            with self.subTest(target=target):
                # Act
                response = answer_get(target, runtime)

                # Assert
                self.assertEqual(response.status, 200)
                self.assertEqual(response.content_type, content_type)


class AnswerDashboardRequestOfAViewTest(unittest.TestCase):
    def test_should_render_the_waves_view_from_the_list_of_the_waves_and_the_overview_of_the_ledger(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {WAVE_LIST: ProcessAnswer(stdout=NO_WAVE), LEDGER_OVERVIEW: ProcessAnswer(stdout=NO_WAVE_STARTED)}
        )

        # Act
        response = answer_get("/views/waves", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(runner.argvs, [WAVE_LIST, LEDGER_OVERVIEW])
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b'<p class="status-sentence">Waves open: 0, parked: 0, blocked: 0.</p><div class="stat-tiles">'
                b'<div class="stat-tile"><span class="stat-value">0</span><span class="stat-label">open now</span>'
                b'<span class="stat-perimeter">0 parked, 0 blocked</span></div>'
                b'<div class="stat-tile"><span class="stat-value">0</span><span class="stat-label">started</span>'
                b'<span class="stat-perimeter">by month: none</span></div>'
                b'<div class="stat-tile"><span class="stat-value">0</span><span class="stat-label">closed</span>'
                b'<span class="stat-perimeter">0 cancelled</span></div>'
                b'<div class="stat-tile"><span class="stat-value">0 of 0</span>'
                b'<span class="stat-label">tasks merged</span>'
                b'<span class="stat-perimeter">over the last 12 waves, 0 merged nothing</span></div></div>'
                b"<p>no wave started</p>",
            ),
        )

    def test_should_render_the_error_of_a_failing_command_under_its_status(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "wave", "show"): ProcessAnswer(exit_code=1, stderr="no wave w9\n"),
                WAVE_LIST: ProcessAnswer(stdout=NO_WAVE),
                (PYTHON, ENTRY_POINT, "ledger"): ProcessAnswer(exit_code=1, stderr="the ledger is unreadable\n"),
            }
        )

        # Act
        response = answer_get("/views/waves/w9", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)
        self.assertEqual(response.body, b"<dl><dt>error</dt><dd>no wave w9\n</dd></dl>")


class AnswerDashboardRequestOfTheInboxViewTest(unittest.TestCase):
    def test_should_render_the_signals_and_the_patterns_of_the_inbox(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "inbox", "list", "--json"): ProcessAnswer(
                    stdout='{"schema_version": 1, "signals": [], "families": [], "patterns": [], "answers": []}\n'
                )
            }
        )

        # Act
        response = answer_get("/views/inbox", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b"<section><h2>Signals</h2><p>no new signal</p></section>"
                b"<section><h2>Patterns</h2><p>no pattern proposed</p></section>",
            ),
        )

    def test_should_render_the_error_of_a_failing_inbox_list(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {(PYTHON, ENTRY_POINT, "inbox", "list"): ProcessAnswer(exit_code=1, stderr="the inbox is unreadable\n")}
        )

        # Act
        response = answer_get("/views/inbox", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 500)
        self.assertEqual(response.body, b"<dl><dt>error</dt><dd>the inbox is unreadable\n</dd></dl>")


INBOX_LIST = (PYTHON, ENTRY_POINT, "inbox", "list", "--json")
INBOX_HOLDING_A_NOTE_AND_A_PATTERN = (
    '{"schema_version": 1, "signals": [{"id": "a4a5f464", "fingerprint": "note:474fa40ae4db", "kind": "note",'
    ' "project": "oak", "count": 1, "age_s": 60, "status": "new"}], "families": [],'
    ' "patterns": [{"name": "FlakyTests", "action": "constraint", "signals": ["a4a5f464"]}]}\n'
)

HOME = (
    '{"schema_version": 1, "projects": [{"name": "oak", "paused": false}], "waves": [], "inbox": {"new_signals": 0, "scans": []},'
    ' "quota": {"window_hours": 5, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,'
    ' "cache_read_input_tokens": 0}, "runs_without_usage": 0, "blocked_waves": []}, "last_tick": null, "studies": [], "orders": []}\n'
)
WAVE_W4_SHOWN = (
    '{"schema_version": 1, "wave": "w4", "project": "oak", "branch": "integration/w4", "started_at":'
    ' "2026-10-19T07:00:00Z", "last_event": "task.parked", "pull_request": null, "milestone": "M4",'
    ' "milestone_report": null, "tasks": [{"task": "B28", "state": "parked", "pull_request": 235, "run": "r28",'
    ' "reason": "blocked"}], "ledger": {"view": "wave", "wave": "w4", "first": "2026-10-19T07:00:00Z",'
    ' "last": "2026-10-19T07:00:00Z", "wall_time_ms": 0, "tasks": [], "cost_usd": null, "by_task": [],'
    ' "halts": [], "halted_ms": 0, "rounds_by_task": {}, "turns_by_task": {"B28": 12}, "events":'
    ' [{"at": "2026-10-19T07:00:00Z", "event": "wave.started", "fields": {"wave": "w4"}}]}}\n'
)
OAK_ON_GITHUB = (
    '{"schema_version": 1, "project": {"name": "oak", "fields": [{"name": "FORGE", "value": "github"},'
    ' {"name": "REMOTE", "value": "acme/oak"}]}}\n'
)
WAVE_W4_EVENTS = (PYTHON, ENTRY_POINT, "wave", "show", "--json", "--events", "w4")
OAK_SHOW = (PYTHON, ENTRY_POINT, "project", "show", "--json", "oak")


def answer_post(target: str, runtime) -> DashboardResponse:
    incoming = IncomingRequest(
        method="POST", target=target, host=LOOPBACK_HOST, origin=LOOPBACK_ORIGIN, token=ISSUED_CREDENTIAL
    )
    return answer_dashboard_request(incoming, DASHBOARD, runtime)


class AnswerDashboardRequestOfAnActionTest(unittest.TestCase):
    def test_should_serve_the_json_of_the_command_the_action_runs(self):
        # Arrange
        rows = [
            ("/api/inbox/ratify/FlakyTests", ("inbox", "ratify", "--json", "FlakyTests")),
            ("/api/inbox/ratify/FlakyTests?kind=guard", ("inbox", "ratify", "--kind=guard", "--json", "FlakyTests")),
            ("/api/inbox/dismiss/FlakyTests", ("inbox", "dismiss", "--json", "FlakyTests")),
            ("/api/inbox/dismiss/a4a5f464", ("inbox", "dismiss", "--json", "a4a5f464")),
            ("/api/projects/oak/pause", ("project", "pause", "--json", "oak")),
            ("/api/projects/oak/resume", ("project", "resume", "--json", "oak")),
            ("/api/waves/w4/resume", ("wave", "resume", "--json", "w4")),
            ("/api/waves/w4/tasks/B28/requeue", ("wave", "requeue", "--json", "w4", "B28")),
        ]
        for target, arguments in rows:
            with self.subTest(target=target):
                runner = ScriptedProcessRunner({(PYTHON, ENTRY_POINT, *arguments): ProcessAnswer(stdout='{"a": 1}\n')})

                # Act
                response = answer_post(target, create_test_runtime(run_process=runner.run))

                # Assert
                self.assertEqual(response, DashboardResponse(status=200, content_type=JSON, body=b'{"a": 1}\n'))

    def test_should_answer_not_found_for_a_pattern_or_a_signal_the_inbox_does_not_list(self):
        # Arrange
        rows = [
            ("/api/inbox/ratify/LongNames", ("inbox", "ratify")),
            ("/api/inbox/dismiss/LongNames", ("inbox", "dismiss")),
        ]
        for target, arguments in rows:
            with self.subTest(target=target):
                runner = ScriptedProcessRunner(
                    {
                        (PYTHON, ENTRY_POINT, *arguments): ProcessAnswer(exit_code=1, stderr="LongNames is unknown\n"),
                        INBOX_LIST: ProcessAnswer(stdout=INBOX_HOLDING_A_NOTE_AND_A_PATTERN),
                    }
                )

                # Act
                response = answer_post(target, create_test_runtime(run_process=runner.run))

                # Assert
                self.assertEqual(response.status, 404)

    def test_should_answer_a_server_error_for_a_pattern_or_a_signal_the_inbox_lists(self):
        # Arrange
        rows = [
            ("/api/inbox/ratify/FlakyTests", ("inbox", "ratify")),
            ("/api/inbox/dismiss/FlakyTests", ("inbox", "dismiss")),
            ("/api/inbox/dismiss/a4a5f464", ("inbox", "dismiss")),
        ]
        for target, arguments in rows:
            with self.subTest(target=target):
                runner = ScriptedProcessRunner(
                    {
                        (PYTHON, ENTRY_POINT, *arguments): ProcessAnswer(exit_code=1, stderr="the corpus is locked\n"),
                        INBOX_LIST: ProcessAnswer(stdout=INBOX_HOLDING_A_NOTE_AND_A_PATTERN),
                    }
                )

                # Act
                response = answer_post(target, create_test_runtime(run_process=runner.run))

                # Assert
                self.assertEqual(
                    response,
                    DashboardResponse(status=500, content_type=JSON, body=b'{"error": "the corpus is locked\\n"}'),
                )

    def test_should_answer_not_found_and_run_nothing_for_a_path_no_action_serves(self):
        # Arrange
        rows = [
            "/api/inbox/ratify/-h",
            "/api/inbox/dismiss/",
            "/api/inbox/accept/FlakyTests",
            "/api/inbox/ratify/FlakyTests/again",
            "/api/inbox",
            "/views/inbox/dismiss/FlakyTests",
            "inbox/dismiss/FlakyTests",
            "waves/w4/resume",
        ]
        runtime = create_test_runtime()
        for target in rows:
            with self.subTest(target=target):
                # Act
                response = answer_post(target, runtime)

                # Assert
                self.assertEqual(response.status, 404)

    def test_should_never_run_an_action_on_a_get(self):
        # Arrange
        rows = ["/api/inbox/ratify/FlakyTests", "/api/inbox/dismiss/FlakyTests"]
        runtime = create_test_runtime()
        for target in rows:
            with self.subTest(target=target):
                # Act
                response = answer_get(target, runtime)

                # Assert
                self.assertEqual(response.status, 404)

    def test_should_answer_not_found_for_a_project_not_registered(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "project", "pause"): ProcessAnswer(
                    exit_code=1, stderr="brigade project pause: @PROJECT.elm is not registered\n"
                ),
                PROJECT_LIST: ProcessAnswer(stdout=NO_PROJECT),
            }
        )

        # Act
        response = answer_post("/api/projects/elm/pause", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfAReportNoListingNamesTest(unittest.TestCase):
    def test_should_answer_not_found(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "report", "show"): ProcessAnswer(exit_code=1, stderr="no report oak_w9\n"),
                (PYTHON, ENTRY_POINT, "report", "list"): ProcessAnswer(stdout='{"schema_version": 1, "reports": []}'),
            }
        )

        # Act
        response = answer_get("/api/reports/oak_w9", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfTheReportsViewsTest(unittest.TestCase):
    def test_should_render_the_list_of_the_reports(self):
        # Arrange
        listed = '{"schema_version": 1, "reports": []}'
        runner = ScriptedProcessRunner(
            {(PYTHON, ENTRY_POINT, "report", "list", "--json"): ProcessAnswer(stdout=listed)}
        )

        # Act
        response = answer_get("/views/reports", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response, DashboardResponse(status=200, content_type="text/html; charset=utf-8", body=b"<p>no report</p>")
        )

    def test_should_render_the_report_asked(self):
        # Arrange
        shown = (
            '{"schema_version": 1, "report": {"id": "oak_w3", "kind": "wave-report", "project": "oak",'
            ' "type": "REPORT", "fields": [{"name": "WAVE", "value": "oak_w3"}]}}'
        )
        runner = ScriptedProcessRunner(
            {(PYTHON, ENTRY_POINT, "report", "show", "--json", "oak_w3"): ProcessAnswer(stdout=shown)}
        )

        # Act
        response = answer_get("/views/reports/oak_w3", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b"<h2>wave-report oak_w3</h2><dl><dt>WAVE</dt><dd>oak_w3</dd></dl>",
            ),
        )


class AnswerDashboardRequestOfTheLedgerViewTest(unittest.TestCase):
    def test_should_run_the_commands_of_the_sections_the_query_asks_for(self):
        # Arrange
        overview = ProcessAnswer(
            stdout=(
                '{"schema_version": 1, "view": "overview", "events": {}, "first": null, "last": null, "files": [],'
                ' "runs": {"outcomes": {}, "error_classes": {}}, "segments": {"outcomes": {}, "error_classes": {}},'
                ' "waves_started": {}, "failed_actions": {"by_day": {}, "by_action": {}}, "since": null, "skipped": []}'
            )
        )
        budgets = ProcessAnswer(stdout='{"schema_version": 1, "last": 20, "procedures": {}, "roles": {}}')
        refused = ProcessAnswer(exit_code=1, stderr="refused\n")
        rows = [
            (
                "/views/ledger",
                [(PYTHON, ENTRY_POINT, "ledger", "--json"), (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json")],
            ),
            (
                "/views/ledger?wave=w4&range=2026-09-01..2026-09-30&range=2026-10-01..2026-10-31",
                [
                    (PYTHON, ENTRY_POINT, "ledger", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json"),
                    (PYTHON, ENTRY_POINT, "wave", "show", "--json", "--events", "w4"),
                    (
                        PYTHON,
                        ENTRY_POINT,
                        "ledger",
                        "compare",
                        "--range=2026-09-01..2026-09-30",
                        "--range=2026-10-01..2026-10-31",
                        "--json",
                    ),
                ],
            ),
            (
                (
                    "/views/ledger?wave=w4&wave=w5&range=2026-09-01..2026-09-30&range=2026-10-01..2026-10-31"
                    "&range=2026-11-01..2026-11-30"
                ),
                [
                    (PYTHON, ENTRY_POINT, "ledger", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json"),
                    (PYTHON, ENTRY_POINT, "wave", "show", "--json", "--events", "w4"),
                    (
                        PYTHON,
                        ENTRY_POINT,
                        "ledger",
                        "compare",
                        "--range=2026-09-01..2026-09-30",
                        "--range=2026-10-01..2026-10-31",
                        "--json",
                    ),
                ],
            ),
        ]
        for target, commands in rows:
            with self.subTest(target=target):
                runner = ScriptedProcessRunner(
                    {
                        (PYTHON, ENTRY_POINT, "ledger", "--json"): overview,
                        (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json"): budgets,
                        (PYTHON, ENTRY_POINT, "wave", "show", "--json", "--events", "w4"): refused,
                        (PYTHON, ENTRY_POINT, "ledger", "compare"): refused,
                    }
                )

                # Act
                response = answer_get(target, create_test_runtime(run_process=runner.run))

                # Assert
                self.assertEqual(response.status, 200)
                self.assertEqual(runner.argvs, commands)


class AnswerDashboardRequestOfTheCorpusViewTest(unittest.TestCase):
    def test_should_render_the_board_of_the_corpus_at_the_ref(self):
        # Arrange
        board_of_oak = json.dumps(
            {
                "project": "oak",
                "ref": "main",
                "sha": "de446f3",
                "type": "TASK",
                "types": ["TASK"],
                "entities": [],
                "awawa_web": None,
                "field": "STATUS",
                "board": [{"value": "todo", "targets": ["@TASK.B30"]}],
            }
        )
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "corpus", "--ref=main", "--type=TASK", "--field=STATUS", "--json", "oak"): (
                    ProcessAnswer(stdout=board_of_oak)
                )
            }
        )

        # Act
        response = answer_get(
            "/views/corpus/oak?ref=main&type=TASK&field=STATUS", create_test_runtime(run_process=runner.run)
        )

        # Assert
        self.assertIn(
            b'<section class="board"><h2>STATUS</h2><div><h3>todo</h3><ul><li>@TASK.B30</li></ul></div></section>',
            response.body,
        )

    def test_should_offer_the_registered_projects_to_choose_from(self):
        # Arrange
        projects = '{"schema_version": 1, "projects": [{"name": "oak", "path": "/srv/oak", "status": "active"}]}'
        runner = ScriptedProcessRunner({PROJECT_LIST: ProcessAnswer(stdout=projects)})

        # Act
        response = answer_get("/views/corpus", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertIn(b'<a href="#corpus/oak">oak</a>', response.body)

    def test_should_render_the_error_of_a_project_not_registered(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "corpus"): ProcessAnswer(
                    exit_code=1, stderr="brigade corpus: @PROJECT.elm is not registered\n"
                ),
                PROJECT_LIST: ProcessAnswer(stdout=NO_PROJECT),
            }
        )

        # Act
        response = answer_get("/views/corpus/elm?ref=main&type=TASK", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)
        self.assertEqual(
            response.body, b"<dl><dt>error</dt><dd>brigade corpus: @PROJECT.elm is not registered\n</dd></dl>"
        )


class AnswerDashboardRequestOfTheHomeViewTest(unittest.TestCase):
    def test_should_render_the_document_of_brigade_status(self):
        # Arrange
        runner = ScriptedProcessRunner({(PYTHON, ENTRY_POINT, "status", "--json"): ProcessAnswer(stdout=HOME)})

        # Act
        response = answer_get("/views/status", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 200)
        self.assertIn(
            b'<li>oak, active <button type="button" data-post="/api/projects/oak/pause">pause</button></li>',
            response.body,
        )


class AnswerDashboardRequestOfTheWaveViewTest(unittest.TestCase):
    def test_should_link_the_pull_requests_of_the_wave_on_the_forge_project_show_names(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {WAVE_W4_EVENTS: ProcessAnswer(stdout=WAVE_W4_SHOWN), OAK_SHOW: ProcessAnswer(stdout=OAK_ON_GITHUB)}
        )

        # Act
        response = answer_get("/views/waves/w4", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 200)
        self.assertIn(b'<td><a href="https://github.com/acme/oak/pull/235">#235</a></td>', response.body)

    def test_should_name_the_pull_requests_unlinked_when_project_show_fails(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                WAVE_W4_EVENTS: ProcessAnswer(stdout=WAVE_W4_SHOWN),
                OAK_SHOW: ProcessAnswer(exit_code=1, stderr="brigade project show: @PROJECT.oak is not registered\n"),
            }
        )

        # Act
        response = answer_get("/views/waves/w4", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 200)
        self.assertIn(b"<td>#235</td>", response.body)


class AnswerDashboardRequestOfAMethodNeitherReadingNorChangingStateTest(unittest.TestCase):
    def test_should_answer_not_found_and_serve_nothing(self):
        # Arrange
        incoming = IncomingRequest(method="DELETE", target="/", host=LOOPBACK_HOST)

        # Act
        response = answer_dashboard_request(incoming, DASHBOARD, create_test_runtime())

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(status=404, content_type=JSON, body=b'{"error": "no route serves the method DELETE"}'),
        )


RUN_LIST = (PYTHON, ENTRY_POINT, "run", "list", "--json")
NO_RUN = '{"schema_version": 1, "runs": [], "skipped": []}\n'
RUN_R1_SHOWN = (
    '{"schema_version": 1, "run": {"run": "r1", "procedure": "build-task", "slot": "build", "role": "ada",'
    ' "project": "oak", "worktree": "/srv/oak/B94", "state": "running", "outcome": null, "wave": null,'
    ' "task": null, "message": null}, "segments": [], "log": null,'
    ' "progress": {"text": "ENTRY e1 <read>\\n", "entities": null}}\n'
)


class AnswerDashboardRequestOfARunNoListingNamesTest(unittest.TestCase):
    def test_should_answer_not_found(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "run", "show"): ProcessAnswer(
                    exit_code=1, stderr="brigade run show: no run r9\n"
                ),
                RUN_LIST: ProcessAnswer(stdout=NO_RUN),
            }
        )

        # Act
        response = answer_get("/api/runs/r9", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)


class AnswerDashboardRequestOfTheRunsViewsTest(unittest.TestCase):
    def test_should_render_the_list_of_the_runs(self):
        # Arrange
        runner = ScriptedProcessRunner({RUN_LIST: ProcessAnswer(stdout=NO_RUN)})

        # Act
        response = answer_get("/views/runs", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response, DashboardResponse(status=200, content_type="text/html; charset=utf-8", body=b"<p>no run</p>")
        )

    def test_should_render_the_run_asked_with_its_progress(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {(PYTHON, ENTRY_POINT, "run", "show", "--json", "r1"): ProcessAnswer(stdout=RUN_R1_SHOWN)}
        )

        # Act
        response = answer_get("/views/runs/r1", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 200)
        self.assertIn(b"<h3>Progress</h3><pre>ENTRY e1 &lt;read&gt;\n</pre>", response.body)

    def test_should_render_the_error_of_a_run_no_listing_names(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "run", "show"): ProcessAnswer(
                    exit_code=1, stderr="brigade run show: no run r9\n"
                ),
                RUN_LIST: ProcessAnswer(stdout=NO_RUN),
            }
        )

        # Act
        response = answer_get("/views/runs/r9", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)
        self.assertEqual(response.body, b"<dl><dt>error</dt><dd>brigade run show: no run r9\n</dd></dl>")


INBOX_HOLDING_A_NOTE_AND_A_STUDY_ANSWER = (
    '{"schema_version": 1, "signals": [{"id": "a4a5f464", "fingerprint": "note:474fa40ae4db", "kind": "note",'
    ' "project": "oak", "count": 1, "age_s": 60, "status": "new"}], "families": [], "patterns": [],'
    ' "answers": [{"id": "disk_r2", "study": "disk", "project": "oak"}]}\n'
)
STUDY_ANSWER_DISK_R2_SHOWN = (
    '{"schema_version": 1, "answer": {"id": "disk_r2", "study": "disk", "project": "oak", "type": "ANSWER",'
    ' "fields": [{"name": "STUDY", "value": "disk"}, {"name": "SUMMARY", "value": "the disk <fills>"}]}}\n'
)


class AnswerDashboardRequestOfAnInboxItemTest(unittest.TestCase):
    def test_should_render_a_study_answer_under_its_title_with_its_fields(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "inbox", "show", "--json", "disk_r2"): ProcessAnswer(
                    stdout=STUDY_ANSWER_DISK_R2_SHOWN
                )
            }
        )

        # Act
        response = answer_get("/views/inbox/disk_r2", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b"<h2>study-answer disk_r2</h2>"
                b"<dl><dt>STUDY</dt><dd>disk</dd><dt>SUMMARY</dt><dd>the disk &lt;fills&gt;</dd></dl>",
            ),
        )

    def test_should_answer_not_found_for_an_id_the_inbox_lists_neither_as_a_signal_nor_as_a_study_answer(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "inbox", "show"): ProcessAnswer(exit_code=1, stderr="no signal zz99\n"),
                INBOX_LIST: ProcessAnswer(stdout=INBOX_HOLDING_A_NOTE_AND_A_STUDY_ANSWER),
            }
        )

        # Act
        response = answer_get("/api/inbox/zz99", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)

    def test_should_answer_a_server_error_for_a_signal_or_a_study_answer_the_inbox_lists(self):
        # Arrange
        for item in ("a4a5f464", "disk_r2"):
            with self.subTest(item=item):
                runner = ScriptedProcessRunner(
                    {
                        (PYTHON, ENTRY_POINT, "inbox", "show"): ProcessAnswer(exit_code=1, stderr="unreadable\n"),
                        INBOX_LIST: ProcessAnswer(stdout=INBOX_HOLDING_A_NOTE_AND_A_STUDY_ANSWER),
                    }
                )

                # Act
                response = answer_get(f"/api/inbox/{item}", create_test_runtime(run_process=runner.run))

                # Assert
                self.assertEqual(response.status, 500)


SCHEDULER_STATUS = (PYTHON, ENTRY_POINT, "scheduler", "status", "--json")
STALE_SCHEDULER = (
    '{"schema_version": 1, "last_tick": {"ts": "2026-10-19T08:00:00Z", "duration_ms": 4, "actions_applied": 0},'
    ' "tick_stale_after": 15, "stale": true}\n'
)


class AnswerDashboardRequestOfTheHeartbeatTest(unittest.TestCase):
    def test_should_render_the_last_tick_of_a_stale_scheduler_under_200(self):
        # Arrange
        runner = ScriptedProcessRunner({SCHEDULER_STATUS: ProcessAnswer(exit_code=1, stdout=STALE_SCHEDULER)})

        # Act
        response = answer_get("/views/heartbeat", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b'<p class="heartbeat">Last tick <time datetime="2026-10-19T08:00:00Z">2026-10-19T08:00:00Z</time>,'
                b' 60 min ago <strong class="heartbeat-stale">stale</strong></p>',
            ),
        )


class AnswerDashboardRequestOfTheProjectSelectorTest(unittest.TestCase):
    def test_should_select_the_project_carried_in_the_address(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {PROJECT_LIST: ProcessAnswer(stdout='{"schema_version": 1, "projects": [{"name": "oak"}]}\n')}
        )

        # Act
        response = answer_get("/views/selector?project=oak", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response.body,
            b'<label>Project <select name="project"><option value="">All projects</option>'
            b'<option value="oak" selected>oak</option></select></label><button>show</button>',
        )

    def test_should_list_every_project_whichever_project_the_address_carries(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                PROJECT_LIST: ProcessAnswer(
                    stdout='{"schema_version": 1, "projects": [{"name": "oak"}, {"name": "elm"}]}\n'
                )
            }
        )

        # Act
        response = answer_get("/views/selector?project=oak", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertIn(b'<option value="elm">elm</option>', response.body)


class AnswerDashboardRequestOfAViewOfOneProjectTest(unittest.TestCase):
    def test_should_leave_out_of_home_the_projects_and_the_blocked_waves_of_the_others(self):
        # Arrange
        home = json.loads(HOME)
        home["projects"] = [{"name": "oak", "paused": False}, {"name": "elm", "paused": True}]
        home["quota"]["blocked_waves"] = [
            {"wave": "oak_w2", "project": "oak", "resume_at": "2026-10-19T10:00:00Z"},
            {"wave": "elm_w1", "project": "elm", "resume_at": "2026-10-19T10:00:00Z"},
        ]
        runner = ScriptedProcessRunner(
            {(PYTHON, ENTRY_POINT, "status", "--json"): ProcessAnswer(stdout=json.dumps(home))}
        )

        # Act
        response = answer_get("/views/status?project=oak", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertNotIn(b"elm", response.body)
        self.assertIn(b"oak_w2 blocked on quota", response.body)

    def test_should_render_the_rows_of_that_project_alone(self):
        # Arrange
        oak_wave = {
            "wave": "w4",
            "project": "oak",
            "branch": "integration/w4",
            "last_event": "wave.started",
            "tasks": 0,
            "started_at": "2026-11-02T08:00:00Z",
            "ended_at": None,
            "ended_by": None,
            "task_states": [],
            "halt": None,
            "rounds": 0,
            "cost_usd": None,
        }
        waves = json.dumps({"schema_version": 1, "waves": [oak_wave, {**oak_wave, "wave": "w5", "project": "elm"}]})
        overview = '{"schema_version": 1, "view": "overview", "waves_started": {"2026-11": ["w4", "w5"]}}\n'
        runner = ScriptedProcessRunner(
            {WAVE_LIST: ProcessAnswer(stdout=waves), LEDGER_OVERVIEW: ProcessAnswer(stdout=overview)}
        )

        # Act
        response = answer_get("/views/waves?project=oak", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertIn(b'<a href="#waves/w4">w4</a>', response.body)
        self.assertNotIn(b"w5", response.body)


def create_dashboard_with_an_addon(test_case: unittest.TestCase, starter: ChildStarterDouble) -> Dashboard:
    addon = AwawaAddonSupervisor(lambda: frozenset({"app"}), starter.start, ANSWER_TIMEOUT_S)
    test_case.addCleanup(addon.stop)
    return Dashboard(port=8470, token=ISSUED_CREDENTIAL, addon=addon)


class AnswerDashboardRequestOfTheAwawaAddonTest(unittest.TestCase):
    def setUp(self):
        self.starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        self.dashboard = create_dashboard_with_an_addon(self, self.starter)

    def test_should_relay_the_project_and_the_arguments_of_the_view_and_answer_the_document(self):
        # Arrange
        incoming = IncomingRequest(
            method="GET",
            target="/api/awawa/app?ref=worktree%3Ab42&view=board&type=TASK&filter=STATUS%3Dtodo&filter=ROLE%3Dada",
            host=LOOPBACK_HOST,
        )

        # Act
        response = answer_dashboard_request(incoming, self.dashboard, create_test_runtime())

        # Assert
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, JSON)
        self.assertEqual(
            json.loads(response.body),
            {
                "asked": {
                    "project": "app",
                    "ref": "worktree:b42",
                    "view": "board",
                    "type": "TASK",
                    "filter": ["STATUS=todo", "ROLE=ada"],
                }
            },
        )

    def test_should_answer_the_status_the_addon_answers(self):
        # Arrange
        incoming = IncomingRequest(method="GET", target="/api/awawa/shop?view=tree", host=LOOPBACK_HOST)

        # Act
        response = answer_dashboard_request(incoming, self.dashboard, create_test_runtime())

        # Assert
        self.assertEqual(response.status, 404)
        self.assertEqual(json.loads(response.body), {"error": "@PROJECT.shop holds no awawa corpus"})

    def test_should_refuse_a_foreign_host_without_asking_the_addon(self):
        # Arrange
        incoming = IncomingRequest(method="GET", target="/api/awawa/app?view=tree", host="attacker.example:8470")

        # Act
        response = answer_dashboard_request(incoming, self.dashboard, create_test_runtime())

        # Assert
        self.assertEqual(response.status, 400)
        self.assertEqual(self.starter.children, [])

    def test_should_serve_no_route_for_an_address_naming_no_project_or_more_than_one(self):
        for target in ("/api/awawa/", "/api/awawa/app/board"):
            with self.subTest(target=target):
                # Arrange
                incoming = IncomingRequest(method="GET", target=target, host=LOOPBACK_HOST)

                # Act
                response = answer_dashboard_request(incoming, self.dashboard, create_test_runtime())

                # Assert
                self.assertEqual(response.status, 404)
                self.assertEqual(json.loads(response.body), {"error": f"no route serves {target}"})
                self.assertEqual(self.starter.children, [])
