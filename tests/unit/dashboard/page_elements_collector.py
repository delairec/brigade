from html.parser import HTMLParser

LOADING_TAGS = ("script", "link")
EVENT_HANDLER_PREFIX = "on"
REGION_ATTRIBUTE = "data-region"
ALERT_ROLE = "alert"


class PageElementsCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.loaded = []
        self.inline_scripts = []
        self.style_elements = []
        self.inline_attributes = []
        self.view_links = []
        self.groups = []
        self.regions = []
        self.alerts = []
        self.in_script = False
        self.in_group_title = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.in_script = tag == "script"
        self.in_group_title = tag == "h2"
        if tag in LOADING_TAGS:
            self.loaded.append((tag, attributes))
        if tag == "a":
            self.view_links.append(attributes["href"])
        if tag == "a" and self.groups:
            self.groups[-1][1].append(attributes["href"])
        if tag == "style":
            self.style_elements.append(tag)
        if REGION_ATTRIBUTE in attributes:
            self.regions.append((tag, attributes))
        if attributes.get("role") == ALERT_ROLE:
            self.alerts.append((tag, attributes))
        for name, _ in attrs:
            if name == "style" or name.startswith(EVENT_HANDLER_PREFIX):
                self.inline_attributes.append((tag, name))

    def handle_endtag(self, tag):
        self.in_script = False
        self.in_group_title = False

    def handle_data(self, data):
        if self.in_script:
            self.inline_scripts.append(data)
        if self.in_group_title:
            self.groups.append((data, []))
