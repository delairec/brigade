from brigade.runs.describe_progress import describe_progress
from brigade.runs.plan_run import RunPlan
from brigade.runtime import Runtime
from brigade.system.ask_document import DocumentQuestion, ask_document
from brigade.system.document_creation import DocumentCreation
from brigade.system.document_text import DocumentText
from brigade.system.entry_detection import EntryDetection


def ask_progress(plan: RunPlan, operation: str, runtime: Runtime) -> DocumentCreation | DocumentText | EntryDetection:
    question = DocumentQuestion(
        document_name=plan.configuration.document, operation=operation, request=describe_progress(plan)
    )
    return ask_document(plan.document, question, runtime)
