import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_card import render_awawa_card

BOARD_OF_THE_TASKS = AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK")))
NO_FACT = []
B1 = {
    "type": "TASK",
    "target": "@TASK.B1",
    "code": "B1",
    "label": "Read the corpus",
    "facts": NO_FACT,
    "status": "todo",
    "position": 1,
    "waiting": False,
    "file": "corpus/tasks.awawa",
    "line": 3,
    "ide_link": None,
}
MARKUP = '"><script>alert(1)</script>'


class RenderAwawaCardTest(unittest.TestCase):
    def test_should_show_the_code_and_the_label_linked_to_the_detail_of_the_entity(self):
        # Act
        fragment = render_awawa_card(B1, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(
            fragment,
            '<div class="awawa-card"><span class="dot tone-work" title="todo"></span>'
            '<a href="#awawa/oak?view=board&amp;type=TASK&amp;entity=%40TASK.B1">'
            '<span class="awawa-code">B1</span> <span class="awawa-label">Read the corpus</span></a></div>',
        )

    def test_should_dot_a_reference_of_its_facts_in_the_tone_of_the_status_of_its_target(self):
        # Arrange
        facts = [
            {
                "field": "MILESTONE",
                "values": [{"text": "Milestone one", "target": "@MILESTONE.M1", "status": "active"}],
            },
            {
                "field": "ROLE",
                "values": [
                    {"text": "ada", "target": None, "status": None},
                    {"text": "lex", "target": None, "status": None},
                ],
            },
        ]

        # Act
        fragment = render_awawa_card(B1 | {"facts": facts}, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<span class="awawa-facts"><span class="awawa-fact">MILESTONE'
            ' <span class="dot tone-work" title="active"></span>Milestone one</span>'
            '<span class="awawa-fact">ROLE ada, lex</span></span>',
            fragment,
        )

    def test_should_mark_an_entity_waiting_on_one_of_its_type(self):
        # Act
        fragment = render_awawa_card(B1 | {"waiting": True}, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<span class="awawa-waiting" title="waits on an entity of its type not past its status">waiting</span>',
            fragment,
        )

    def test_should_show_the_value_an_entity_of_the_others_column_holds(self):
        # Act
        fragment = render_awawa_card(B1 | {"value": "bilal"}, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn('<span class="awawa-value">bilal</span>', fragment)

    def test_should_dot_an_entity_without_status_in_the_neutral_tone(self):
        # Act
        fragment = render_awawa_card(B1 | {"status": None}, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn('<span class="dot tone-faint" title="no status"></span>', fragment)

    def test_should_escape_a_label_holding_markup(self):
        # Act
        fragment = render_awawa_card(B1 | {"label": MARKUP}, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn('<span class="awawa-label">&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;</span>', fragment)
