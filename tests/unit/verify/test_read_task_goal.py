import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.verify.read_task_goal import read_task_goal
from tests.unit.commands.command_runtime import create_corpus_double

HEAD_TREE = Path("/cache/refs/tidepool/8885daa")
TIDE_TABLES = (
    ("TITLE", "Tide tables"),
    ("SUBJECT", "print the tide tables of a harbour"),
    ("STATUS", "active"),
    ("DESC", "a sailor reads the tides of the week at a glance"),
    ("DESC", "drawn from the harbour mockup, page by page"),
    ("SOURCE", "the user's words: I want the tides of the week on one page"),
)


class ReadTaskGoalOfATaskOfAMilestoneTest(unittest.TestCase):
    def test_should_give_the_title_of_the_task_and_the_goal_its_milestone_states_in_the_users_words(self):
        # Arrange
        task = Entity(
            name="T7",
            fields=(
                EntityField(name="TITLE", value="Print the tide table of the week"),
                EntityField(name="MILESTONE", value="@MILESTONE.M4"),
            ),
        )
        run_process = create_corpus_double({"MILESTONE": {"M4": TIDE_TABLES}})

        # Act
        goal = read_task_goal(run_process, HEAD_TREE, task)

        # Assert
        self.assertEqual(
            goal,
            {
                "task": "T7",
                "title": "Print the tide table of the week",
                "milestone": {
                    "name": "M4",
                    "title": "Tide tables",
                    "subject": "print the tide tables of a harbour",
                    "desc": [
                        "a sailor reads the tides of the week at a glance",
                        "drawn from the harbour mockup, page by page",
                    ],
                    "source": ["the user's words: I want the tides of the week on one page"],
                },
            },
        )

    def test_should_give_no_subject_no_description_and_no_source_its_milestone_does_not_state(self):
        # Arrange
        task = Entity(
            name="T7",
            fields=(
                EntityField(name="TITLE", value="Print the tide table of the week"),
                EntityField(name="MILESTONE", value="@MILESTONE.M4"),
            ),
        )
        run_process = create_corpus_double({"MILESTONE": {"M4": (("TITLE", "Tide tables"), ("STATUS", "active"))}})

        # Act
        goal = read_task_goal(run_process, HEAD_TREE, task)

        # Assert
        self.assertEqual(
            goal["milestone"], {"name": "M4", "title": "Tide tables", "subject": None, "desc": [], "source": []}
        )


class ReadTaskGoalOfATaskOfNoMilestoneTest(unittest.TestCase):
    def test_should_give_the_title_of_the_task_as_its_own_goal_and_no_milestone(self):
        # Arrange
        task = Entity(name="T9", fields=(EntityField(name="TITLE", value="Fix the harbour name"),))
        empty_corpus = create_corpus_double({})

        # Act
        goal = read_task_goal(empty_corpus, HEAD_TREE, task)

        # Assert
        self.assertEqual(goal, {"task": "T9", "title": "Fix the harbour name", "milestone": None})
