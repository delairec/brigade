import unittest

from brigade.registry.describe_remote import RemoteDescription, describe_remote


class DescribeRemoteTest(unittest.TestCase):
    def test_should_name_the_owner_and_the_repository_and_tell_the_forge(self):
        rows = [
            ("https://github.com/acme/app.git", RemoteDescription(remote="acme/app", forge="github")),
            ("https://github.com/acme/app", RemoteDescription(remote="acme/app", forge="github")),
            ("git@github.com:acme/app.git", RemoteDescription(remote="acme/app", forge="github")),
            ("ssh://git@github.com/acme/app.git", RemoteDescription(remote="acme/app", forge="github")),
            ("https://gitlab.com/group/app.git", RemoteDescription(remote="group/app", forge="none")),
            ("git@gitlab.example.org:group/app.git", RemoteDescription(remote="group/app", forge="none")),
            ("/srv/mirrors/acme/app.git", RemoteDescription(remote="acme/app", forge="none")),
        ]
        for url, expected in rows:
            with self.subTest(url=url):
                # Act
                description = describe_remote(url)

                # Assert
                self.assertEqual(description, expected)

    def test_should_tell_no_forge_without_an_origin_remote(self):
        # Arrange
        no_origin = None

        # Act
        description = describe_remote(no_origin)

        # Assert
        self.assertEqual(description, RemoteDescription(remote=None, forge="none"))
