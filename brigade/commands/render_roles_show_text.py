from brigade.roles.render_role_file import render_role_file

FINAL_NEWLINE = "\n"


def render_roles_show_text(document: dict) -> str:
    return render_role_file(document["front_matter"], document["body"]).removesuffix(FINAL_NEWLINE)
