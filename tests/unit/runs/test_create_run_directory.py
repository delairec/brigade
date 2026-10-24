import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.runs.create_run_directory import create_run_directory
from brigade.runs.read_run_pid import read_run_pid
from brigade.system.read_process_identity import read_process_identity
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.runs.create_run_plan import RUN_ID, create_run_plan


class CreateRunDirectoryTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root))


class CreateRunDirectoryOfANewRunTest(CreateRunDirectoryTestCase):
    def test_should_record_the_run_its_role_and_its_progress_file(self):
        # Arrange
        plan = create_run_plan(self.root, project="tidepool", wave="w1", task="TP1")

        # Act
        create_run_directory(plan, self.runtime)

        # Assert
        self.assertEqual(
            json.loads((plan.run_directory / "run.json").read_text()),
            {
                "schema_version": 1,
                "run": RUN_ID,
                "procedure": "build-task",
                "procedure_path": "built-in",
                "slot": "build",
                "role": "builder",
                "role_source": "built-in",
                "client": "fake",
                "project": "tidepool",
                "cwd": str(self.root / "project"),
                "worktree": str(self.root / "project"),
                "capabilities": ["read", "write"],
                "budget": 40,
                "wall_limit_s": 1500.0,
                "arguments": {},
                "wave": "w1",
                "task": "TP1",
                "brief": None,
            },
        )
        self.assertCountEqual(
            plan.run_directory.iterdir(),
            [
                plan.run_directory / "pid",
                plan.run_directory / "progress.md",
                plan.run_directory / "role.md",
                plan.run_directory / "run.json",
            ],
        )

    def test_should_record_the_path_of_the_brief_of_the_run(self):
        # Arrange
        plan = create_run_plan(self.root, brief_path=self.root / "briefs" / "shop_w1-S3.md")

        # Act
        create_run_directory(plan, self.runtime)

        # Assert
        self.assertEqual(
            json.loads((plan.run_directory / "run.json").read_text())["brief"],
            str(self.root / "briefs" / "shop_w1-S3.md"),
        )

    def test_should_record_the_process_holding_the_run(self):
        # Arrange
        plan = create_run_plan(self.root)

        # Act
        create_run_directory(plan, self.runtime)

        # Assert
        self.assertEqual(read_run_pid(plan.run_directory), (os.getpid(), read_process_identity(os.getpid())))


class CreateRunDirectoryOfAResumedRunTest(CreateRunDirectoryTestCase):
    def test_should_drop_the_result_of_the_run_and_record_its_new_process(self):
        # Arrange
        brief = self.root / "brief.md"
        plan = create_run_plan(self.root, resumed=True, brief_path=brief)
        plan.run_directory.mkdir(parents=True)
        (plan.run_directory / "result.json").write_text("{}")

        # Act
        create_run_directory(plan, self.runtime)

        # Assert
        self.assertCountEqual(plan.run_directory.iterdir(), [plan.run_directory / "pid"])
        self.assertEqual(read_run_pid(plan.run_directory).pid, os.getpid())
