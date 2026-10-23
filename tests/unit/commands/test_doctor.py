import argparse
import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.doctor import COMMAND, doctor
from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from brigade.errors import ToolFailure, ToolNotFound
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_runtime
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

GIT_ANSWERS = {
    ("git", "for-each-ref"): ProcessAnswer(stdout="*\tde446f3\torigin/main\n"),
    ("git", "rev-parse"): ProcessAnswer(stdout="8885daa\n"),
    ("git", "rev-list"): ProcessAnswer(stdout="1\t0\n"),
}
CONFIGURATION = (
    'client = "scripted"\ninstructions = "/srv/instructions"\n'
    '[slot_clients]\nreview = "other"\n'
    '[forge_accounts]\ncli = "ada-bot"\nbuild = "ada-bot"\nreview = "rev-bot"\n'
)
PROBE = {
    "schema_version": 1,
    "client": "scripted",
    "version_argv": ["scripted", "--version"],
    "operations": ["probe", "launch", "result"],
    "features": ["step_count"],
    "models": {},
}
POLICIES = json.dumps({"entities": [{"type": "POLICY", "name": "p1"}, {"type": "POLICY", "name": "p2"}]})
APPROVAL_POLICY = json.dumps(
    {"fields": [{"name": "PROJECT", "atoms": ["@PROJECT.app"]}, {"name": "REVIEW", "atoms": ["approval"]}]}
)
COMMENT_POLICY = json.dumps(
    {"fields": [{"name": "PROJECT", "atoms": ["@PROJECT.lib"]}, {"name": "REVIEW", "atoms": ["comment"]}]}
)
TOKEN = {"GH_TOKEN": "t0k3n"}


class ScriptedForgeDouble:
    def __init__(self, environments: dict, account):
        self.environments = environments
        self.account = account

    def read_login_environment(self, request: dict, runtime) -> dict:
        environment = self.environments[request["login"]]
        if isinstance(environment, Exception):
            raise environment
        return {"schema_version": 1, "environment": environment}

    def describe_account(self, request: dict, runtime) -> dict:
        if isinstance(self.account, Exception):
            raise self.account
        return {"schema_version": 1, "login": self.account}


def _create_doctor_answers() -> dict:
    return {
        ("git", "--version"): ProcessAnswer(stdout="git version 2.47.0\n"),
        ("awawa", "--version"): ProcessAnswer(stdout="awawa 2.8.1\n"),
        ("scripted", "--version"): ProcessAnswer(stdout="scripted 1.4.2\nbuild 5\n"),
        ("systemctl",): ProcessAnswer(stdout="running\n"),
        ("awawa-web",): ProcessAnswer(),
        ("awawa", "lint"): ProcessAnswer(),
        ("git", "for-each-ref"): ProcessAnswer(),
        ("awawa", "status", "POLICY"): ProcessAnswer(stdout=POLICIES),
        ("awawa", "show", "@POLICY.p1"): ProcessAnswer(stdout=APPROVAL_POLICY),
        ("awawa", "show", "@POLICY.p2"): ProcessAnswer(stdout=COMMENT_POLICY),
    }


class DoctorTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.answers = _create_doctor_answers()
        self.probe = dict(PROBE)
        self.forge = ScriptedForgeDouble({"ada-bot": TOKEN, "rev-bot": TOKEN}, "ada-bot")
        plugins = {("client", "scripted"): ScriptedClient({"probe": self.probe}), ("forge", "github"): self.forge}
        self.runtime = create_runtime(
            Path(self.root.name),
            run_process=ScriptedProcessRunner(self.answers).run,
            resolve_plugin=create_plugin_resolver(plugins),
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.no_option = argparse.Namespace()

    def configure(self, text: str) -> None:
        self.runtime.paths.configuration_file.write_text(text)


class DoctorPrerequisitesTest(DoctorTestCase):
    def test_should_check_git(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ToolNotFound("git"), "finding", "not on PATH"),
            (ProcessAnswer(stdout="git version 2.47.0\n"), "ok", "2.47.0 (no floor)"),
        ]
        for answer, state, detail in rows:
            with self.subTest(detail=detail):
                self.answers["git", "--version"] = answer

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {"name": "git", "kind": "prerequisite", "state": state, "detail": detail, "fallback": None},
                    document["items"],
                )

    def test_should_check_awawa_against_its_floor(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ToolNotFound("awawa"), "finding", "not on PATH (floor 2.7)"),
            (ProcessAnswer(stdout="awawa dev\n"), "finding", "dev (floor 2.7)"),
            (ProcessAnswer(stdout="awawa 2.6.0\n"), "finding", "2.6.0 (floor 2.7)"),
            (ProcessAnswer(stdout="awawa 2.8.1\n"), "ok", "2.8.1 (floor 2.7)"),
        ]
        for answer, state, detail in rows:
            with self.subTest(detail=detail):
                self.answers["awawa", "--version"] = answer

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {"name": "awawa", "kind": "prerequisite", "state": state, "detail": detail, "fallback": None},
                    document["items"],
                )

    def test_should_check_the_executable_of_the_configured_client(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ProcessAnswer(stdout="scripted 1.4.2\nbuild 5\n"), "ok", "scripted: scripted 1.4.2"),
            (
                ToolFailure("scripted --version timed out after 10 s"),
                "finding",
                "scripted: scripted --version timed out after 10 s",
            ),
        ]
        for answer, state, detail in rows:
            with self.subTest(detail=detail):
                self.answers["scripted", "--version"] = answer

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {"name": "client", "kind": "prerequisite", "state": state, "detail": detail, "fallback": None},
                    document["items"],
                )

    def test_should_accept_a_client_with_no_executable(self):
        # Arrange
        self.configure(CONFIGURATION)
        self.probe["version_argv"] = None

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(
            {
                "name": "client",
                "kind": "prerequisite",
                "state": "ok",
                "detail": "scripted: no client executable",
                "fallback": None,
            },
            document["items"],
        )

    def test_should_find_no_client_without_a_configuration(self):
        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(
            {
                "name": "client",
                "kind": "prerequisite",
                "state": "finding",
                "detail": f"no configuration at {self.runtime.paths.configuration_file}; run brigade init",
                "fallback": None,
            },
            document["items"],
        )

    def test_should_report_each_finding_of_the_configuration(self):
        # Arrange
        self.configure("journal_poll_s = 0\n" + CONFIGURATION)

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(
            {
                "name": "config",
                "kind": "prerequisite",
                "state": "finding",
                "detail": f"journal_poll_s is 0, not a positive number, in {self.runtime.paths.configuration_file};"
                " the default of 2 s holds",
                "fallback": None,
            },
            document["items"],
        )


class DoctorSchedulerTest(DoctorTestCase):
    def test_should_check_the_user_systemd_instance(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ToolNotFound("systemctl"), "warning", "systemctl not on PATH"),
            (ProcessAnswer(stdout="running\n"), "ok", "user systemd instance running"),
            (ProcessAnswer(stdout=""), "warning", "no user systemd instance"),
            (ProcessAnswer(stdout="offline\n"), "warning", "no user systemd instance (offline)"),
        ]
        for answer, state, detail in rows:
            with self.subTest(detail=detail):
                self.answers["systemctl",] = answer

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {
                        "name": "scheduler",
                        "kind": "optional",
                        "state": state,
                        "detail": detail,
                        "fallback": "a cron line, or brigade tick --loop",
                    },
                    document["items"],
                )


class DoctorForgeTest(DoctorTestCase):
    def test_should_check_the_forge_as_the_cli_login(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ToolNotFound("gh"), "ada-bot", "warning", "gh not on PATH"),
            (None, "ada-bot", "warning", "gh printed no token for ada-bot"),
            (TOKEN, ToolNotFound("gh"), "warning", "gh not on PATH"),
            (TOKEN, None, "warning", "gh logged in to no account"),
            (TOKEN, "ada-bot", "ok", "gh as ada-bot"),
        ]
        for environment, account, state, detail in rows:
            with self.subTest(detail=detail, account=account):
                self.forge.environments["ada-bot"] = environment
                self.forge.account = account

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {
                        "name": "forge",
                        "kind": "optional",
                        "state": state,
                        "detail": detail,
                        "fallback": "local mode without a forge",
                    },
                    document["items"],
                )

    def test_should_check_the_forge_unbound_when_no_cli_login_is_configured(self):
        # Arrange
        self.configure('client = "scripted"\n')
        self.forge.account = "octocat"

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(
            {
                "name": "forge",
                "kind": "optional",
                "state": "ok",
                "detail": "gh as octocat",
                "fallback": "local mode without a forge",
            },
            document["items"],
        )

    def test_should_check_each_login_with_the_keys_bound_to_it(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ToolNotFound("gh"), "warning", "gh not on PATH for rev-bot, bound to review"),
            (None, "warning", "gh printed no token for rev-bot, bound to review"),
            (TOKEN, "ok", "rev-bot for review"),
        ]
        for environment, state, detail in rows:
            with self.subTest(detail=detail):
                self.forge.environments["rev-bot"] = environment

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {
                        "name": "forge login",
                        "kind": "optional",
                        "state": state,
                        "detail": detail,
                        "fallback": "the commands acting as it stop",
                    },
                    document["items"],
                )


