import tempfile
import unittest
from pathlib import Path

from brigade.commands._read_attribution import read_attribution
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

ATTRIBUTING_PROBE = {
    "schema_version": 1,
    "client": "scripted",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
    "attribution": ["Co-authored-by: Scripted <scripted@example.org>"],
}


class ReadAttributionTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"probe": ATTRIBUTING_PROBE})
        self.runtime = create_test_runtime(
            create_test_paths(Path(self.root.name)),
            resolve_plugin=create_plugin_resolver({("client", "scripted"): client}),
        )

    def test_should_take_the_attribution_the_configuration_states(self):
        # Arrange
        configuration = Configuration(client="scripted", attribution=("Signed-off-by: Ada <ada@example.org>",))

        # Act
        attribution = read_attribution(configuration, self.runtime)

        # Assert
        self.assertEqual(attribution, ["Signed-off-by: Ada <ada@example.org>"])

    def test_should_take_the_attribution_the_configured_client_declares(self):
        # Arrange
        configuration = Configuration(client="scripted")

        # Act
        attribution = read_attribution(configuration, self.runtime)

        # Assert
        self.assertEqual(attribution, ["Co-authored-by: Scripted <scripted@example.org>"])

    def test_should_attribute_nothing_without_a_client(self):
        # Arrange
        configuration = Configuration()

        # Act
        attribution = read_attribution(configuration, self.runtime)

        # Assert
        self.assertEqual(attribution, [])
