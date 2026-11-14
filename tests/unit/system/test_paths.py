import getpass
import unittest
from pathlib import Path

import brigade
from brigade.system.paths import Paths, build_paths
from tests.unit.create_test_paths import PACKAGE_FILE


class BuildPathsTest(unittest.TestCase):
    def test_should_build_the_roots_from_the_xdg_variables(self):
        # Arrange
        environment = {
            "HOME": "/home/ada",
            "USER": "ada",
            "PATH": "/usr/local/bin:/usr/bin",
            "XDG_CONFIG_HOME": "/srv/config",
            "XDG_STATE_HOME": "/srv/state",
            "XDG_CACHE_HOME": "/srv/cache",
        }

        # Act
        paths = build_paths(environment)

        # Assert
        self.assertEqual(
            paths,
            Paths(
                config_root=Path("/srv/config/brigade"),
                state_root=Path("/srv/state/brigade"),
                cache_root=Path("/srv/cache/brigade"),
                home=Path("/home/ada"),
                executable_search_path="/usr/local/bin:/usr/bin",
                package_file=Path(brigade.__file__),
                user="ada",
            ),
        )

    def test_should_fall_back_to_the_home_directories_and_the_default_search_path(self):
        # Arrange
        rows = [
            ("unset", {"HOME": "/home/ada", "USER": "ada"}),
            (
                "empty",
                {"HOME": "/home/ada", "USER": "ada", "XDG_CONFIG_HOME": "", "XDG_STATE_HOME": "", "XDG_CACHE_HOME": ""},
            ),
            (
                "relative",
                {
                    "HOME": "/home/ada",
                    "USER": "ada",
                    "XDG_CONFIG_HOME": "config",
                    "XDG_STATE_HOME": "state",
                    "XDG_CACHE_HOME": "cache",
                },
            ),
        ]
        for case, environment in rows:
            with self.subTest(case=case):
                # Act
                paths = build_paths(environment)

                # Assert
                self.assertEqual(
                    paths,
                    Paths(
                        config_root=Path("/home/ada/.config/brigade"),
                        state_root=Path("/home/ada/.local/state/brigade"),
                        cache_root=Path("/home/ada/.cache/brigade"),
                        home=Path("/home/ada"),
                        executable_search_path="/bin:/usr/bin",
                        package_file=Path(brigade.__file__),
                        user="ada",
                    ),
                )


class BuildPathsWithoutAHomeVariableTest(unittest.TestCase):
    def test_should_take_the_home_of_the_account_when_no_variable_names_it(self):
        # Arrange
        no_variable = {}

        # Act
        paths = build_paths(no_variable)

        # Assert
        self.assertEqual(paths.home, Path.home())


class BuildPathsUserTest(unittest.TestCase):
    def test_should_name_the_user_the_environment_names(self):
        # Act
        paths = build_paths({"HOME": "/home/ada", "USER": "ada"})

        # Assert
        self.assertEqual(paths.user, "ada")

    def test_should_take_the_name_of_the_account_when_no_variable_names_it(self):
        # Arrange
        no_variable = {}

        # Act
        paths = build_paths(no_variable)

        # Assert
        self.assertEqual(paths.user, getpass.getuser())


class PathsSharedBySeveralComponentsTest(unittest.TestCase):
    def test_should_build_each_shared_file_and_directory_from_its_root(self):
        # Arrange
        paths = Paths(
            config_root=Path("/srv/config/brigade"),
            state_root=Path("/srv/state/brigade"),
            cache_root=Path("/srv/cache/brigade"),
            home=Path("/home/ada"),
            executable_search_path="/usr/bin",
            package_file=PACKAGE_FILE,
            user="ada",
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


class BuildPathsInsideARunTest(unittest.TestCase):
    def test_should_hold_the_run_directory_brigade_run_exported(self):
        # Act
        paths = build_paths({"HOME": "/home/ada", "BRIGADE_RUN_DIR": "/srv/state/brigade/runs/r1"})

        # Assert
        self.assertEqual(paths.run_directory, Path("/srv/state/brigade/runs/r1"))


class BuildPathsWithTheSessionBusTest(unittest.TestCase):
    def test_should_hold_the_address_of_the_session_bus_of_the_environment(self):
        # Arrange
        rows = [
            ("set", {"HOME": "/srv/homes/ada", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}),
            ("unset", {"HOME": "/srv/homes/ada"}),
        ]
        expected_addresses = {"set": "unix:path=/run/user/1000/bus", "unset": None}
        for case, environment in rows:
            with self.subTest(case=case):
                # Act
                paths = build_paths(environment)

                # Assert
                self.assertEqual(paths.session_bus_address, expected_addresses[case])
