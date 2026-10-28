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


class AnswerDashboardRequestOfAnApiRouteTest(unittest.TestCase):
    def test_should_serve_the_json_of_the_command_the_route_runs(self):
        # Arrange
        rows = [
            ("/api/waves", ("wave", "list", "--json")),
            ("/api/waves/w4", ("wave", "show", "--json", "w4")),
            ("/api/inbox", ("inbox", "list", "--json")),
            ("/api/ledger", ("ledger", "--json")),
            ("/api/corpus/oak?ref=main", ("corpus", "--ref=main", "--json", "oak")),
            ("/api/corpus/oak", ("corpus", "--json", "oak")),
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
            }
        )

        # Act
        response = answer_get("/views/waves/w9", create_test_runtime(run_process=runner.run))

        # Assert
        self.assertEqual(response.status, 404)
        self.assertEqual(response.body, b"<dl><dt>error</dt><dd>no wave w9\n</dd></dl>")
