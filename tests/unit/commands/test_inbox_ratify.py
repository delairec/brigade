import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import ANY

from brigade.commands.inbox_ratify import COMMAND
from brigade.errors import BrigadeError
from brigade.inbox.read_inbox import Signal, read_inbox
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    write_operational_corpus,
)
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_RECORDED
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime

CORPUS_CHANGE_OUTPUTS = {
    ("awawa", "fmt"): ProcessAnswer(),
    ("awawa", "lint"): ProcessAnswer(),
    ("git", "add"): ProcessAnswer(),
    ("git", "diff"): ProcessAnswer(exit_code=1),
    ("git", "commit"): ProcessAnswer(),
}
CART_TIMEOUT_TITLE = "the cart tests fail on a timeout"
NOTE_EVIDENCE = "note:474fa40ae4db the checkout test timed out"
THREAD_EVIDENCE = "rt:PRRT_kwDO the reviewer asked for a rename"


class InboxRatifyTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        self.config = self.root / "config"
        (self.config / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.repository = self.root / "shop"
        self.repository.mkdir()
        self.signals = self.root / "state" / "inbox" / "signals.jsonl"
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text(NOTE_ON_OAK_RECORDED + THREAD_RECORDED, encoding="utf-8")

    def _create_runtime(self, pattern_text: str, pattern_fields: tuple):
        (self.config / "patterns.awawa").write_text(pattern_text, encoding="utf-8")
        corpus = {
            "PATTERN": {"CartTimeouts": pattern_fields},
            "PROJECT": {"shop": (("PATH", str(self.repository)),)},
        }
        runner = ScriptedProcessRunner(CORPUS_CHANGE_OUTPUTS, fallback=create_corpus_double(corpus))
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=runner.run,
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

    def _create_wave_runtime(self):
        return self._create_runtime(
            "PATTERN CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tSTATUS new\n"
            '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
            '\tEVIDENCE "rt:PRRT_kwDO the reviewer asked for a rename"\n'
            "\tACTION wave\n"
            '\tTARGET "shop"\n',
            (
                ("TITLE", CART_TIMEOUT_TITLE),
                ("STATUS", "new"),
                ("EVIDENCE", NOTE_EVIDENCE),
                ("EVIDENCE", THREAD_EVIDENCE),
                ("ACTION", "wave"),
                ("TARGET", "shop"),
            ),
        )

    def _create_constraint_runtime(self):
        return self._create_runtime(
            "PATTERN CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tSTATUS new\n"
            '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
            "\tACTION constraint\n"
            '\tTARGET "shop"\n',
            (
                ("TITLE", CART_TIMEOUT_TITLE),
                ("STATUS", "new"),
                ("EVIDENCE", NOTE_EVIDENCE),
                ("ACTION", "constraint"),
                ("TARGET", "shop"),
            ),
        )

    def _create_order_runtime(self):
        return self._create_runtime(
            "PATTERN CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tSTATUS new\n"
            '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
            "\tACTION order\n"
            '\tRECIPE "flaky-tests"\n'
            '\tTARGET "shop"\n',
            (
                ("TITLE", CART_TIMEOUT_TITLE),
                ("STATUS", "new"),
                ("EVIDENCE", NOTE_EVIDENCE),
                ("ACTION", "order"),
                ("RECIPE", "flaky-tests"),
                ("TARGET", "shop"),
            ),
        )

    def _read_corpus_file(self, file_name: str) -> str:
        return (self.config / file_name).read_text(encoding="utf-8")

    def test_should_record_the_request_of_a_wave_from_the_pattern_and_launch_its_planner(self):
        # Arrange
        runtime = self._create_wave_runtime()

        # Act
        document = COMMAND.run(Namespace(pattern="CartTimeouts", kind=None), runtime)

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "pattern": "CartTimeouts", "action": "wave", "request": "shop_r1", "run": ANY},
        )
        self.assertEqual(
            self._read_corpus_file("requests.awawa"),
            (
                "REQUEST shop_r1\n"
                "\tPROJECT @PROJECT.shop\n"
                '\tTEXT "the cart tests fail on a timeout. Evidence: note:474fa40ae4db the checkout test timed out;'
                ' rt:PRRT_kwDO the reviewer asked for a rename"\n'
                '\tCREATED_AT "2026-10-19T09:00:00Z"\n'
                "\tSTATUS planning\n"
                "\tFROM @PATTERN.CartTimeouts\n"
            ),
        )

    def test_should_record_the_constraint_and_the_request_that_delivers_it(self):
        # Arrange
        runtime = self._create_constraint_runtime()

        # Act
        document = COMMAND.run(Namespace(pattern="CartTimeouts", kind="guard"), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "pattern": "CartTimeouts",
                "action": "constraint",
                "constraint": "CartTimeouts",
                "request": "shop_r1",
                "run": ANY,
            },
        )
        self.assertEqual(
            self._read_corpus_file("constraints.awawa"),
            "CONSTRAINT CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tKIND guard\n"
            "\tFROM @PATTERN.CartTimeouts\n"
            '\tTARGET "shop"\n'
            "\tSTATUS proposed\n",
        )
        self.assertEqual(
            self._read_corpus_file("requests.awawa"),
            (
                "REQUEST shop_r1\n"
                "\tPROJECT @PROJECT.shop\n"
                '\tTEXT "the cart tests fail on a timeout. Evidence: note:474fa40ae4db the checkout test timed out"\n'
                '\tCREATED_AT "2026-10-19T09:00:00Z"\n'
                "\tSTATUS planning\n"
                "\tFROM @PATTERN.CartTimeouts\n"
            ),
        )

    def test_should_record_the_order_of_the_recipe_on_the_project_of_the_target(self):
        # Arrange
        runtime = self._create_order_runtime()

        # Act
        document = COMMAND.run(Namespace(pattern="CartTimeouts", kind=None), runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "pattern": "CartTimeouts", "action": "order", "order": "CartTimeouts"}
        )
        self.assertEqual(
            self._read_corpus_file("orders.awawa"),
            'ORDER CartTimeouts\n\tRECIPE "flaky-tests"\n\tPROJECT @PROJECT.shop\n\tSTATUS active\n',
        )

    def test_should_set_the_pattern_ratified(self):
        # Arrange
        runtime = self._create_order_runtime()

        # Act
        COMMAND.run(Namespace(pattern="CartTimeouts", kind=None), runtime)

        # Assert
        self.assertEqual(
            self._read_corpus_file("patterns.awawa"),
            "PATTERN CartTimeouts\n"
            '\tTITLE "the cart tests fail on a timeout"\n'
            "\tSTATUS ratified\n"
            '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
            "\tACTION order\n"
            '\tRECIPE "flaky-tests"\n'
            '\tTARGET "shop"\n',
        )

    def test_should_dismiss_every_signal_the_evidence_of_the_pattern_cites(self):
        # Arrange
        runtime = self._create_wave_runtime()

        # Act
        COMMAND.run(Namespace(pattern="CartTimeouts", kind=None), runtime)

        # Assert
        self.assertEqual(
            read_inbox(runtime.paths.state_root, FIXED_NOW),
            (
                Signal(
                    id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                    fingerprint="note:474fa40ae4db",
                    kind="note",
                    project="oak",
                    count=1,
                    age_s=172800,
                    status="dismissed",
                    evidence={"text": "fix the flaky test"},
                ),
                Signal(
                    id=ANY,
                    fingerprint="rt:PRRT_kwDO",
                    kind="review_thread",
                    project=None,
                    count=1,
                    age_s=3600,
                    status="dismissed",
                    evidence={"pr": 12, "comment": "rename it"},
                ),
            ),
        )

    def test_should_record_the_ratification_in_the_ledger(self):
        # Arrange
        runtime = self._create_order_runtime()
        self.signals.unlink()

        # Act
        COMMAND.run(Namespace(pattern="CartTimeouts", kind=None), runtime)

        # Assert
        self.assertEqual(
            json.loads((self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8")),
            {"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "pattern.ratified", "project": "shop"},
        )


class InboxRatifyRefusalTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        self.config = self.root / "config"
        self.signals = self.root / "state" / "inbox" / "signals.jsonl"
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text(NOTE_ON_OAK_RECORDED, encoding="utf-8")

    def _ratify(self, pattern_fields: tuple, kind: str | None) -> BrigadeError:
        corpus = {"PATTERN": {"CartTimeouts": pattern_fields}, "PROJECT": {"shop": (("PATH", "/srv/shop"),)}}
        runner = ScriptedProcessRunner({}, fallback=create_corpus_double(corpus))
        runtime = create_test_runtime(create_test_paths(self.root), run_process=runner.run)
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pattern="CartTimeouts", kind=kind), runtime)
        return raised.exception

    def test_should_refuse_the_pattern_naming_it_and_write_nothing(self):
        # Arrange
        rows = [
            (
                "a pattern already ratified",
                (
                    ("TITLE", CART_TIMEOUT_TITLE),
                    ("STATUS", "ratified"),
                    ("EVIDENCE", NOTE_EVIDENCE),
                    ("ACTION", "wave"),
                    ("TARGET", "shop"),
                ),
                None,
                "@PATTERN.CartTimeouts is ratified: only a new pattern is ratified or dismissed",
            ),
            (
                "a pattern with no action",
                (("TITLE", CART_TIMEOUT_TITLE), ("STATUS", "new"), ("EVIDENCE", NOTE_EVIDENCE), ("TARGET", "shop")),
                None,
                "@PATTERN.CartTimeouts names no ACTION",
            ),
            (
                "a target naming no registered project",
                (
                    ("TITLE", CART_TIMEOUT_TITLE),
                    ("STATUS", "new"),
                    ("EVIDENCE", NOTE_EVIDENCE),
                    ("ACTION", "wave"),
                    ("TARGET", "garden"),
                ),
                None,
                "@PATTERN.CartTimeouts: its TARGET garden names no registered project",
            ),
            (
                "a pattern with no target",
                (("TITLE", CART_TIMEOUT_TITLE), ("STATUS", "new"), ("EVIDENCE", NOTE_EVIDENCE), ("ACTION", "wave")),
                None,
                "@PATTERN.CartTimeouts names no TARGET",
            ),
            (
                "an order with no recipe",
                (
                    ("TITLE", CART_TIMEOUT_TITLE),
                    ("STATUS", "new"),
                    ("EVIDENCE", NOTE_EVIDENCE),
                    ("ACTION", "order"),
                    ("TARGET", "shop"),
                ),
                None,
                "@PATTERN.CartTimeouts places an order and names no RECIPE",
            ),
            (
                "a constraint with no kind",
                (
                    ("TITLE", CART_TIMEOUT_TITLE),
                    ("STATUS", "new"),
                    ("EVIDENCE", NOTE_EVIDENCE),
                    ("ACTION", "constraint"),
                    ("TARGET", "shop"),
                ),
                None,
                "@PATTERN.CartTimeouts becomes a constraint: --kind names its KIND",
            ),
            (
                "a pattern proposing its own dismissal",
                (("TITLE", CART_TIMEOUT_TITLE), ("STATUS", "new"), ("EVIDENCE", NOTE_EVIDENCE), ("ACTION", "dismiss")),
                None,
                "@PATTERN.CartTimeouts proposes its dismissal: brigade inbox dismiss CartTimeouts",
            ),
        ]
        for case, pattern_fields, kind, expected in rows:
            with self.subTest(case=case):
                # Act
                refusal = self._ratify(pattern_fields, kind)

                # Assert
                self.assertEqual(str(refusal), expected)
                self.assertCountEqual(self.config.iterdir(), [self.config / "_schema.awawa"])
                self.assertEqual(self.signals.read_text(encoding="utf-8"), NOTE_ON_OAK_RECORDED)

    def test_should_refuse_a_pattern_the_operational_corpus_does_not_define(self):
        # Act
        refusal = self._ratify_unknown()

        # Assert
        self.assertEqual(str(refusal), "@PATTERN.Unknown is not defined in the operational corpus")

    def _ratify_unknown(self) -> BrigadeError:
        runner = ScriptedProcessRunner({}, fallback=create_corpus_double({}))
        runtime = create_test_runtime(create_test_paths(self.root), run_process=runner.run)
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pattern="Unknown", kind=None), runtime)
        return raised.exception


class InboxRatifyTextTest(unittest.TestCase):
    def test_should_name_what_the_pattern_became(self):
        # Arrange
        rows = [
            (
                "a wave",
                {"schema_version": 1, "pattern": "P", "action": "wave", "request": "shop_r1", "run": "R"},
                "@PATTERN.P ratified: @REQUEST.shop_r1 planning, run R\nbrigade runs show R --log",
            ),
            (
                "a constraint",
                {
                    "schema_version": 1,
                    "pattern": "P",
                    "action": "constraint",
                    "constraint": "P",
                    "request": "shop_r1",
                    "run": "R",
                },
                (
                    "@PATTERN.P ratified: @CONSTRAINT.P proposed, @REQUEST.shop_r1 planning, run R\n"
                    "brigade runs show R --log"
                ),
            ),
            (
                "an order",
                {"schema_version": 1, "pattern": "P", "action": "order", "order": "P"},
                "@PATTERN.P ratified: @ORDER.P active",
            ),
        ]
        for case, document, expected in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected)
