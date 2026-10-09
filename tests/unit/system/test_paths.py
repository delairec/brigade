import os
import unittest
from pathlib import Path
from unittest import mock

from brigade.system.paths import Paths, build_paths


def build_paths_under(environment: dict) -> Paths:
    with mock.patch.dict(os.environ, environment, clear=True):
        return build_paths()


class BuildPathsTest(unittest.TestCase):
    def test_should_build_the_roots_from_the_xdg_variables(self):
        # Arrange
        environment = {
            "HOME": "/home/ada",
            "PATH": "/usr/local/bin:/usr/bin",
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
                home=Path("/home/ada"),
                executable_search_path="/usr/local/bin:/usr/bin",
            ),
        )

    def test_should_fall_back_to_the_home_directories_and_the_default_search_path(self):
        rows = [
            ("unset", {"HOME": "/home/ada"}),
            ("empty", {"HOME": "/home/ada", "XDG_CONFIG_HOME": "", "XDG_STATE_HOME": "", "XDG_CACHE_HOME": ""}),
            (
                "relative",
                {
                    "HOME": "/home/ada",
                    "XDG_CONFIG_HOME": "config",
                    "XDG_STATE_HOME": "state",
                    "XDG_CACHE_HOME": "cache",
                },
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
                        home=Path("/home/ada"),
                        executable_search_path="/bin:/usr/bin",
                    ),
                )


class PathsSharedBySeveralComponentsTest(unittest.TestCase):
    def test_should_build_each_shared_file_and_directory_from_its_root(self):
        paths = Paths(
            config_root=Path("/srv/config/brigade"),
            state_root=Path("/srv/state/brigade"),
            cache_root=Path("/srv/cache/brigade"),
            home=Path("/home/ada"),
            executable_search_path="/usr/bin",
        )
        rows = [
            ("configuration_file", Path("/srv/config/brigade/config.toml")),
            ("lock_directory", Path("/srv/state/brigade/locks")),
            ("heartbeat_file", Path("/srv/state/brigade/tick.json")),
            ("schema_file", Path("/srv/config/brigade/_schema.awawa")),
        ]
        for shared_path, expected_path in rows:
            with self.subTest(shared_path=shared_path):
                # Act
                path = getattr(paths, shared_path)

                # Assert
                self.assertEqual(path, expected_path)
