import unittest

from brigade.commands import order_cancel, order_pause, order_resume


class OrderStatusTextTest(unittest.TestCase):
    def test_should_say_whether_the_status_of_the_order_changed(self):
        # Arrange
        rows = [
            ("an order paused", order_pause.COMMAND, "paused", True, "paused @ORDER.nightly"),
            ("an order already paused", order_pause.COMMAND, "paused", False, "@ORDER.nightly is already paused"),
            ("an order cancelled", order_cancel.COMMAND, "archived", True, "cancelled @ORDER.nightly"),
            (
                "an order already cancelled",
                order_cancel.COMMAND,
                "archived",
                False,
                "@ORDER.nightly is already archived",
            ),
            ("an order resumed", order_resume.COMMAND, "active", True, "resumed @ORDER.nightly"),
            ("an order already active", order_resume.COMMAND, "active", False, "@ORDER.nightly is already active"),
        ]
        for case, command, status, changed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = command.render_text(
                    {"schema_version": 1, "order": "nightly", "status": status, "changed": changed}
                )

                # Assert
                self.assertEqual(text, expected_text)
