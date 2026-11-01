from html.parser import HTMLParser

LOADING_TAGS = ("script", "link")
EVENT_HANDLER_PREFIX = "on"


class PageElementsCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.loaded = []
        self.inline_scripts = []
        self.style_elements = []
        self.inline_attributes = []
        self.view_links = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        self.in_script = tag == "script"
        if tag in LOADING_TAGS:
            self.loaded.append((tag, dict(attrs)))
        if tag == "a":
            self.view_links.append(dict(attrs)["href"])
        if tag == "style":
            self.style_elements.append(tag)
        for name, _ in attrs:
            if name == "style" or name.startswith(EVENT_HANDLER_PREFIX):
                self.inline_attributes.append((tag, name))

    def handle_endtag(self, tag):
        self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.inline_scripts.append(data)
