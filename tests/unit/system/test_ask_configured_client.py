import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.test_clients import fake
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.parse_configuration import Configuration
from brigade.system.probe_request import ProbeRequest
from brigade.system.require_configured_client import ConfiguredClient
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class AskConfiguredClientTest(unittest.TestCase):
    def test_should_answer_for_the_client_and_name_the_slots_bound_elsewhere(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        configuration = Configuration(
            client="fake",
            clients={"fake": {"attribution": "Co-authored-by: Ada"}},
            slot_clients={"build": "fake", "review": "codex"},
        )

        # Act
        answer = ask_configured_client(
            fake,
            ConfiguredClient(name="fake", configuration=configuration),
            ProbeRequest(),
            create_test_runtime(create_test_paths(root)),
        )

        # Assert
        self.assertEqual(
            (answer.client, answer.slot_clients, answer.document["client"]), ("fake", {"review": "codex"}, "fake")
        )