class DoctorOfAnUnreadableConfigurationTest(DoctorTestCase):
    def test_should_warn_with_the_error_wherever_the_configuration_is_read(self):
        # Arrange
        self.configure('colour = "blue"\n')
        self.runtime.paths.schema_file.write_text("SCHEMA POLICY\n")
        error = f"unknown key colour in {self.runtime.paths.configuration_file}"
        rows = [
            ("forge", error, "local mode without a forge"),
            ("forge login", error, "the commands acting as it stop"),
            ("review", error, "the review mode of each project unchecked"),
            ("instructions", error, "built-in roles and no instructions package"),
        ]

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        for name, detail, fallback in rows:
            with self.subTest(name=name):
                self.assertIn(
                    {"name": name, "kind": "optional", "state": "warning", "detail": detail, "fallback": fallback},
                    document["items"],
                )

    def test_should_name_no_client_and_no_slot_client(self):
        # Arrange
        self.configure('colour = "blue"\n')

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertEqual((document["client"], document["slot_clients"]), (None, {}))


class DoctorClientsTest(DoctorTestCase):
    def test_should_name_the_client_and_the_slots_bound_to_another(self):
        # Arrange
        self.configure(CONFIGURATION)

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertEqual((document["client"], document["slot_clients"]), ("scripted", {"review": "other"}))


class DoctorReviewTest(DoctorTestCase):
    def setUp(self):
        super().setUp()
        self.configure('client = "scripted"\n[forge_accounts]\nbuild = "ada-bot"\nreview = "ada-bot"\n')
        self.approval_warning = {
            "name": "review",
            "kind": "optional",
            "state": "warning",
            "detail": "app reviews by approval without distinct logins for build and review",
            "fallback": "GitHub refuses the approval of the review slot",
        }

    def test_should_warn_of_a_project_reviewed_by_approval_without_distinct_logins(self):
        # Arrange
        self.runtime.paths.schema_file.write_text("SCHEMA POLICY\n")

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(self.approval_warning, document["items"])

    def test_should_not_read_the_policies_with_distinct_logins(self):
        # Arrange
        self.runtime.paths.schema_file.write_text("SCHEMA POLICY\n")
        self.configure(CONFIGURATION)

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertNotIn(self.approval_warning, document["items"])

    def test_should_not_read_the_policies_without_the_operational_corpus(self):
        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertNotIn(self.approval_warning, document["items"])

    def test_should_warn_that_the_policies_are_unreadable(self):
        # Arrange
        self.runtime.paths.schema_file.write_text("SCHEMA POLICY\n")
        self.answers["awawa", "status", "POLICY"] = ToolFailure("awawa status POLICY timed out after 30 s")

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(
            {
                "name": "review",
                "kind": "optional",
                "state": "warning",
                "detail": "POLICY unreadable: awawa status POLICY timed out after 30 s",
                "fallback": "the review mode of each project unchecked",
            },
            document["items"],
        )


class DoctorAwawaWebTest(DoctorTestCase):
    def test_should_check_awawa_web_on_the_path(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [(ToolNotFound("awawa-web"), "warning", "not on PATH"), (ProcessAnswer(), "ok", "on PATH")]
        for answer, state, detail in rows:
            with self.subTest(detail=detail):
                self.answers["awawa-web",] = answer

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {
                        "name": "awawa-web",
                        "kind": "optional",
                        "state": state,
                        "detail": detail,
                        "fallback": "the dashboard's corpus view only",
                    },
                    document["items"],
                )


class DoctorInstructionsTest(DoctorTestCase):
    def test_should_lint_the_instructions_configured(self):
        # Arrange
        self.configure(CONFIGURATION)
        rows = [
            (ProcessAnswer(), "ok", "lint --strict clean in /srv/instructions"),
            (ProcessAnswer(exit_code=1), "warning", "lint --strict fails in /srv/instructions"),
            (ToolFailure("awawa lint timed out after 30 s"), "warning", "awawa lint timed out after 30 s"),
        ]
        for answer, state, detail in rows:
            with self.subTest(detail=detail):
                self.answers["awawa", "lint"] = answer

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {
                        "name": "instructions",
                        "kind": "optional",
                        "state": state,
                        "detail": detail,
                        "fallback": "built-in roles and no instructions package",
                    },
                    document["items"],
                )

    def test_should_warn_that_no_instructions_are_configured(self):
        # Arrange
        rows = [("without a configuration", None), ("with a configuration naming none", 'client = "scripted"\n')]
        for case, configuration in rows:
            with self.subTest(case=case):
                if configuration is not None:
                    self.configure(configuration)

                # Act
                document = doctor(self.no_option, self.runtime)

                # Assert
                self.assertIn(
                    {
                        "name": "instructions",
                        "kind": "optional",
                        "state": "warning",
                        "detail": "none configured",
                        "fallback": "built-in roles and no instructions package",
                    },
                    document["items"],
                )


