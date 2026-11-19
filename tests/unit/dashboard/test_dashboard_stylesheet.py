import unittest

from tests.unit.dashboard.stylesheet_reader import (
    read_colour_literals_of_the_views,
    read_dark_properties,
    read_light_properties,
    read_rule,
    read_stylesheet,
    read_tone_classes,
)


class DashboardStylesheetTest(unittest.TestCase):
    def test_should_declare_the_tones_the_neutrals_the_spacing_the_radius_the_fonts_and_the_sizes(self):
        # Act
        properties = read_light_properties()

        # Assert
        self.assertEqual(
            properties,
            {
                "--you": "#b36b00",
                "--work": "#2f6fdb",
                "--review": "#138a8a",
                "--done": "#2e8b3e",
                "--limit": "#8a3fc7",
                "--failed": "#c4372f",
                "--off": "#7a7a7a",
                "--bg": "#f7f7f5",
                "--surface": "#ffffff",
                "--sunken": "#efefec",
                "--line": "#e3e3de",
                "--line-strong": "#c8c8c1",
                "--text": "#1d1d1b",
                "--muted": "#5c5c57",
                "--faint": "#8f8f89",
                "--ink": "#1d1d1b",
                "--on-ink": "#ffffff",
                "--space-1": "4px",
                "--space-2": "8px",
                "--space-3": "12px",
                "--space-4": "16px",
                "--space-5": "24px",
                "--space-6": "32px",
                "--space-7": "48px",
                "--radius": "3px",
                "--font-sans": 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
                "--font-mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                "--size-1": "26px",
                "--size-2": "19px",
                "--size-3": "16px",
                "--size-4": "14px",
                "--size-5": "13px",
                "--size-6": "11px",
            },
        )

    def test_should_declare_the_dark_tones_and_neutrals_under_the_dark_colour_scheme(self):
        # Act
        properties = read_dark_properties()

        # Assert
        self.assertEqual(
            properties,
            {
                "--you": "#e0a04b",
                "--work": "#6fa3f7",
                "--review": "#4fc1c1",
                "--done": "#6cc47a",
                "--limit": "#b58cf0",
                "--failed": "#f0796f",
                "--off": "#8c8c8c",
                "--bg": "#141413",
                "--surface": "#1c1c1a",
                "--sunken": "#10100f",
                "--line": "#2d2d2a",
                "--line-strong": "#3f3f3a",
                "--text": "#ecece8",
                "--muted": "#a3a39c",
                "--faint": "#77776f",
                "--ink": "#ecece8",
                "--on-ink": "#141413",
            },
        )

    def test_should_give_each_tone_class_the_custom_property_of_its_tone(self):
        # Act
        classes = read_tone_classes()

        # Assert
        self.assertEqual(
            classes,
            [
                ("you", "you"),
                ("work", "work"),
                ("review", "review"),
                ("done", "done"),
                ("limit", "limit"),
                ("failed", "failed"),
                ("off", "off"),
                ("faint", "faint"),
            ],
        )

    def test_should_write_no_colour_as_a_literal_in_a_rule_of_a_view(self):
        # Act
        literals = read_colour_literals_of_the_views()

        # Assert
        self.assertEqual(literals, [])

    def test_should_draw_with_borders_and_no_shadow_on_system_fonts_and_tabular_figures(self):
        # Act
        stylesheet = read_stylesheet()

        # Assert
        self.assertNotIn("box-shadow", stylesheet)
        self.assertNotIn("@font-face", stylesheet)
        self.assertIn("font-variant-numeric: tabular-nums;", stylesheet)

    def test_should_lay_the_stat_tiles_of_a_view_in_a_row_that_wraps_above_its_table(self):
        # Act
        rule = read_rule(".stat-tiles")

        # Assert
        self.assertEqual(
            rule,
            {"display": "flex", "flex-wrap": "wrap", "gap": "var(--space-3)", "margin": "0 0 var(--space-5)"},
        )

    def test_should_draw_a_missing_verdict_and_a_missing_date_in_the_faint_neutral(self):
        # Act
        rule = read_rule(".no-verdict,\n.no-date")

        # Assert
        self.assertEqual(rule, {"color": "var(--faint)"})

    def test_should_turn_the_rail_into_a_top_bar_under_900px(self):
        # Act
        stylesheet = read_stylesheet()

        # Assert
        self.assertIn("@media (max-width: 900px) {\n  body {\n    grid-template-columns: 1fr;", stylesheet)
