from brigade.dashboard.render_empty_state import render_empty_state


def render_nothing_matching() -> str:
    return render_empty_state(
        "No entity matches this address.", "Clear the filters and the search to see the whole corpus."
    )
