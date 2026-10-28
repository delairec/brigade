class DocumentPluginDouble:
    def __init__(self, entities_by_path: dict):
        self.entities_by_path = entities_by_path

    def render_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "text": "", "entities": self.entities_by_path[request["path"]]}
