import dataclasses
import unittest
from pathlib import Path

from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.parse_configuration import Configuration
from brigade.system.probe_request import ProbeRequest
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

PROBE_ANSWER = {
    "schema_version": 1,
    "client": "double",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
}


class ClientRecordingItsRequestDouble:
    def __init__(self):
        self.requests = []

    def answer(self, operation: str, request: dict) -> dict:
        self.requests.append(request)
        return PROBE_ANSWER


def create_runtime_on_a_session_bus(session_bus_address: str | None):
    paths = create_test_paths(Path("/srv/machine"))
    return create_test_runtime(dataclasses.replace(paths, session_bus_address=session_bus_address))


class AskNamedClientTest(unittest.TestCase):
    def test_should_complete_the_request_with_the_machine_and_the_configuration(self):
        # Arrange
        client = ClientRecordingItsRequestDouble()
        configuration = Configuration(client="double", clients={"double": {"model": "m1"}})
        runtime = create_runtime_on_a_session_bus("unix:path=/run/user/1000/bus")

        # Act
        ask_named_client(client, ClientQuestion("double", ProbeRequest()), configuration, runtime)

        # Assert
        self.assertEqual(
            client.requests,
            [
                {
                    "schema_version": 1,
                    "reasoning_table": {},
                    "settings": {"model": "m1"},
                    "home": "/srv/machine/home",
                    "session_bus_address": "unix:path=/run/user/1000/bus",
                }
            ],
        )

    def test_should_complete_the_request_with_no_session_bus_when_the_machine_has_none(self):
        # Arrange
        client = ClientRecordingItsRequestDouble()
        configuration = Configuration(client="double")
        no_session_bus = None
        runtime = create_runtime_on_a_session_bus(no_session_bus)

        # Act
        ask_named_client(client, ClientQuestion("double", ProbeRequest()), configuration, runtime)

        # Assert
        self.assertEqual(
            client.requests,
            [
                {
                    "schema_version": 1,
                    "reasoning_table": {},
                    "settings": {},
                    "home": "/srv/machine/home",
                    "session_bus_address": None,
                }
            ],
        )
