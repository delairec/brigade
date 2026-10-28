from brigade.dashboard.render_corpus_selector import render_corpus_selector

NO_SELECTION: dict = {}


def render_project_choice(document: dict) -> str:
    return render_corpus_selector([project["name"] for project in document["projects"]], NO_SELECTION)
