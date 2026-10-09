import unittest
from pathlib import Path

from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.system.read_configuration import Configuration

NO_ARGUMENTS = {}
NO_BRIEF = None
NO_WARNINGS = ()
NO_HANDOVER = 0


class RunPlanOfASlotBoundToALoginTest(unittest.TestCase):
    def test_should_keep_the_token_of_the_login_out_of_its_representation(self):
        # Arrange
        plan = RunPlan(
            run_id="20261009T120000Z-b75a01",
            run_directory=Path("/state/runs/20261009T120000Z-b75a01"),
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
            client_adapter=object(),
            configuration=Configuration(),
            project=None,
            cwd=Path("/project"),
            worktree=Path("/project"),
            disposable_worktree=False,
            capabilities=("read", "write"),
            wall_limit_s=1500.0,
            arguments=NO_ARGUMENTS,
            brief_path=None,
            brief=NO_BRIEF,
            counts_steps=True,
            reads_actions=False,
            handovers=NO_HANDOVER,
            warnings=NO_WARNINGS,
            forge_environment={"GH_TOKEN": "token-of-octo-builder"},
        )

        # Act
        representation = repr(plan)

        # Assert
        self.assertNotIn("token-of-octo-builder", representation)
