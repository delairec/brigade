import unittest

from brigade.list_command_modules import list_command_modules
from brigade.select_command_modules import select_command_modules

COMMAND_MODULES = [
    "adapter_launch_argv",
    "corpus",
    "corpus_awawa",
    "ledger",
    "ledger_budgets",
    "run",
    "runs_list",
    "runs_show",
]


class SelectCommandModulesTest(unittest.TestCase):
    def test_should_select_the_module_of_the_command_line(self):
        # Arrange
        rows = [
            ("a command of its own", ["run", "awawa-task", "--slot", "build", "task=@TASK.X"], ["run"]),
            ("an action of a group", ["runs", "list"], ["runs_list"]),
            ("a hyphenated action", ["adapter", "launch-argv"], ["adapter_launch_argv"]),
            ("a group that is a command", ["ledger", "--json"], ["ledger"]),
            ("an action of that group", ["ledger", "budgets"], ["ledger_budgets"]),
            ("the common options first", ["--json", "--verbose", "runs", "show", "20261019-abc"], ["runs_show"]),
            ("the value of an option", ["runs", "list", "--wave", "w1"], ["runs_list"]),
            ("a command line given no --", ["corpus", "--project", "brigade"], ["corpus"]),
        ]
        for case, arguments, expected_modules in rows:
            with self.subTest(case=case):
                # Act
                modules = select_command_modules(arguments, COMMAND_MODULES)

                # Assert
                self.assertEqual(modules, expected_modules)

    def test_should_add_the_passthrough_of_a_command_line_given_its_separator(self):
        # Arrange
        arguments = ["corpus", "--project", "brigade", "--", "status", "."]

        # Act
        modules = select_command_modules(arguments, COMMAND_MODULES)

        # Assert
        self.assertEqual(modules, ["corpus", "corpus_awawa"])

    def test_should_select_none_for_arguments_naming_no_command_line(self):
        # Arrange
        rows = [
            ("the version", ["--version", "--json"]),
            ("the help", ["--help"]),
            ("a group alone", ["runs"]),
            ("an unknown command", ["frobnicate", "list"]),
            ("the words after the separator", ["--", "runs", "list"]),
        ]
        for case, arguments in rows:
            with self.subTest(case=case):
                # Act
                modules = select_command_modules(arguments, COMMAND_MODULES)

                # Assert
                self.assertEqual(modules, [])


class SelectCommandModulesOfThePackageTest(unittest.TestCase):
    def test_should_select_the_one_module_of_each_command_line_the_help_lists(self):
        # Arrange
        module_names = list_command_modules()
        rows = [
            (["adapter", "actions"], ["adapter_actions"]),
            (["adapter", "launch-argv"], ["adapter_launch_argv"]),
            (["adapter", "matrix"], ["adapter_matrix"]),
            (["adapter", "parse-result"], ["adapter_parse_result"]),
            (["adapter", "probe"], ["adapter_probe"]),
            (["adapter", "resume-argv"], ["adapter_resume_argv"]),
            (["adapter", "transcripts"], ["adapter_transcripts"]),
            (["collect"], ["collect"]),
            (["collectors", "list"], ["collectors_list"]),
            (["corpus"], ["corpus"]),
            (["doctor"], ["doctor"]),
            (["init"], ["init"]),
            (["ledger"], ["ledger"]),
            (["ledger", "budgets"], ["ledger_budgets"]),
            (["ledger", "compare"], ["ledger_compare"]),
            (["plan", "context"], ["plan_context"]),
            (["plan", "record"], ["plan_record"]),
            (["processes", "list"], ["processes_list"]),
            (["processes", "show"], ["processes_show"]),
            (["project", "add"], ["project_add"]),
            (["project", "list"], ["project_list"]),
            (["project", "pause"], ["project_pause"]),
            (["project", "resume"], ["project_resume"]),
            (["project", "show"], ["project_show"]),
            (["request", "cancel"], ["request_cancel"]),
            (["request", "list"], ["request_list"]),
            (["request", "new"], ["request_new"]),
            (["request", "show"], ["request_show"]),
            (["roles", "lint"], ["roles_lint"]),
            (["roles", "list"], ["roles_list"]),
            (["roles", "show"], ["roles_show"]),
            (["run"], ["run"]),
            (["runs", "list"], ["runs_list"]),
            (["runs", "prune"], ["runs_prune"]),
            (["runs", "show"], ["runs_show"]),
            (["runs", "stop"], ["runs_stop"]),
            (["scheduler", "install"], ["scheduler_install"]),
            (["scheduler", "status"], ["scheduler_status"]),
            (["study", "answer"], ["study_answer"]),
            (["study", "context"], ["study_context"]),
            (["study", "list"], ["study_list"]),
            (["study", "new"], ["study_new"]),
            (["study", "pause"], ["study_pause"]),
            (["study", "resume"], ["study_resume"]),
            (["study", "run"], ["study_run"]),
            (["study", "show"], ["study_show"]),
            (["task", "check"], ["task_check"]),
            (["task", "context"], ["task_context"]),
            (["task", "pr"], ["task_pr"]),
            (["task", "promote"], ["task_promote"]),
            (["tick"], ["tick"]),
            (["verify", "preflight"], ["verify_preflight"]),
            (["wave", "cancel"], ["wave_cancel"]),
            (["wave", "list"], ["wave_list"]),
            (["wave", "requeue"], ["wave_requeue"]),
            (["wave", "resume"], ["wave_resume"]),
            (["wave", "show"], ["wave_show"]),
            (["wave", "start"], ["wave_start"]),
        ]
        for arguments, expected_modules in rows:
            with self.subTest(command=" ".join(arguments)):
                # Act
                modules = select_command_modules(arguments, module_names)

                # Assert
                self.assertEqual(modules, expected_modules)
