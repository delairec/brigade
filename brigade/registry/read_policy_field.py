from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field


def read_policy_field(policies: list[Entity], project: str, field_name: str, neutral: str) -> str:
    values = [
        read_project_field(policy, field_name)
        for policy in policies
        if read_project_field(policy, "PROJECT") == f"@PROJECT.{project}"
    ]
    return next((value for value in values if value is not None), neutral)
