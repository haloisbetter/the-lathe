"""
Lathe App Layer

The shell around the Lathe kernel.
All state lives here. Lathe remains pure.
"""
from lathe_app.orchestrator import Orchestrator
from lathe_app.artifacts import (
    RunRecord,
    PlanArtifact,
    ProposalArtifact,
    RefusalArtifact,
)

_default_orchestrator = Orchestrator()


def run_request(
    intent: str,
    task: str,
    why: dict,
    *,
    model: str = None,
) -> RunRecord:
    """
    Execute a request through Lathe and return a structured RunRecord.
    
    This is the main entry point for the app layer.
    Lathe is called but never stores state.
    
    Args:
        intent: The intent type (propose, think, rag, etc.)
        task: The task description
        why: The WHY record (goal, context, evidence, etc.)
        model: Optional model override
        
    Returns:
        RunRecord containing the full execution trace and artifacts.
    """
    return _default_orchestrator.execute(
        intent=intent,
        task=task,
        why=why,
        model=model,
    )


__all__ = [
    "run_request",
    "Orchestrator",
    "RunRecord",
    "PlanArtifact",
    "ProposalArtifact",
    "RefusalArtifact",
]
