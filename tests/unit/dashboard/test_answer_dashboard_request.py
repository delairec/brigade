import json
import sys
import unittest

from brigade.dashboard.answer_dashboard_request import answer_dashboard_request
from brigade.dashboard.dashboard_exchange import Dashboard, DashboardResponse, IncomingRequest
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_runtime import create_test_runtime

PYTHON = sys.executable
ENTRY_POINT = "/srv/brigade/bin/brigade"
ISSUED_CREDENTIAL = "t0k3n"
DASHBOARD = Dashboard(port=8470, token=ISSUED_CREDENTIAL)
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
            ("/api/reports", ("reports", "list", "--json")),
            ("/api/reports/oak_w3", ("reports", "show", "--json", "oak_w3")),
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
            "/api/runs",
            "/api/waves/w4/tasks",
            "/api/waves/",
            "/api/waves/--help",
            "/api/corpus/-h?ref=main",
            "/nowhere",
            "/views/runs",
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
    def test_should_render_the_fragment_of_the_json_of_the_command(self):
        # Arrange
        runner = ScriptedProcessRunner({WAVE_LIST: ProcessAnswer(stdout='{"schema_version": 1, "waves": []}\n')})

        # Act
        response = answer_get("/views/waves", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b"<dl><dt>schema_version</dt><dd>1</dd><dt>waves</dt><dd><ol></ol></dd></dl>",
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
                    stdout='{"schema_version": 1, "signals": [], "families": [], "patterns": []}\n'
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
    '{"schema_version": 1, "projects": [{"name": "oak", "paused": false}], "waves": [], "inbox": {"new_signals": 0},'
    ' "quota": {"window_hours": 5, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,'
    ' "cache_read_input_tokens": 0}, "runs_without_usage": 0, "paused_waves": []}, "last_tick": null, "studies": []}\n'
)
WAVE_W4_SHOWN = (
    '{"schema_version": 1, "wave": "w4", "project": "oak", "branch": "integration/w4", "started_at":'
    ' "2026-10-19T07:00:00Z", "last_event": "task.parked", "pull_request": null, "tasks": [{"task": "B28",'
    ' "state": "parked", "pull_request": null, "run": "r28", "reason": "blocked"}]}\n'
)
WAVE_W4_LEDGER = (
    '{"view": "wave", "wave": "w4", "rounds_by_task": {}, "steps_by_task": {"B28": 12}, "timeline":'
    ' [{"at": "2026-10-19T07:00:00Z", "event": "wave.started", "fields": {"wave": "w4"}}]}\n'
)


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
                (PYTHON, ENTRY_POINT, "reports", "show"): ProcessAnswer(exit_code=1, stderr="no report oak_w9\n"),
                (PYTHON, ENTRY_POINT, "reports", "list"): ProcessAnswer(stdout='{"schema_version": 1, "reports": []}'),
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
            {(PYTHON, ENTRY_POINT, "reports", "list", "--json"): ProcessAnswer(stdout=listed)}
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
            {(PYTHON, ENTRY_POINT, "reports", "show", "--json", "oak_w3"): ProcessAnswer(stdout=shown)}
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
        overview = ProcessAnswer(stdout='{"schema_version": 1, "view": "overview", "waves_started": {}}')
        budgets = ProcessAnswer(stdout='{"schema_version": 1, "last": 20, "procedures": {}}')
        refused = ProcessAnswer(exit_code=1, stderr="refused\n")
        rows = [
            (
                "/views/ledger",
                [(PYTHON, ENTRY_POINT, "ledger", "--json"), (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json")],
            ),
            (
                "/views/ledger?wave=w4&before=2026-10-01",
                [
                    (PYTHON, ENTRY_POINT, "ledger", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "--wave=w4", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "compare", "--before=2026-10-01", "--json"),
                ],
            ),
            (
                "/views/ledger?wave=w4&wave=w5&before=2026-10-01&before=2026-11-01",
                [
                    (PYTHON, ENTRY_POINT, "ledger", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "--wave=w4", "--json"),
                    (PYTHON, ENTRY_POINT, "ledger", "compare", "--before=2026-10-01", "--json"),
                ],
            ),
        ]
        for target, commands in rows:
            with self.subTest(target=target):
                runner = ScriptedProcessRunner(
                    {
                        (PYTHON, ENTRY_POINT, "ledger", "--json"): overview,
                        (PYTHON, ENTRY_POINT, "ledger", "budgets", "--json"): budgets,
                        (PYTHON, ENTRY_POINT, "ledger", "--wave=w4"): refused,
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
    def test_should_render_the_wave_from_its_show_and_its_ledger(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "wave", "show", "--json", "w4"): ProcessAnswer(stdout=WAVE_W4_SHOWN),
                (PYTHON, ENTRY_POINT, "ledger", "--json", "--wave=w4"): ProcessAnswer(stdout=WAVE_W4_LEDGER),
            }
        )

        # Act
        response = answer_get("/views/waves/w4", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 200)
        self.assertIn(b"<li>B28, pull request -, run r28, 0 rounds, 12 steps, blocked", response.body)
        self.assertIn(b"<li>2026-10-19T07:00:00Z wave.started</li>", response.body)

    def test_should_render_the_error_of_its_ledger_under_the_status_of_its_show(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                (PYTHON, ENTRY_POINT, "wave", "show", "--json", "w4"): ProcessAnswer(stdout=WAVE_W4_SHOWN),
                (PYTHON, ENTRY_POINT, "ledger", "--json", "--wave=w4"): ProcessAnswer(
                    exit_code=1, stderr="the ledger is unreadable\n"
                ),
            }
        )

        # Act
        response = answer_get("/views/waves/w4", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(
            response,
            DashboardResponse(
                status=200,
                content_type="text/html; charset=utf-8",
                body=b"<dl><dt>error</dt><dd>the ledger is unreadable\n</dd></dl>",
            ),
        )


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