class DoctorStepsTest(DoctorTestCase):
    def setUp(self):
        super().setUp()
        self.configure(CONFIGURATION)
        self.steps_warning = {
            "name": "steps",
            "kind": "optional",
            "state": "warning",
            "detail": "scripted counts no steps: the budget is held on the clock and the run cut at its limit",
            "fallback": "the wall-time limit of each run",
        }

    def test_should_warn_of_a_client_that_counts_no_steps(self):
        # Arrange
        self.probe["features"] = []

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(self.steps_warning, document["items"])

    def test_should_not_warn_of_a_client_counting_steps(self):
        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertNotIn(self.steps_warning, document["items"])


class DoctorSchemaTest(DoctorTestCase):
    def setUp(self):
        super().setUp()
        self.configure(CONFIGURATION)
        self.schema_warning = {
            "name": "schema",
            "kind": "optional",
            "state": "warning",
            "detail": f"{self.runtime.paths.schema_file} differs from the shipped schema",
            "fallback": "throw the operational corpus away, then run brigade init",
        }

    def test_should_warn_of_a_schema_that_differs_from_the_shipped_one(self):
        # Arrange
        self.runtime.paths.schema_file.write_text("SCHEMA POLICY\n")

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertIn(self.schema_warning, document["items"])

    def test_should_not_warn_of_the_shipped_schema(self):
        # Arrange
        self.runtime.paths.schema_file.write_bytes(SHIPPED_SCHEMA.read_bytes())

        # Act
        document = doctor(self.no_option, self.runtime)

        # Assert
        self.assertNotIn(self.schema_warning, document["items"])


class DoctorCheckOfACheckoutTest(DoctorTestCase):
    def test_should_warn_that_the_checkout_is_behind_its_upstream(self):
        # Arrange
        self.configure(CONFIGURATION)
        checkout = Path(self.root.name).resolve() / "checkout"
        (checkout / "brigade").mkdir(parents=True)
        paths = dataclasses.replace(self.runtime.paths, package_file=checkout / "brigade" / "__init__.py")
        runtime = dataclasses.replace(self.runtime, paths=paths)
        self.answers.update(GIT_ANSWERS)

        # Act
        document = doctor(self.no_option, runtime)

        # Assert
        self.assertIn(
            {
                "name": "checkout",
                "kind": "optional",
                "state": "warning",
                "detail": f"{checkout} at de446f3, 1 behind origin/main at 8885daa",
                "fallback": "git pull in the checkout",
            },
            document["items"],
        )


class DoctorRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(json=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(json=True))


class DoctorExitCodeTest(unittest.TestCase):
    def test_should_exit_1_on_a_finding_and_0_otherwise(self):
        # Arrange
        rows = [("finding", 1), ("warning", 0)]
        for state, expected in rows:
            with self.subTest(state=state):
                document = {"items": [{"name": "git", "kind": "prerequisite", "state": state}]}

                # Act
                exit_code = COMMAND.decide_exit_code(document)

                # Assert
                self.assertEqual(exit_code, expected)


class DoctorTextTest(unittest.TestCase):
    def test_should_print_the_prerequisites_the_optional_items_and_the_count_of_fallbacks(self):
        # Arrange
        document = {
            "slot_clients": {"review": "other"},
            "items": [
                {"name": "python", "kind": "prerequisite", "state": "ok", "detail": "3.11.4", "fallback": None},
                {"name": "awawa", "kind": "prerequisite", "state": "finding", "detail": "dev", "fallback": None},
                {"name": "scheduler", "kind": "optional", "state": "ok", "detail": "running", "fallback": "cron"},
                {"name": "awawa-web", "kind": "optional", "state": "warning", "detail": "absent", "fallback": "none"},
                {"name": "forge", "kind": "optional", "state": "warning", "detail": "no gh", "fallback": "local"},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "prerequisites\n"
            "ok       python       3.11.4\n"
            "finding  awawa        dev\n"
            "optional\n"
            "ok       scheduler    running                             else: cron\n"
            "warning  awawa-web    absent                              fallback: none\n"
            "warning  forge        no gh                               fallback: local\n"
            "slot review runs on other\n"
            "\n"
            "doctor: 1 of 2 prerequisites ok · 2 optional items on their fallback",
        )

    def test_should_count_a_single_optional_item_on_its_fallback(self):
        # Arrange
        document = {
            "slot_clients": {},
            "items": [
                {"name": "forge", "kind": "optional", "state": "warning", "detail": "no gh", "fallback": "local"}
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "prerequisites\n"
            "optional\n"
            "warning  forge        no gh                               fallback: local\n"
            "\n"
            "doctor: 0 of 0 prerequisites ok · 1 optional item on its fallback",
        )
