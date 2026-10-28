import unittest

from brigade.dashboard.route_action import route_action
from brigade.dashboard.route_command import PROJECT_LISTING, WAVE_LISTING, CommandRoute


class RouteActionTest(unittest.TestCase):
    def test_should_route_each_action_to_the_command_it_runs(self):
        # Arrange
        rows = [
            (
                "projects/oak/pause",
                CommandRoute(("project", "pause", "--json", "oak"), identifier="oak", listing=PROJECT_LISTING),
            ),
            (
                "projects/oak/resume",
                CommandRoute(("project", "resume", "--json", "oak"), identifier="oak", listing=PROJECT_LISTING),
            ),
            (
                "waves/w4/resume",
                CommandRoute(("wave", "resume", "--json", "w4"), identifier="w4", listing=WAVE_LISTING),
            ),
            (
                "waves/w4/tasks/B28/requeue",
                CommandRoute(("wave", "requeue", "--json", "w4", "B28"), identifier="w4", listing=WAVE_LISTING),
            ),
        ]
        for target, expected in rows:
            with self.subTest(target=target):
                # Act
                route = route_action(target)

                # Assert
                self.assertEqual(route, expected)

    def test_should_route_no_other_path(self):
        # Arrange
        rows = [
            "projects/oak/delete",
            "projects/oak",
            "projects/-h/pause",
            "projects//pause",
            "waves/w4/pause",
            "waves/--all/resume",
            "waves/w4/tasks/-x/requeue",
            "waves/w4/tasks/B28/park",
            "waves",
            "status",
        ]
        for target in rows:
            with self.subTest(target=target):
                # Act
                route = route_action(target)

                # Assert
                self.assertIsNone(route)
