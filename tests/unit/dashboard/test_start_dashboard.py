import gc
import socket
import sys
import unittest
import warnings

from brigade.dashboard.start_dashboard import start_dashboard
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_runtime import create_test_runtime

ANY_FREE_PORT = 0
ISSUED_CREDENTIAL = "t0k3n"
ANOTHER_LOOPBACK_ADDRESS = "127.0.0.2"
WAVE_LIST = (sys.executable, "/srv/brigade/bin/brigade", "wave", "list", "--json")
SECURITY_POLICY = b"\r\nContent-Security-Policy: default-src 'self'\r\n"
CORS_HEADER_PREFIX = b"\r\naccess-control-"


def exchange(port: int, request: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port)) as connection:
        connection.sendall(request)
        connection.shutdown(socket.SHUT_WR)
        return b"".join(iter(lambda: connection.recv(4096), b""))


def occupy_a_loopback_port(test_case: unittest.TestCase) -> int:
    occupant = socket.socket()
    test_case.addCleanup(occupant.close)
    occupant.bind(("127.0.0.1", ANY_FREE_PORT))
    occupant.listen()
    return occupant.getsockname()[1]


class StartDashboardTest(unittest.TestCase):
    def setUp(self):
        runner = ScriptedProcessRunner({WAVE_LIST: ProcessAnswer(stdout='{"schema_version": 1, "waves": []}\n')})
        dashboard = start_dashboard(ANY_FREE_PORT, ISSUED_CREDENTIAL, create_test_runtime(run_process=runner.run))
        self.dashboard = dashboard.__enter__()
        self.addCleanup(dashboard.__exit__, None, None, None)

    def test_should_serve_on_the_loopback_address_alone(self):
        # Act
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection((ANOTHER_LOOPBACK_ADDRESS, self.dashboard.port)).close()

        # Assert
        self.assertEqual(self.dashboard.url, f"http://127.0.0.1:{self.dashboard.port}/")

    def test_should_carry_the_security_policy_on_every_response(self):
        # Arrange
        host = f"Host: 127.0.0.1:{self.dashboard.port}\r\n".encode()
        rows = [
            ("the page", b"GET / HTTP/1.0\r\n" + host + b"\r\n", b"HTTP/1.0 200 "),
            ("a foreign host", b"GET / HTTP/1.0\r\nHost: attacker.example\r\n\r\n", b"HTTP/1.0 400 "),
            ("a malformed request", b"NONSENSE\r\n\r\n", b"HTTP/1.0 400 "),
        ]
        for case, request, status_line in rows:
            with self.subTest(case=case):
                # Act
                response = exchange(self.dashboard.port, request)

                # Assert
                self.assertTrue(response.startswith(status_line), response)
                self.assertIn(SECURITY_POLICY, response)

    def test_should_carry_no_cors_header_whatever_the_origin(self):
        # Arrange
        headers = f"Host: 127.0.0.1:{self.dashboard.port}\r\nOrigin: http://attacker.example\r\n\r\n".encode()
        rows = [
            ("a route", b"GET /api/waves HTTP/1.0\r\n" + headers, b"HTTP/1.0 200 "),
            ("a preflight", b"OPTIONS /api/waves HTTP/1.0\r\n" + headers, b"HTTP/1.0 501 "),
        ]
        for case, request, status_line in rows:
            with self.subTest(case=case):
                # Act
                response = exchange(self.dashboard.port, request)

                # Assert
                self.assertTrue(response.startswith(status_line), response)
                self.assertNotIn(CORS_HEADER_PREFIX, response.lower())

    def test_should_carry_the_token_and_origin_of_a_post_to_the_guard(self):
        # Arrange
        request = (
            f"POST /api/waves HTTP/1.0\r\nHost: 127.0.0.1:{self.dashboard.port}\r\n"
            f"Origin: {self.dashboard.url.rstrip('/')}\r\nX-Brigade-Token: {ISSUED_CREDENTIAL}\r\nContent-Length: 0\r\n\r\n"
        ).encode()

        # Act
        response = exchange(self.dashboard.port, request)

        # Assert
        self.assertTrue(response.startswith(b"HTTP/1.0 404 "), response)


class StartDashboardOnATakenPortTest(unittest.TestCase):
    def test_should_refuse_naming_the_port(self):
        # Arrange
        port = occupy_a_loopback_port(self)

        # Act
        with self.assertRaises(BrigadeError) as raised, start_dashboard(port, ISSUED_CREDENTIAL, create_test_runtime()):
            pass

        # Assert
        self.assertEqual(str(raised.exception), f"cannot listen on port {port}: Address already in use")


class StartDashboardOnAPortOutOfRangeTest(unittest.TestCase):
    def test_should_refuse_naming_the_port_and_the_range(self):
        for port in (70000, -1):
            with self.subTest(port=port):
                # Act
                with self.assertRaises(BrigadeError) as raised, start_dashboard(port, ISSUED_CREDENTIAL, create_test_runtime()):
                    pass

                # Assert
                self.assertEqual(str(raised.exception), f"cannot listen on port {port}: not a port from 0 to 65535")


class StopDashboardTest(unittest.TestCase):
    def test_should_close_the_listening_socket(self):
        # Arrange
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("ignore")
            warnings.simplefilter("always", ResourceWarning)

            # Act
            with start_dashboard(ANY_FREE_PORT, ISSUED_CREDENTIAL, create_test_runtime()):
                pass
            gc.collect()

        # Assert
        self.assertEqual(caught, [])
