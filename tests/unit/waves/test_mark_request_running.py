import unittest

from brigade.waves.mark_request_running import mark_request_running

REQUESTS = (
    "REQUEST oak_1\n"
    "\tPROJECT @PROJECT.oak\n"
    "\tSTATUS planned\n"
    "\n"
    "REQUEST oak_2\n"
    "\tPROJECT @PROJECT.oak\n"
    "\tSTATUS planned\n"
)


class MarkRequestRunningTest(unittest.TestCase):
    def test_should_mark_the_named_request_running_and_leave_the_others(self):
        # Act
        marked = mark_request_running(REQUESTS, "oak_2")

        # Assert
        self.assertEqual(
            marked,
            "REQUEST oak_1\n"
            "\tPROJECT @PROJECT.oak\n"
            "\tSTATUS planned\n"
            "\n"
            "REQUEST oak_2\n"
            "\tPROJECT @PROJECT.oak\n"
            "\tSTATUS running\n",
        )
