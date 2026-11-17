import json

from tests.cli.test_collector_run import CollectTestCase, install_executable

SILENT_CHECK = "#!/bin/sh\n"


class BrigadeCheckListTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        install_executable(self.project.path / ".brigade" / "checks" / "style", SILENT_CHECK)
        install_executable(self.machine.config_home / "brigade" / "checks" / "latency", SILENT_CHECK)
        install_executable(self.path_collectors / "brigade-check-coverage", SILENT_CHECK)

    def test_should_list_the_checks_of_the_four_sources(self):
        # Act
        completed = self.run_brigade(
            "check", "list", "--json", environment=self.describe_environment_with_collectors_on_path()
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "checks": [
                    {"name": "style", "source": "project"},
                    {"name": "latency", "source": "machine"},
                    {"name": "coverage", "source": "PATH"},
                    {"name": "acceptance", "source": "built-in"},
                    {"name": "ancestry", "source": "built-in"},
                    {"name": "body", "source": "built-in"},
                    {"name": "check_runs", "source": "built-in"},
                    {"name": "corpus_at_head", "source": "built-in"},
                    {"name": "forge_logins", "source": "built-in"},
                    {"name": "moved_citations", "source": "built-in"},
                    {"name": "overlapping_deliverables", "source": "built-in"},
                    {"name": "privacy", "source": "built-in"},
                    {"name": "promotion", "source": "built-in"},
                    {"name": "reviewed", "source": "built-in"},
                    {"name": "tasks_outside_after", "source": "built-in"},
                    {"name": "untouched_files", "source": "built-in"},
                ],
            },
        )
