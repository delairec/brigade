import unittest
from unittest import mock

from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import resolve_plugin
from brigade.system.run_process import ProcessRecord


def make_runtime(search_path: str = "/nonexistent"):
    return mock.Mock(
        paths=mock.Mock(executable_search_path=search_path),
        run_process=lambda request: ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=0, stdout="{}", stderr=""
        ),
    )


class ResolvePluginTest(unittest.TestCase):
    def test_should_resolve_a_built_in_forge_plugin(self):
        # Act
        plugin = resolve_plugin("forge", "github", make_runtime())

        # Assert
        self.assertTrue(hasattr(plugin, "describe_account"))

    def test_should_resolve_a_built_in_scheduler_plugin(self):
        # Act
        plugin = resolve_plugin("scheduler", "cron", make_runtime())

        # Assert
        self.assertTrue(hasattr(plugin, "install"))

    def test_should_refuse_a_built_in_plugin_that_does_not_exist(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_plugin("forge", "gitlab", make_runtime())

        # Assert
        self.assertEqual(str(raised.exception), "no forge plugin gitlab")

    def test_should_refuse_a_built_in_plugin_whose_name_is_not_an_identifier(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_plugin("forge", "not-an-identifier", make_runtime())

        # Assert
        self.assertEqual(str(raised.exception), "no forge plugin not-an-identifier")

    def test_should_resolve_a_built_in_client_plugin(self):
        # Act
        plugin = resolve_plugin("client", "claude-code", make_runtime())

        # Assert
        self.assertTrue(hasattr(plugin, "answer"))

    def test_should_refuse_a_client_name_that_does_not_match_the_pattern(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_plugin("client", "INVALID_NAME", make_runtime())

        # Assert
        self.assertEqual(
            str(raised.exception),
            "no client adapter INVALID_NAME: no built-in module and no brigade-client-INVALID_NAME on PATH",
        )

    def test_should_refuse_a_client_that_exists_nowhere(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_plugin("client", "nonexistent", make_runtime())

        # Assert
        self.assertEqual(
            str(raised.exception),
            "no client adapter nonexistent: no built-in module and no brigade-client-nonexistent on PATH",
        )

    def test_should_refuse_an_unknown_plugin_kind(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_plugin("widget", "anything", make_runtime())

        # Assert
        self.assertEqual(str(raised.exception), "no plugin kind widget")

    def test_should_reraise_a_module_not_found_for_a_different_module(self):
        # Arrange
        runtime = make_runtime()

        # Act
        with (
            mock.patch("importlib.import_module", side_effect=ModuleNotFoundError("other.module")),
            self.assertRaises(ModuleNotFoundError),
        ):
            resolve_plugin("forge", "github", runtime)
