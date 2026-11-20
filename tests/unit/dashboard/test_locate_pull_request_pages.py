import unittest

from brigade.dashboard.locate_pull_request_pages import locate_pull_request_pages

NO_PAGE = None


def create_project(fields: list[dict]) -> dict:
    return {"schema_version": 1, "project": {"name": "oak", "fields": fields}}


class LocatePullRequestPagesTest(unittest.TestCase):
    def test_should_give_the_pull_request_pages_of_the_forge_the_project_names(self):
        # Arrange
        project = create_project([{"name": "FORGE", "value": "github"}, {"name": "REMOTE", "value": "alice/oak"}])

        # Act
        pages = locate_pull_request_pages(project)

        # Assert
        self.assertEqual(pages, "https://github.com/alice/oak/pull/")

    def test_should_give_no_page_when_the_project_names_no_known_forge_or_no_remote(self):
        # Arrange
        rows = [
            (
                "a forge brigade does not know",
                [{"name": "FORGE", "value": "gitea"}, {"name": "REMOTE", "value": "alice/oak"}],
            ),
            ("a known forge without a remote", [{"name": "FORGE", "value": "github"}]),
        ]
        for case, fields in rows:
            with self.subTest(case=case):
                # Act
                pages = locate_pull_request_pages(create_project(fields))

                # Assert
                self.assertEqual(pages, NO_PAGE)
