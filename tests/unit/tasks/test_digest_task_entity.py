import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.tasks.digest_task_entity import digest_task_entity

STATUS_TODO = EntityField(name="STATUS", value="todo")


class DigestTaskEntityTest(unittest.TestCase):
    def test_should_digest_the_fields_of_the_task(self):
        # Arrange
        task = Entity(name="S3", fields=(STATUS_TODO,))

        # Act
        digest = digest_task_entity(task)

        # Assert
        self.assertEqual(digest, "21b807323b879dff2247378dd129efd4c59248cf48c93498e31ce3e7709eca31")

    def test_should_give_another_digest_to_a_task_worded_otherwise(self):
        # Arrange
        worded_otherwise = Entity(
            name="S3", fields=(STATUS_TODO, EntityField(name="SPEC", value="the forge is github"))
        )

        # Act
        digest = digest_task_entity(worded_otherwise)

        # Assert
        self.assertNotEqual(digest, "21b807323b879dff2247378dd129efd4c59248cf48c93498e31ce3e7709eca31")


if __name__ == "__main__":
    unittest.main()
