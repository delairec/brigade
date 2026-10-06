FENCE = "---\n"


def render_role_file(front_matter: dict, body: str) -> str:
    entries = "".join(f"{key}: {value}\n" for key, value in front_matter.items())
    return f"{FENCE}{entries}{FENCE}{body}"
