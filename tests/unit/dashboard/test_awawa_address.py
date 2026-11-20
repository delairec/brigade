import unittest

from brigade.dashboard.awawa_address import AwawaAddress

BOARD_OF_THE_TODO_TASKS = AwawaAddress(
    project="oak", parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=todo"))
)


class AwawaAddressTest(unittest.TestCase):
    def test_should_link_the_tab_of_the_project_with_its_parameters(self):
        # Act
        link = BOARD_OF_THE_TODO_TASKS.link()

        # Assert
        self.assertEqual(link, "#awawa/oak?view=board&type=TASK&filter=STATUS%3Dtodo")

    def test_should_link_the_tab_alone_when_the_address_carries_no_parameter(self):
        # Arrange
        address = AwawaAddress(project="my oak")

        # Act
        link = address.link()

        # Assert
        self.assertEqual(link, "#awawa/my%20oak")

    def test_should_read_the_first_value_of_a_parameter_and_nothing_for_an_absent_one(self):
        # Act
        read = (BOARD_OF_THE_TODO_TASKS.read("type"), BOARD_OF_THE_TODO_TASKS.read("search"))

        # Assert
        self.assertEqual(read, ("TASK", None))

    def test_should_replace_every_value_of_the_parameter_it_sets(self):
        # Act
        address = BOARD_OF_THE_TODO_TASKS.setting("type", "MILESTONE")

        # Assert
        self.assertEqual(
            address,
            AwawaAddress(
                project="oak", parameters=(("view", "board"), ("filter", "STATUS=todo"), ("type", "MILESTONE"))
            ),
        )

    def test_should_add_a_value_beside_the_values_of_the_parameter(self):
        # Act
        address = BOARD_OF_THE_TODO_TASKS.adding("filter", "ROLE=ada")

        # Assert
        self.assertEqual(address.read_all("filter"), ("STATUS=todo", "ROLE=ada"))

    def test_should_remove_one_value_of_a_parameter(self):
        # Act
        address = BOARD_OF_THE_TODO_TASKS.removing("filter", "STATUS=todo")

        # Assert
        self.assertEqual(address, AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK"))))

    def test_should_remove_every_value_of_a_parameter(self):
        # Act
        address = BOARD_OF_THE_TODO_TASKS.removing("type")

        # Assert
        self.assertEqual(
            address, AwawaAddress(project="oak", parameters=(("view", "board"), ("filter", "STATUS=todo")))
        )
