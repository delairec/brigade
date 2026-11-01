from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.mining.read_sessions import read_sessions
from brigade.runtime import Runtime

NAME = "transcripts"
NOT_CACHED = False


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    read = read_sessions(environment, runtime, equipment)
    items = [
        {
            "client": session.finished.client,
            "session": session.finished.session,
            "run": session.finished.run,
            "project": session.finished.project,
            "task": session.finished.task,
            "position": position,
            **message.to_document(),
        }
        for session in read.sessions
        for position, message in enumerate(session.messages, start=1)
    ]
    summary = {"sessions": len(read.sessions), "messages": len(items), "unreadable": list(read.unreadable)}
    return {**describe_collection(NAME, runtime, summary, items), "cache": NOT_CACHED}
