import unittest

from brigade.dashboard.render_addons_rail import render_addons_rail

HOLDERS = frozenset({"oak", "elm"})
ALL_PROJECTS = None


class RenderAddonsRailTest(unittest.TestCase):
    def test_should_offer_the_awawa_tab_of_the_project_chosen_when_it_holds_a_corpus(self):
        # Act
        fragment = render_addons_rail(HOLDERS, "oak")

        # Assert
        self.assertEqual(fragment, '<a href="#awawa/oak" data-rail-view="awawa">awawa</a>')

    def test_should_offer_no_awawa_tab_for_a_project_holding_no_corpus(self):
        # Act
        fragment = render_addons_rail(HOLDERS, "shop")

        # Assert
        self.assertEqual(fragment, "")

    def test_should_offer_the_awawa_tab_of_each_project_holding_a_corpus_under_all_projects(self):
        # Act
        fragment = render_addons_rail(HOLDERS, ALL_PROJECTS)

        # Assert
        self.assertEqual(
            fragment,
            '<a href="#awawa/elm" data-rail-view="awawa">awawa · elm</a><a href="#awawa/oak" data-rail-view="awawa">awawa · oak</a>',
        )

    def test_should_escape_a_project_holding_markup(self):
        # Act
        fragment = render_addons_rail(frozenset({"<b>"}), ALL_PROJECTS)

        # Assert
        self.assertEqual(fragment, '<a href="#awawa/%3Cb%3E" data-rail-view="awawa">awawa · &lt;b&gt;</a>')
