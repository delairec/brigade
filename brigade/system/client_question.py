from dataclasses import dataclass

from brigade.system.actions_request import ActionsRequest
from brigade.system.launch_argv_request import LaunchArgvRequest
from brigade.system.parse_result_request import ParseResultRequest
from brigade.system.probe_request import ProbeRequest
from brigade.system.resume_argv_request import ResumeArgvRequest
from brigade.system.transcripts_request import TranscriptsRequest

ClientRequest = (
    ProbeRequest | LaunchArgvRequest | ResumeArgvRequest | ParseResultRequest | TranscriptsRequest | ActionsRequest
)


@dataclass(frozen=True)
class ClientQuestion:
    client_name: str
    request: ClientRequest
