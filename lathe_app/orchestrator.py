"""
Lathe App Orchestrator

The workflow loop that drives Lathe.
Stateless - all state is in the artifacts returned.
Storage is optional and injected.

RAG Enhancement:
- If intent == rag, queries knowledge index for evidence
- Missing index returns empty results (not error)
- Kernel RAG remains untouched
"""
from typing import Any, Callable, Dict, List, Optional

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
from lathe_app.storage import Storage


def query_knowledge_index(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Query the knowledge index for relevant chunks.
    
    Returns empty list if index is not available (never fails).
    """
    try:
        from lathe_app.knowledge.index import get_default_index
        index = get_default_index()
        
        if index.is_empty:
            return []
        
        results = index.query(query, k=k)
        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "similarity": round(score, 4),
            }
            for chunk, score in results
        ]
    except Exception:
        return []


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
    5. Optionally persists runs to storage
    
    The orchestrator is STATELESS.
    It may call Lathe multiple times but stores nothing internally.
    Persistence is delegated to the injected Storage.
    
    PROPOSALS DO NOT AUTO-APPLY.
    Execution requires an explicit call to execute_proposal().
    """
    
    def __init__(
        self,
        agent_fn: Callable = None,
        storage: Storage = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            agent_fn: Function to call for model execution.
                      Signature: (normalized, model_id) -> str
            storage: Optional storage backend for persisting runs.
                     If None, runs are not persisted.
        """
        self._agent_fn = agent_fn or _default_agent_fn
        self._storage = storage
    
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
            
        NOTE: Proposals are NOT auto-applied.
        Call execute_proposal() explicitly to apply changes.
        """
        model_id = model or FALLBACK_MODEL
        
        input_data = ArtifactInput(
            intent=intent,
            task=task,
            why=why,
            model_requested=model_id,
        )
        
        kernel_intent = intent
        if intent == "plan":
            kernel_intent = "think"
        
        payload = {
            "intent": kernel_intent,
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
        
        run_record = self._build_run_record(input_data, result)
        
        if self._storage is not None:
            self._storage.save_run(run_record)
        
        return run_record
    
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
