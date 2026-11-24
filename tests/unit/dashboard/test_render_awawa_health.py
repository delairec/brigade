import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_health import render_awawa_health
from tests.unit.dashboard.test_render_awawa_card import B1

HEALTH_OF_OAK = AwawaAddress(project="oak", parameters=(("view", "health"),))
NO_AILING = []
HEALTH = {
    "view": "health",
    "errors": 2,
    "warnings": 1,
    "unresolved": 3,
    "entities": [
        {
            "entity": B1,
            "diagnostics": [
                {"rule": "L001", "severity": "error", "file": "corpus/tasks.awawa", "line": 3, "message": "<b>bad</b>"}
            ],
        }
    ],
    "files": [
        {
            "file": "corpus/old.awawa",
            "diagnostics": [
                {"rule": "L010", "severity": "warning", "file": "corpus/old.awawa", "line": 1, "message": "unused"}
            ],
        }
    ],
}


class RenderAwawaHealthTest(unittest.TestCase):
    def test_should_count_the_errors_the_warnings_and_the_unresolved_references(self):
        # Act
        fragment = render_awawa_health(HEALTH, HEALTH_OF_OAK)

        # Assert
        self.assertIn(
            '<div class="awawa-health"><dl class="awawa-counts"><div><dt>Errors</dt><dd>2</dd></div>'
            "<div><dt>Warnings</dt><dd>1</dd></div><div><dt>Unresolved references</dt><dd>3</dd></div></dl>",
            fragment,
        )

    def test_should_list_the_diagnostics_of_an_entity_below_it_escaped(self):
        # Act
        fragment = render_awawa_health(HEALTH, HEALTH_OF_OAK)

        # Assert
        self.assertIn(
            '</div><ul class="awawa-diagnostics"><li><span class="tone tone-failed">error</span>'
            " L001 corpus/tasks.awawa:3 &lt;b&gt;bad&lt;/b&gt;</li></ul></li></ul>",
            fragment,
        )

    def test_should_list_the_diagnostics_of_a_file_outside_any_entity(self):
        # Act
        fragment = render_awawa_health(HEALTH, HEALTH_OF_OAK)

        # Assert
        self.assertIn(
            '<h3>Files</h3><ul class="awawa-files"><li>corpus/old.awawa<ul class="awawa-diagnostics"><li>'
            '<span class="tone tone-you">warning</span> L010 corpus/old.awawa:1 unused</li></ul></li></ul>',
            fragment,
        )

    def test_should_say_that_a_healthy_corpus_raises_no_diagnostic(self):
        # Arrange
        healthy = HEALTH | {"errors": 0, "warnings": 0, "unresolved": 0, "entities": NO_AILING, "files": NO_AILING}

        # Act
        fragment = render_awawa_health(healthy, HEALTH_OF_OAK)

        # Assert
        self.assertIn(
            '</dl><div class="empty-state"><p class="empty-why">The corpus raises no diagnostic.</p>'
            '<p class="empty-fill">A lint error or warning would be listed here.</p></div>',
            fragment,
        )


class RenderAwawaHealthUnresolvedTest(unittest.TestCase):
    def test_should_not_call_a_corpus_holding_unresolved_references_free_of_diagnostics(self):
        # Arrange
        unresolved = HEALTH | {"errors": 0, "warnings": 0, "unresolved": 1, "entities": NO_AILING, "files": NO_AILING}

        # Act
        fragment = render_awawa_health(unresolved, HEALTH_OF_OAK)

        # Assert
        self.assertIn('<p class="empty-why">No entity or file raises a lint error or warning.</p>', fragment)
