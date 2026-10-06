from brigade.roles.resolve_role import resolve_role

DOCUMENT_SCHEMA_VERSION = 1


def run(request, runtime) -> dict:
    resolved = resolve_role(request.slot, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "slot": resolved.slot,
        "role": resolved.role,
        "source": resolved.source,
        "front_matter": resolved.front_matter,
        "body": resolved.body,
    }
