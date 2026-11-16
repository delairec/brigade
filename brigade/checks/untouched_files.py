from pathlib import Path

from brigade.checks._read_pull_request import read_pull_request
from brigade.git.count_changed_lines import ChangedFile
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_untouched_files import UntouchedFilesFacts, check_untouched_files


def check(subject: dict, runtime: Runtime) -> dict:
    facts = read_pull_request(subject)
    untouched = UntouchedFilesFacts(
        base_tree=Path(facts["base_tree"]),
        head_tree=Path(facts["head_tree"]),
        changed=tuple(ChangedFile(**changed) for changed in facts["changed"]),
        folder=Path(facts["folder"]),
    )
    return {
        "schema_version": CHECK_DOCUMENT_SCHEMA_VERSION,
        **check_untouched_files(runtime.run_process, untouched),
    }
