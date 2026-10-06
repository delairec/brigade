import os
import unittest
from pathlib import Path
from unittest import mock

from brigade.system.paths import Paths, build_paths


def build_paths_under(environment: dict) -> Paths:
    with mock.patch.dict(os.environ, environment, clear=True):
        return build_paths()


class BuildPaths(unittest.TestCase):
    def test_should_build_the_roots_from_the_xdg_variables(self):
        # Arrange
        environment = {
            "HOME": "/home/ada",
            "XDG_CONFIG_HOME": "/srv/config",
            "XDG_STATE_HOME": "/srv/state",
            "XDG_CACHE_HOME": "/srv/cache",
        }

        # Act
        paths = build_paths_under(environment)

        # Assert
        self.assertEqual(
            paths,
            Paths(
                config_root=Path("/srv/config/brigade"),
                state_root=Path("/srv/state/brigade"),
                cache_root=Path("/srv/cache/brigade"),
            ),
        )

    def test_should_fall_back_to_the_home_directories(self):
        rows = [
            ("unset", {"HOME": "/home/ada"}),
            ("empty", {"HOME": "/home/ada", "XDG_CONFIG_HOME": "", "XDG_STATE_HOME": "", "XDG_CACHE_HOME": ""}),
            (
                "relative",
                {"HOME": "/home/ada", "XDG_CONFIG_HOME": "config", "XDG_STATE_HOME": "state", "XDG_CACHE_HOME": "cache"},
            ),
        ]
        for case, environment in rows:
            with self.subTest(case=case):
                # Act
                paths = build_paths_under(environment)

                # Assert
                self.assertEqual(
                    paths,
                    Paths(
                        config_root=Path("/home/ada/.config/brigade"),
                        state_root=Path("/home/ada/.local/state/brigade"),
                        cache_root=Path("/home/ada/.cache/brigade"),
                    ),
                )
