import unittest

from tests.guards.find_glossary_defects import GlossarySources, find_glossary_defects

SOURCES = GlossarySources(
    task_milestones={"B7": "M1", "B11": "M2", "B257": "M8"},
    command_paths=[("doctor",), ("wave", "show")],
    schema_words=["POLICY", "POLICY.REPAIR_ROUNDS"],
    carried_text="a wave is a batch of ratified tasks recorded in the ledger",
)


class FindGlossaryDefectsTest(unittest.TestCase):
    def test_should_accept_a_table_holding_every_word_with_the_task_that_delivers_it(self):
        # Arrange
        page = (
            "What each word of brigade means.\n\n"
            "<!-- glossary: begin -->\n"
            "| Word | Kind | What it is | Page | Milestone | Task |\n"
            "|---|---|---|---|---|---|\n"
            "| `brigade doctor` | command | inspect the prerequisites | [Install](Install.md) | M1 | B7 |\n"
            "| `brigade wave show` | command | print a wave | [Waves](Waves.md) | M2 | B11 |\n"
            "| `POLICY` | entity | how brigade acts on a project | [Tick](Tick.md) | M8 | B257 |\n"
            "| `POLICY.REPAIR_ROUNDS` | field | the repair rounds of a task | [Review](Review.md) | M8 | B257 |\n"
            "| wave | concept | a batch of ratified tasks | [Waves](Waves.md) | M2 | B11 |\n"
            "<!-- glossary: end -->\n"
        )

        # Act
        defects = find_glossary_defects(page, SOURCES)

        # Assert
        self.assertEqual(defects, [])

    def test_should_flag_a_row_citing_a_task_the_corpus_lacks(self):
        # Arrange
        page = (
            "<!-- glossary: begin -->\n"
            "| wave | concept | a batch of ratified tasks | [Waves](Waves.md) | M2 | B999 |\n"
            "<!-- glossary: end -->\n"
        )

        # Act
        defects = find_glossary_defects(page, SOURCES)

        # Assert
        self.assertIn("the row wave of wiki/Glossary.md cites @TASK.B999, which the corpus lacks", defects)

    def test_should_flag_a_milestone_that_is_not_the_milestone_of_its_task(self):
        # Arrange
        page = (
            "<!-- glossary: begin -->\n"
            "| wave | concept | a batch of ratified tasks | [Waves](Waves.md) | M8 | B11 |\n"
            "<!-- glossary: end -->\n"
        )

        # Act
        defects = find_glossary_defects(page, SOURCES)

        # Assert
        self.assertIn("the row wave of wiki/Glossary.md names M8, where @TASK.B11 is of M2", defects)

    def test_should_flag_a_command_group_or_a_subcommand_without_a_row(self):
        for kind, path, defect in [
            ("command group", ("doctor",), "brigade doctor has no row in wiki/Glossary.md"),
            ("subcommand", ("wave", "show"), "brigade wave show has no row in wiki/Glossary.md"),
        ]:
            with self.subTest(kind=kind):
                # Arrange
                page_without_command = "<!-- glossary: begin -->\n<!-- glossary: end -->\n"
                sources = GlossarySources(task_milestones={}, command_paths=[path], schema_words=[], carried_text="")

                # Act
                defects = find_glossary_defects(page_without_command, sources)

                # Assert
                self.assertEqual(defects, [defect])

    def test_should_flag_an_entity_or_a_field_of_the_schema_without_a_row(self):
        for kind, word in [("entity", "POLICY"), ("field", "POLICY.REPAIR_ROUNDS")]:
            with self.subTest(kind=kind):
                # Arrange
                page_without_schema_word = "<!-- glossary: begin -->\n<!-- glossary: end -->\n"
                sources = GlossarySources(task_milestones={}, command_paths=[], schema_words=[word], carried_text="")

                # Act
                defects = find_glossary_defects(page_without_schema_word, sources)

                # Assert
                self.assertEqual(defects, [f"{word} has no row in wiki/Glossary.md"])

    def test_should_flag_a_row_naming_a_word_neither_the_code_nor_the_corpus_carries(self):
        for kind, row, defect in [
            (
                "command",
                "| `brigade wave plan` | command | plan a wave | [Waves](Waves.md) | M2 | B11 |",
                "the row brigade wave plan of wiki/Glossary.md names a word neither the code nor the corpus carries",
            ),
            (
                "field",
                "| `POLICY.VERIFY_ROUNDS` | field | the rounds | [Review](Review.md) | M8 | B257 |",
                "the row POLICY.VERIFY_ROUNDS of wiki/Glossary.md names a word neither the code nor the corpus carries",
            ),
            (
                "concept",
                "| verification | concept | the review | [Review](Review.md) | M8 | B257 |",
                "the row verification of wiki/Glossary.md names a word neither the code nor the corpus carries",
            ),
        ]:
            with self.subTest(kind=kind):
                # Arrange
                page = f"<!-- glossary: begin -->\n{row}\n<!-- glossary: end -->\n"

                # Act
                defects = find_glossary_defects(page, SOURCES)

                # Assert
                self.assertIn(defect, defects)

    def test_should_read_an_escaped_bar_as_part_of_its_cell(self):
        # Arrange
        page = (
            "<!-- glossary: begin -->\n"
            "| `POLICY` | entity | `ask\\|auto` | [Tick](Tick.md) | M8 | B257 |\n"
            "<!-- glossary: end -->\n"
        )
        sources = GlossarySources(
            task_milestones={"B257": "M8"}, command_paths=[], schema_words=["POLICY"], carried_text=""
        )

        # Act
        defects = find_glossary_defects(page, sources)

        # Assert
        self.assertEqual(defects, [])

    def test_should_flag_a_concept_the_code_carries_only_inside_a_longer_word(self):
        for side, word in [("start", "atified"), ("end", "ratif")]:
            with self.subTest(side=side):
                # Arrange
                page = (
                    "<!-- glossary: begin -->\n"
                    f"| {word} | concept | a part of a word | [Inbox](Inbox.md) | M2 | B11 |\n"
                    "<!-- glossary: end -->\n"
                )

                # Act
                defects = find_glossary_defects(page, SOURCES)

                # Assert
                self.assertIn(
                    f"the row {word} of wiki/Glossary.md names a word neither the code nor the corpus carries", defects
                )

    def test_should_read_no_row_outside_the_markers(self):
        # Arrange
        page_with_a_table_before_the_markers = (
            "| verification | concept | the review | [Review](Review.md) | M8 | B999 |\n"
            "<!-- glossary: begin -->\n"
            "<!-- glossary: end -->\n"
        )
        sources_without_words = GlossarySources(task_milestones={}, command_paths=[], schema_words=[], carried_text="")

        # Act
        defects = find_glossary_defects(page_with_a_table_before_the_markers, sources_without_words)

        # Assert
        self.assertEqual(defects, [])
