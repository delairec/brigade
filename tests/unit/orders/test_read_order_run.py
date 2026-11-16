import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.orders.read_order_run import read_order_run
from brigade.recipes.run_order import OrderRun
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

RUN_ID = "20261019T090000Z-aaaaaa"
ORDER_RECORD = {
    "schema_version": 1,
    "order": {
        "name": "nightly",
        "recipe": "triage",
        "project": "shop",
        "text": None,
        "params": [],
        "every": None,
        "output": None,
        "status": "active",
    },
    "recipe": {"name": "triage", "max_wall": 30, "steps": [{"kind": "judge", "answer": "RESULT"}]},
}


class ReadOrderRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        self.run_directory = self.runtime.paths.state_root / "runs" / RUN_ID

    def test_should_read_the_order_and_the_recipe_its_run_recorded(self):
        # Arrange
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "order.json").write_text(json.dumps(ORDER_RECORD), encoding="utf-8")

        # Act
        run = read_order_run(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(
            run,
            OrderRun(
                order="nightly",
                project="shop",
                recipe={"name": "triage", "max_wall": 30, "steps": [{"kind": "judge", "answer": "RESULT"}]},
                run_id=RUN_ID,
                run_directory=self.run_directory,
            ),
        )

    def test_should_refuse_a_run_that_is_not_of_an_order(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_order_run(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), f"{RUN_ID} is not a run of an order")
