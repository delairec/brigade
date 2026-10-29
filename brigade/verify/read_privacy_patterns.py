from brigade.corpus.read_entity import Entity
from brigade.verify.check_privacy import PrivacyPatterns


def read_privacy_patterns(project: Entity) -> PrivacyPatterns:
    return PrivacyPatterns(
        private=tuple(field.value for field in project.fields if field.name == "PRIVATE"),
        public=tuple(field.value for field in project.fields if field.name == "PUBLIC"),
    )
