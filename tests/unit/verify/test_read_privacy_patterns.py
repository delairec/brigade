import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.verify.check_privacy import PrivacyPatterns
from brigade.verify.read_privacy_patterns import read_privacy_patterns


class ReadPrivacyPatternsTest(unittest.TestCase):
    def test_should_read_every_private_and_public_pattern_of_the_project(self):
        # Arrange
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="PRIVATE", value="oak-internal"),
                EntityField(name="PATH", value="/srv/oak"),
                EntityField(name="PUBLIC", value="/home/alice"),
                EntityField(name="PRIVATE", value="acme-corp"),
            ),
        )

        # Act
        patterns = read_privacy_patterns(project)

        # Assert
        self.assertEqual(patterns, PrivacyPatterns(private=("oak-internal", "acme-corp"), public=("/home/alice",)))
