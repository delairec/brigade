import json
import tempfile
import unittest
from pathlib import Path

from brigade.triage.deliver_patterns import WaveDelivery, deliver_patterns
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    write_operational_corpus,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

CORPUS_CHANGE_OUTPUTS = {
    ("awawa", "fmt"): ProcessAnswer(),
    ("awawa", "lint"): ProcessAnswer(),
    ("git", "add"): ProcessAnswer(),
    ("git", "diff"): ProcessAnswer(exit_code=1),
    ("git", "commit"): ProcessAnswer(),
}
PATTERNS_TEXT = (
    "PATTERN CartTimeouts\n"
    '\tTITLE "the cart tests fail on a timeout"\n'
    "\tSTATUS ratified\n"
    '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
    "\tACTION constraint\n"
    '\tTARGET "shop"\n'
)
CONSTRAINTS_TEXT = (
    "CONSTRAINT CartTimeouts\n"
    '\tTITLE "the cart tests fail on a timeout"\n'
    "\tKIND guard\n"
    "\tFROM @PATTERN.CartTimeouts\n"
    '\tTARGET "shop"\n'
    "\tSTATUS proposed\n"
)
CART_TIMEOUTS_REQUEST = (
    ("PROJECT", "@PROJECT.shop"),
    ("TEXT", "the cart tests fail on a timeout. Evidence: note:474fa40ae4db the checkout test timed out"),
    ("STATUS", "planned"),
    ("MILESTONE", "M4"),
    ("FROM", "@PATTERN.CartTimeouts"),
)
CART_TIMEOUTS_CONSTRAINT = (("FROM", "@PATTERN.CartTimeouts"), ("STATUS", "proposed"))


class DeliverPatternsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        self.config = self.root / "config"
        (self.config / "patterns.awawa").write_text(PATTERNS_TEXT, encoding="utf-8")

    def _create_runtime(self, corpus: dict):
        runner = ScriptedProcessRunner(CORPUS_CHANGE_OUTPUTS, fallback=create_corpus_double(corpus))
        return create_test_runtime(create_test_paths(self.root), run_process=runner.run)

    def _read_corpus_file(self, file_name: str) -> str:
        return (self.config / file_name).read_text(encoding="utf-8")

    def test_should_deliver_the_pattern_and_the_constraint_of_a_request_the_wave_delivers(self):
        # Arrange
        (self.config / "constraints.awawa").write_text(CONSTRAINTS_TEXT, encoding="utf-8")
        runtime = self._create_runtime(
            {
                "REQUEST": {"shop_r1": CART_TIMEOUTS_REQUEST},
                "CONSTRAINT": {"CartTimeouts": CART_TIMEOUTS_CONSTRAINT},
            }
        )

        # Act
        deliver_patterns(runtime, WaveDelivery(project="shop", milestones=("M4",)))

        # Assert
        self.assertEqual(
            self._read_corpus_file("patterns.awawa"),
            "PATTERN CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tSTATUS delivered\n"
            '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
            "\tACTION constraint\n"
            '\tTARGET "shop"\n',
        )
        self.assertEqual(
            self._read_corpus_file("constraints.awawa"),
            "CONSTRAINT CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tKIND guard\n"
            "\tFROM @PATTERN.CartTimeouts\n"
            '\tTARGET "shop"\n'
            "\tSTATUS delivered\n",
        )

    def test_should_record_each_constraint_delivered_in_the_ledger(self):
        # Arrange
        (self.config / "constraints.awawa").write_text(CONSTRAINTS_TEXT, encoding="utf-8")
        runtime = self._create_runtime(
            {
                "REQUEST": {"shop_r1": CART_TIMEOUTS_REQUEST},
                "CONSTRAINT": {"CartTimeouts": CART_TIMEOUTS_CONSTRAINT},
            }
        )

        # Act
        deliver_patterns(runtime, WaveDelivery(project="shop", milestones=("M4",)))

        # Assert
        self.assertEqual(
            json.loads((self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8")),
            {"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "constraint.delivered", "project": "shop"},
        )

    def test_should_deliver_the_pattern_of_a_wave_request_that_no_constraint_comes_from(self):
        # Arrange
        no_constraint = {}
        runtime = self._create_runtime({"REQUEST": {"shop_r1": CART_TIMEOUTS_REQUEST}, "CONSTRAINT": no_constraint})

        # Act
        deliver_patterns(runtime, WaveDelivery(project="shop", milestones=("M4",)))

        # Assert
        self.assertEqual(
            self._read_corpus_file("patterns.awawa"),
            "PATTERN CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tSTATUS delivered\n"
            '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
            "\tACTION constraint\n"
            '\tTARGET "shop"\n',
        )

    def test_should_write_no_constraint_file_for_a_pattern_that_no_constraint_comes_from(self):
        # Arrange
        no_constraint = {}
        runtime = self._create_runtime({"REQUEST": {"shop_r1": CART_TIMEOUTS_REQUEST}, "CONSTRAINT": no_constraint})

        # Act
        deliver_patterns(runtime, WaveDelivery(project="shop", milestones=("M4",)))

        # Assert
        self.assertFalse((self.config / "constraints.awawa").exists())

    def test_should_leave_the_pattern_of_a_request_the_wave_does_not_deliver(self):
        for case, project, milestones in [
            ("another milestone", "shop", ("M5",)),
            ("another project", "oak", ("M4",)),
        ]:
            with self.subTest(case=case):
                # Arrange
                runtime = self._create_runtime({"REQUEST": {"shop_r1": CART_TIMEOUTS_REQUEST}})

                # Act
                deliver_patterns(runtime, WaveDelivery(project=project, milestones=milestones))

                # Assert
                self.assertEqual(
                    self._read_corpus_file("patterns.awawa"),
                    "PATTERN CartTimeouts\n"
                    '\tTITLE "the cart tests fail on a timeout"\n'
                    "\tSTATUS ratified\n"
                    '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
                    "\tACTION constraint\n"
                    '\tTARGET "shop"\n',
                )
