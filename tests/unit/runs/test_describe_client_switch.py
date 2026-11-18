import dataclasses
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.ledger.run_client_switched import RunClientSwitched
from brigade.runs.describe_client_switch import describe_client_switch
from brigade.system.parse_configuration import Configuration, Fallback, ReasoningRow
from tests.unit.runs.create_run_plan import RUN_ID, create_run_plan

CONFIGURATION = Configuration(
    client="claude-code",
    reasoning={"standard": ReasoningRow(model="opus", effort="high")},
    fallback=Fallback(client="vibe", reasoning={"standard": ReasoningRow(model="devstral", effort="high")}),
)
CONFIGURATION_WITHOUT_FALLBACK = Configuration(
    client="claude-code", reasoning={"standard": ReasoningRow(model="opus", effort="high")}
)
NEW_RUN = None


class DescribeClientSwitchTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def create_plan(self, client: str, reasoning: dict, **changes):
        plan = create_run_plan(self.root, client=client, **changes)
        role = dataclasses.replace(plan.role, front_matter={**plan.role.front_matter, "reasoning": "standard"})
        configuration = dataclasses.replace(CONFIGURATION, reasoning=reasoning)
        return dataclasses.replace(plan, role=role, configuration=configuration)


class DescribeClientSwitchToTheFallbackTest(DescribeClientSwitchTestCase):
    def test_should_describe_a_new_run_launched_on_the_fallback(self):
        # Arrange
        plan = self.create_plan("vibe", CONFIGURATION.fallback.reasoning, on_fallback=True, resumed_client=NEW_RUN)

        # Act
        switch = describe_client_switch(plan, "claude-code", CONFIGURATION)

        # Assert
        self.assertEqual(
            switch,
            RunClientSwitched(
                run=RUN_ID,
                client_left="claude-code",
                model_left="opus",
                client_taken="vibe",
                model_taken="devstral",
                reason="rate_limit",
            ),
        )

    def test_should_describe_no_switch_for_a_run_resumed_on_the_fallback_it_already_ran_on(self):
        # Arrange
        plan = self.create_plan("vibe", CONFIGURATION.fallback.reasoning, on_fallback=True, resumed_client="vibe")

        # Act
        switch = describe_client_switch(plan, "claude-code", CONFIGURATION)

        # Assert
        self.assertIsNone(switch)


class DescribeClientSwitchBackToTheClientTest(DescribeClientSwitchTestCase):
    def test_should_describe_a_run_resumed_on_the_client_after_the_fallback(self):
        # Arrange
        plan = self.create_plan("claude-code", CONFIGURATION.reasoning, resumed_client="vibe")

        # Act
        switch = describe_client_switch(plan, "claude-code", CONFIGURATION)

        # Assert
        self.assertEqual(
            switch,
            RunClientSwitched(
                run=RUN_ID,
                client_left="vibe",
                model_left="devstral",
                client_taken="claude-code",
                model_taken="opus",
                reason="reset",
            ),
        )

    def test_should_describe_no_switch_for_a_run_that_stays_on_the_client(self):
        # Arrange
        plan = self.create_plan("claude-code", CONFIGURATION.reasoning, resumed_client="claude-code")

        # Act
        switch = describe_client_switch(plan, "claude-code", CONFIGURATION)

        # Assert
        self.assertIsNone(switch)

    def test_should_describe_no_switch_for_a_run_resumed_after_a_client_no_fallback_names(self):
        # Arrange
        plan = self.create_plan("claude-code", CONFIGURATION.reasoning, resumed_client="vibe")

        # Act
        switch = describe_client_switch(plan, "claude-code", CONFIGURATION_WITHOUT_FALLBACK)

        # Assert
        self.assertIsNone(switch)

    def test_should_describe_no_switch_for_a_run_resumed_after_a_client_the_fallback_does_not_name(self):
        # Arrange
        plan = self.create_plan("claude-code", CONFIGURATION.reasoning, resumed_client="codex")

        # Act
        switch = describe_client_switch(plan, "claude-code", CONFIGURATION)

        # Assert
        self.assertIsNone(switch)
