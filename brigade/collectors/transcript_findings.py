from collections import Counter

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.mining.detect_findings import detect_findings
from brigade.mining.read_sessions import read_sessions
from brigade.mining.scrub_document import scrub_document
from brigade.runtime import Runtime

NAME = "transcript-findings"
NOT_CACHED = False


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    read = read_sessions(environment, runtime, equipment)
    items = [finding for session in read.sessions for finding in detect_findings(session)]
    summary = {
        "sessions": len(read.sessions),
        "findings": dict(Counter(finding["detector"] for finding in items)),
        "unreadable": list(read.unreadable),
    }
    return scrub_document({**describe_collection(NAME, runtime, summary, items), "cache": NOT_CACHED}, runtime)
