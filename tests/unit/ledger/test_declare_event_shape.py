import unittest
from dataclasses import dataclass
from typing import ClassVar

from brigade.ledger.declare_event_shape import declare_event_shape
from brigade.system.validate_document import Field


@dataclass(frozen=True)
class SampleEvent:
    name: ClassVar[str] = "sample.event"
    run: str
    steps: int | None
    cost_usd: float | None = None


class DeclareEventShapeTest(unittest.TestCase):
    def test_should_require_every_field_without_default_of_any_kind_and_nullable(self):
        # Act
        shape = declare_event_shape(SampleEvent)

        # Assert
        self.assertEqual(
            shape,
            {
                "run": Field((bool, int, float, str, list, dict), nullable=True),
                "steps": Field((bool, int, float, str, list, dict), nullable=True),
            },
        )
