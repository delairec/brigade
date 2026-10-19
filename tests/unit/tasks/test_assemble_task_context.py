import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import CommandFailed
from brigade.system.read_configuration import Configuration
from brigade.tasks.assemble_task_context import assemble_task_context
from brigade.tasks.locate_task_worktree import TaskWorktree
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

PROJECT = Entity(
    name="oak",
    fields=(
        EntityField(name="PATH", value="/srv/oak"),
        EntityField(name="ACCEPTANCE", value="python3 -m unittest"),
        EntityField(name="HEAVY", value="npm run e2e"),
    ),
)
ATTRIBUTION = ["Co-Authored-By: Ada <ada@example.org>"]
TASK_SHOWN = {
    "fields": [
        {"name": "SPEC", "atoms": ['"edit brigade/parse.py, then docs."'], "fields": []},
        {"name": "DONE", "atoms": ['"x"'], "fields": [{"name": "IMPL", "atoms": ['"tests/test_parse.py::Parse"']}]},
    ]
}


class AssembleTaskContextTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.worktree_path = self.root / "oak-b12"
        self.worktree_path.mkdir()
        self.worktree = TaskWorktree(
            path=self.worktree_path, task="B12", project=PROJECT, wave={"branch": "integration/f0-parser"}
        )
        self.instructions = self.root / "instructions"
        self.processes = ScriptedProcesses()
        self.processes.answer(("git", "merge-base", "--is-ancestor", "integration/f0-parser", "HEAD"))
        self.processes.answer(("awawa", "context", "@TASK.B12", "--with-schema", "."), stdout="TASK B12\n")
        self.processes.answer(("awawa", "lint", "--closure", "@TASK.B12", "."), exit_code=1, stderr="L001\n")

    def script_wave_tree(self, runtime) -> None:
        self.processes.answer_entities(runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "integration/f0-parser^{commit}"),
            stdout="c0ffee\n",
        )
        tree = self.root / "cache" / "refs" / "oak" / "c0ffee"
        tree.mkdir(parents=True)
        self.processes.answer_json(
            ("awawa", "status", "--json", str(tree)),
            {"entities": [{"type": "TASK", "name": "B12"}, {"type": "TASK", "name": "B15"}]},
        )

    def script_rules(self) -> None:
        instructions = str(self.instructions)
        self.processes.answer_json(("awawa", "show", "@TASK.B12", "--json", str(self.worktree_path)), TASK_SHOWN)
        self.processes.answer_json(
            ("awawa", "status", "TRIGGER", "--where", "KIND==path", "--json", instructions),
            {
                "entities": [
                    {"name": "python_file", "file": "triggers.awawa", "line": 9},
                    {"name": "docs_file", "file": "triggers.awawa", "line": 3},
                ]
            },
        )
        self.processes.answer_entity(self.instructions, "TRIGGER", "python_file", (("GLOB", "**/*.py"),))
        self.processes.answer_entity(self.instructions, "TRIGGER", "docs_file", (("GLOB", "docs/**"),))
        self.processes.answer(
            ("awawa", "context", "@TRIGGER.python_file", "--depth", "1", "--skip", "reasoning", instructions),
            stdout="RULE python\n",
        )

    def test_should_assemble_what_a_run_needs_to_deliver_the_task(self):
        # Arrange
        runtime = create_scripted_runtime(self.root, self.processes)
        self.script_wave_tree(runtime)

        # Act
        context = assemble_task_context(runtime, Configuration(), self.worktree, ATTRIBUTION)

        # Assert
        self.assertEqual(
            context,
            {
                "worktree": {
                    "ancestry": {"command": "git merge-base --is-ancestor integration/f0-parser HEAD", "exit_code": 0},
                    "setup": None,
                },
                "task": [
                    {
                        "command": "awawa context @TASK.B12 --with-schema .",
                        "exit_code": 0,
                        "stderr": "",
                        "output": "TASK B12\n",
                    },
                    {"command": "awawa lint --closure @TASK.B12 .", "exit_code": 1, "stderr": "L001\n", "output": ""},
                ],
                "rules": None,
                "project": None,
                "acceptance": {"acceptance": ["python3 -m unittest"], "heavy": ["npm run e2e"]},
                "reserved": {"task_number": 16, "temporary_directory": None, "attribution": ATTRIBUTION},
                "when_done": ["brigade task check", "brigade task pr", "brigade task promote"],
            },
        )

    def test_should_carry_the_rules_of_the_path_triggers_matching_a_path_the_task_names(self):
        # Arrange
        runtime = create_scripted_runtime(self.root, self.processes)
        self.script_wave_tree(runtime)
        self.script_rules()
        configuration = Configuration(instructions=str(self.instructions))

        # Act
        context = assemble_task_context(runtime, configuration, self.worktree, ATTRIBUTION)

        # Assert
        self.assertEqual(
            context["rules"],
            [
                {
                    "trigger": "python_file",
                    "command": f"awawa context @TRIGGER.python_file --depth 1 --skip reasoning {self.instructions}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": "RULE python\n",
                }
            ],
        )

    def test_should_carry_the_setup_log_and_the_project_instructions_of_the_worktree(self):
        # Arrange
        runtime = create_scripted_runtime(self.root, self.processes)
        self.script_wave_tree(runtime)
        setup_log = self.root / "state" / "setups" / "oak" / "B12.log"
        setup_log.parent.mkdir(parents=True)
        setup_log.write_text("npm ci\n", encoding="utf-8")
        (self.worktree_path / "AGENTS.md").write_text("# oak\n", encoding="utf-8")

        # Act
        context = assemble_task_context(runtime, Configuration(), self.worktree, ATTRIBUTION)

        # Assert
        self.assertEqual((context["worktree"]["setup"], context["project"]), ("npm ci\n", "# oak\n"))

    def test_should_reserve_a_temporary_directory_in_the_run_directory_of_a_run(self):
        # Arrange
        runtime = create_scripted_runtime(self.root, self.processes, run_directory=self.root / "run")
        self.script_wave_tree(runtime)

        # Act
        context = assemble_task_context(runtime, Configuration(), self.worktree, ATTRIBUTION)

        # Assert
        self.assertEqual(
            (context["reserved"]["temporary_directory"], (self.root / "run" / "tmp").is_dir()),
            (str(self.root / "run" / "tmp"), True),
        )

    def test_should_fail_when_the_context_of_the_task_cannot_be_read(self):
        # Arrange
        self.processes.answer(
            ("awawa", "context", "@TASK.B12", "--with-schema", "."), exit_code=1, stderr="@TASK.B12 is not defined\n"
        )
        runtime = create_scripted_runtime(self.root, self.processes)

        # Act
        with self.assertRaises(CommandFailed) as refusal:
            assemble_task_context(runtime, Configuration(), self.worktree, ATTRIBUTION)

        # Assert
        self.assertEqual(
            str(refusal.exception), "awawa context @TASK.B12 --with-schema . exited 1: @TASK.B12 is not defined"
        )
