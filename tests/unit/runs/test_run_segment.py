import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.runs.run_result import RunResult
from brigade.runs.run_segment import run_segment
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.read_configuration import Configuration
from brigade.system.trail_writer import TrailWriter

FIRST_SEGMENT = 1
NO_PATH_NEEDED = ""
NO_ARGUMENTS = {}
NO_BRIEF = None
NO_WARNINGS = ()
NO_HANDOVER = 0
LAUNCH_ANSWER = {
    "schema_version": 1,
    "argv": ["double-client", "--print"],
    "environment": {"DOUBLE_CLIENT_MODE": "unattended"},
    "stdin": "the brief of the run",
}


class ClientDouble:
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "launch-argv":
            return LAUNCH_ANSWER
        return {
            "schema_version": 1,
            "outcome": "done",
            "steps": 12,
            "usage": None,
            "session_id": "session-b73",
            "duration_ms": 4200,
            "error_class": None,
            "reset": None,
            "message": request["stdout"],
        }


class ExitedProcessDouble:
    pid = 4242

    def wait(self, **_limit) -> int:
        return 0


class SpawnDouble:
    def __init__(self):
        self.requests = []

    def spawn(self, request):
        self.requests.append(request)
        request.stdout.write_text("the client finished the task", encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        return ExitedProcessDouble()


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"run_segment ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"run_segment resolved the {kind} plugin {name}")


def _create_runtime(root: Path, spawn: SpawnDouble) -> Runtime:
    return Runtime(
        run_process=_refuse_process,
        spawn_process=spawn.spawn,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
        ),
        now=datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC),
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


def _create_plan(root: Path) -> RunPlan:
    return RunPlan(
        run_id="20261007T090000Z-b73a01",
        run_directory=root / "state" / "runs" / "20261007T090000Z-b73a01",
        procedure=Procedure(
            name="deliver",
            location="built-in",
            argument="deliver",
            capabilities=("read", "write"),
            budget=40,
            body="Deliver the task.",
        ),
        slot="build",
        role=ResolvedRole(
            slot="build",
            role="builder",
            source="built-in",
            front_matter={"reasoning": "standard"},
            body="You build.",
        ),
        client="double-client",
        client_adapter=ClientDouble(),
        configuration=Configuration(),
        project=None,
        cwd=root / "project",
        worktree=root / "project",
        disposable_worktree=False,
        capabilities=("read", "write"),
        wall_limit_s=1500.0,
        arguments=NO_ARGUMENTS,
        brief_path=None,
        brief=NO_BRIEF,
        counts_steps=True,
        handovers=NO_HANDOVER,
        warnings=NO_WARNINGS,
    )


class RunSegmentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawn = SpawnDouble()

    def test_should_spawn_in_the_worktree_the_command_the_client_answers(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn))

        # Assert
        [request] = self.spawn.requests
        progress_file = str(self.root / "state" / "runs" / "20261007T090000Z-b73a01" / "progress.md")
        self.assertEqual(request.argv, ("double-client", "--print"))
        self.assertEqual(request.cwd, str(self.root / "project"))
        self.assertEqual(
            request.environment, {"DOUBLE_CLIENT_MODE": "unattended", "BRIGADE_PROGRESS_FILE": progress_file}
        )
        self.assertEqual(request.stdin, "the brief of the run")

    def test_should_return_the_result_the_client_parses_from_what_the_process_wrote(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn))

        # Assert
        self.assertEqual(record.number, 1)
        self.assertEqual(record.exit_code, 0)
        self.assertEqual(
            record.result,
            RunResult(
                outcome="done",
                steps=12,
                usage=None,
                session_id="session-b73",
                duration_ms=4200,
                error_class=None,
                reset=None,
                message="the client finished the task",
            ),
        )
