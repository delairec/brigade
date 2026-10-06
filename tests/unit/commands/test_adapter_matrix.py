import argparse
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.commands.adapter_matrix import adapter_matrix
from brigade.errors import ToolFailure
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.run_process import ProcessRequest


def _time_out(request: ProcessRequest):
    raise ToolFailure(f"{' '.join(request.argv)} timed out after 30 s")


class AdapterMatrixWhenAProbeTimesOutTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        search_directory = root / "bin"
        search_directory.mkdir()
        self.executable = search_directory / "brigade-client-slow"
        self.executable.write_text("#!/bin/sh\n")
        self.executable.chmod(0o755)
        self.runtime = Runtime(
            run_process=_time_out,
            paths=Paths(
                config_root=root / "config" / "brigade",
                state_root=root / "state" / "brigade",
                cache_root=root / "cache" / "brigade",
                home=root,
                executable_search_path=str(search_directory),
            ),
            now=datetime(2026, 10, 6, 9, 0, tzinfo=UTC),
            entry_point=Path("/srv/brigade/bin/brigade"),
        )

    def tearDown(self):
        self.root.cleanup()

    def test_should_name_the_timeout_in_the_row_of_the_adapter(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        document = adapter_matrix(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["adapters"][1],
            {
                "name": "slow",
                "audience": "supported_client",
                "capabilities": None,
                "error": f"{self.executable} probe timed out after 30 s",
            },
        )
