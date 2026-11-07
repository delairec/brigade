import unittest

from brigade.commands._remember_forge_logins import remember_forge_logins

FORGE = object()
CHECK_RUNS_COLLECTOR = object()


def resolve_plugin(kind: str, name: str, **options) -> object:
    return {("forge", "github"): FORGE, ("collector", "check-runs"): CHECK_RUNS_COLLECTOR}[(kind, name)]


class RememberForgeLoginsTest(unittest.TestCase):
    def test_should_resolve_a_forge_to_one_keeper_of_its_logins_for_the_tick(self):
        # Arrange
        resolve = remember_forge_logins(resolve_plugin)
        first = resolve("forge", "github")

        # Act
        second = resolve("forge", "github")

        # Assert
        self.assertIs(second, first)

    def test_should_resolve_a_plugin_of_another_kind_as_it_is(self):
        # Arrange
        resolve = remember_forge_logins(resolve_plugin)

        # Act
        collector = resolve("collector", "check-runs")

        # Assert
        self.assertIs(collector, CHECK_RUNS_COLLECTOR)
