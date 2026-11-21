import unittest

from brigade.dashboard.render_page_head import Crumb, PageHead, render_page_head


class RenderPageHeadTest(unittest.TestCase):
    def test_should_name_the_page_say_what_it_is_for_and_leave_room_for_the_read_time(self):
        # Arrange
        head = PageHead(title="Waves", lede="A wave is a batch <of> ratified tasks & more.")

        # Act
        rendered = render_page_head(head)

        # Assert
        self.assertEqual(
            rendered,
            '<header class="page-head"><div><h1>Waves</h1>'
            '<p class="lede">A wave is a batch &lt;of&gt; ratified tasks &amp; more.</p></div>'
            '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>',
        )

    def test_should_set_the_name_alone_when_the_page_shows_no_state(self):
        # Arrange
        no_state = ""
        head = PageHead(title="Report", lede="One delivery.", name="oak_M4", state=no_state)

        # Act
        rendered = render_page_head(head)

        # Assert
        self.assertEqual(
            rendered,
            '<header class="page-head"><div><h1>Report <span class="mono">oak_M4</span></h1>'
            '<p class="lede">One delivery.</p></div>'
            '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>',
        )

    def test_should_set_the_name_of_what_a_detail_page_shows_in_mono_beside_the_pill_of_its_state(self):
        # Arrange
        head = PageHead(title="Wave", lede="All 4 tasks merged.", name="w<57>", state="parked")

        # Act
        rendered = render_page_head(head)

        # Assert
        self.assertEqual(
            rendered,
            '<header class="page-head"><div><h1>Wave <span class="mono">w&lt;57&gt;</span>'
            ' <span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>'
            "parked</span></span></h1>"
            '<p class="lede">All 4 tasks merged.</p></div>'
            '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>',
        )

    def test_should_lead_a_detail_page_back_to_the_list_it_belongs_to(self):
        # Arrange
        here = ""
        head = PageHead(
            title="Wave",
            lede="All 4 tasks merged.",
            name="w57",
            crumbs=(Crumb(label="Waves", address="#waves"), Crumb(label="oak <&>", address=here)),
        )

        # Act
        rendered = render_page_head(head)

        # Assert
        self.assertEqual(
            rendered,
            '<header class="page-head"><div><p class="crumbs"><a href="#waves">Waves</a> / oak &lt;&amp;&gt;</p>'
            '<h1>Wave <span class="mono">w57</span></h1>'
            '<p class="lede">All 4 tasks merged.</p></div>'
            '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>',
        )
