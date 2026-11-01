from html.parser import HTMLParser

WRITING_ATTRIBUTES = ("formmethod", "formaction")


class FormsCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.methods = []
        self.writing_attributes = []

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            self.methods.append(dict(attrs).get("method"))
        self.writing_attributes.extend((tag, name) for name, _ in attrs if name in WRITING_ATTRIBUTES)
