import unittest
from pathlib import Path

from brigade.collecting.collect_document import Collection
from brigade.recipes.create_collect_performer import create_collect_performer
from brigade.recipes.run_order import OrderRun

FAILING_TESTS_STEP = {"kind": "collect", "collector": "failing-tests", "parameters": {"branch": "{branch}"}}
OPEN_ISSUES_STEP = {"kind": "collect", "collector": "open-issues"}
NIGHTLY_RUN = OrderRun(
    order="nightly",
    project="shop",
    recipe={
        "name": "triage",
        "steps": [{"kind": "command", "argv": ["make", "test"]}, FAILING_TESTS_STEP, OPEN_ISSUES_STEP],
    },
    run_id="20261019T090000Z-aaaaaa",
    run_directory=Path("/srv/runs/20261019T090000Z-aaaaaa"),
)


class CollectorDouble:
    def __init__(self, collection: Collection):
        self.collection = collection
        self.collections: list[tuple[str, dict, Path]] = []

    def collect(self, name: str, parameters: dict, place: Path) -> Collection:
        self.collections.append((name, parameters, place))
        return self.collection


class CreateCollectPerformerTest(unittest.TestCase):
    def test_should_keep_the_summary_and_the_document_of_the_collector_the_step_names(self):
        # Arrange
        collector = CollectorDouble(
            Collection(
                document_path=Path("/srv/runs/20261019T090000Z-aaaaaa/collectors/2/collection.json"),
                document={"summary": {"failing": 3}, "items": []},
                cached=False,
            )
        )
        perform = create_collect_performer(collector.collect, {"branch": "main"})

        # Act
        result = perform(FAILING_TESTS_STEP, NIGHTLY_RUN)

        # Assert
        self.assertEqual(
            result,
            {
                "collector": "failing-tests",
                "summary": {"failing": 3},
                "collection": "/srv/runs/20261019T090000Z-aaaaaa/collectors/2/collection.json",
            },
        )

    def test_should_collect_with_the_values_of_the_order_into_the_place_of_the_rank_of_the_step(self):
        # Arrange
        collector = CollectorDouble(
            Collection(document_path=Path("/srv/collection.json"), document={"summary": {}}, cached=False)
        )
        perform = create_collect_performer(collector.collect, {"branch": "main"})

        # Act
        perform(FAILING_TESTS_STEP, NIGHTLY_RUN)

        # Assert
        self.assertEqual(
            collector.collections,
            [("failing-tests", {"branch": "main"}, Path("/srv/runs/20261019T090000Z-aaaaaa/collectors/2"))],
        )

    def test_should_collect_with_no_parameters_for_a_step_that_declares_none(self):
        # Arrange
        collector = CollectorDouble(
            Collection(document_path=Path("/srv/collection.json"), document={"summary": {}}, cached=False)
        )
        perform = create_collect_performer(collector.collect, {"branch": "main"})

        # Act
        perform(OPEN_ISSUES_STEP, NIGHTLY_RUN)

        # Assert
        self.assertEqual(
            collector.collections, [("open-issues", {}, Path("/srv/runs/20261019T090000Z-aaaaaa/collectors/3"))]
        )
