"""
Lathe App Orchestrator

The workflow loop that drives Lathe.
Stateless - all state is in the artifacts returned.
"""
from typing import Any, Callable, Dict, Optional

from lathe.pipeline import process_request, PipelineResult
from lathe.model_tiers import FALLBACK_MODEL
from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    RefusalArtifact,
    ProposalArtifact,
    PlanArtifact,
)


def _default_agent_fn(normalized, model_id: str) -> str:
    """
    Default agent function that returns a placeholder.
    In production, this would call an actual LLM.
    """
    import json
    return json.dumps({
        "proposals": [],
        "assumptions": [],
        "risks": [],
        "results": [],
        "model_fingerprint": model_id,
    })


class Orchestrator:
    """
    Drives Lathe to produce artifacts.
    
    The orchestrator:
    1. Accepts user requests
    2. Calls Lathe pipeline
    3. Classifies results (success / refusal)
    4. Returns structured RunRecords
    
    The orchestrator is STATELESS.
    It may call Lathe multiple times but stores nothing.
    """
    
    def __init__(self, agent_fn: Callable = None):
        """
        Initialize orchestrator.
        
        Args:
            agent_fn: Function to call for model execution.
                      Signature: (normalized, model_id) -> str
        """
        self._agent_fn = agent_fn or _default_agent_fn
    
    def execute(
        self,
        intent: str,
        task: str,
        why: Dict[str, Any],
        *,
        model: str = None,
    ) -> RunRecord:
        """
        Execute a single request through Lathe.
        
        Args:
            intent: The intent type (propose, think, rag, plan)
            task: The task description
            why: The WHY record
            model: Optional model override (defaults to FALLBACK_MODEL)
            
        Returns:
            RunRecord with the execution result.
        """
        model_id = model or FALLBACK_MODEL
        
        input_data = ArtifactInput(
            intent=intent,
            task=task,
            why=why,
            model_requested=model_id,
        )
        
        payload = {
            "intent": intent,
            "task": task,
            "why": why,
        }
        
        result = process_request(
            payload=payload,
            model_id=model_id,
            agent_fn=self._agent_fn,
            allow_fallback=True,
            require_fingerprint=True,
            enable_observability=True,
        )
        
        return self._build_run_record(input_data, result)
    
    def _build_run_record(
        self,
        input_data: ArtifactInput,
        result: PipelineResult,
    ) -> RunRecord:
        """Build a RunRecord from pipeline result."""
        response = result.response
        
        obs_data = response.get("_observability", {})
        observability = ObservabilityTrace.from_dict(obs_data)
        
        is_refusal = response.get("refusal") is True
        
        if is_refusal:
            output = RefusalArtifact.create(
                input_data=input_data,
                reason=response.get("reason", "Unknown"),
                details=response.get("details", ""),
                observability=observability,
            )
            success = False
        else:
            output = self._build_success_artifact(
                input_data=input_data,
                response=response,
                observability=observability,
            )
            success = True
        
        return RunRecord.create(
            input_data=input_data,
            output=output,
            model_used=result.model_used,
            fallback_triggered=result.fallback_triggered,
            success=success,
        )
    
    def _build_success_artifact(
        self,
        input_data: ArtifactInput,
        response: Dict[str, Any],
        observability: ObservabilityTrace,
    ):
        """Build the appropriate success artifact based on intent."""
        intent = input_data.intent
        
        if intent == "plan":
            return PlanArtifact.create(
                input_data=input_data,
                steps=response.get("steps", response.get("proposals", [])),
                dependencies=response.get("dependencies", []),
                results=response.get("results", []),
                model_fingerprint=response.get("model_fingerprint"),
                observability=observability,
            )
        else:
            return ProposalArtifact.create(
                input_data=input_data,
                proposals=response.get("proposals", []),
                assumptions=response.get("assumptions", []),
                risks=response.get("risks", []),
                results=response.get("results", []),
                model_fingerprint=response.get("model_fingerprint"),
                observability=observability,
            )
