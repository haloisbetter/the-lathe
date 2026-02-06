"""
Lathe App Orchestrator

The workflow loop that drives Lathe.
Stateless - all state is in the artifacts returned.
Storage is optional and injected.

RAG Enhancement:
- If intent == rag, queries knowledge index for evidence
- Missing index returns empty results (not error)
- Kernel RAG remains untouched

Workspace Isolation:
- Operations can be scoped to a workspace
- No workspace = default workspace (current directory)
- Workspace data never leaks into kernel

Speculative Model Selection:
- For propose/think intents, tries cheap model first
- Escalates to stronger model if validator rejects or warnings exceed threshold
- All escalation decisions are logged in RunRecord.escalation
"""
from typing import Any, Callable, Dict, List, Optional

from lathe.pipeline import process_request, PipelineResult
from lathe.model_tiers import FALLBACK_MODEL, classify_model, ModelTier
from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    RefusalArtifact,
    ProposalArtifact,
    PlanArtifact,
)
from lathe_app.classification import ResultClassification
from lathe_app.storage import Storage
from lathe_app.workspace.context import WorkspaceContext, get_current_context
from lathe_app.workspace.memory import load_workspace_context, create_file_read

SPECULATIVE_CHEAP_MODEL = "deepseek-chat"
SPECULATIVE_STRONG_MODEL = "gpt-4"
WARNING_ESCALATION_THRESHOLD = 3
SPECULATIVE_INTENTS = frozenset({"propose", "think", "plan"})


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
        workspace_id: str = None,
        speculative: bool = True,
    ) -> RunRecord:
        """
        Execute a single request through Lathe.
        
        Args:
            intent: The intent type (propose, think, rag, plan)
            task: The task description
            why: The WHY record
            model: Optional model override (defaults to FALLBACK_MODEL)
            workspace_id: Optional workspace to scope this run to
            speculative: If True, use cheap-first speculative model selection
            
        Returns:
            RunRecord with the execution result.
            
        NOTE: Proposals are NOT auto-applied.
        Call execute_proposal() explicitly to apply changes.
        """
        model_id = model or FALLBACK_MODEL
        
        context = self._get_workspace_context(workspace_id)
        
        input_data = ArtifactInput(
            intent=intent,
            task=task,
            why=why,
            model_requested=model_id,
        )
        
        input_data.workspace_id = context.workspace_id
        
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
        
        escalation = None
        classification = ResultClassification.from_pipeline_result(
            result.response, not result.response.get("refusal", False)
        )
        
        if (speculative
            and intent in SPECULATIVE_INTENTS
            and self._should_escalate(result, classification)
            and model_id != SPECULATIVE_STRONG_MODEL):
            
            escalation = {
                "from_model": model_id,
                "to_model": SPECULATIVE_STRONG_MODEL,
                "reasons": self._escalation_reasons(result, classification),
            }
            
            strong_result = process_request(
                payload=payload,
                model_id=SPECULATIVE_STRONG_MODEL,
                agent_fn=self._agent_fn,
                allow_fallback=True,
                require_fingerprint=True,
                enable_observability=True,
            )
            
            strong_classification = ResultClassification.from_pipeline_result(
                strong_result.response,
                not strong_result.response.get("refusal", False),
            )
            
            if self._is_better_result(strong_result, strong_classification, result, classification):
                result = strong_result
                classification = strong_classification
                escalation["accepted"] = True
            else:
                escalation["accepted"] = False
        
        ws_context_data = None
        try:
            ws_context_data = load_workspace_context(context.root_path)
        except Exception:
            pass

        file_reads = self._extract_file_reads(result.response, context)

        run_record = self._build_run_record(
            input_data, result,
            classification=classification,
            escalation=escalation,
            file_reads=file_reads,
            workspace_context_loaded=ws_context_data,
        )
        
        if self._storage is not None:
            self._storage.save_run(run_record)
        
        return run_record
    
    def _should_escalate(
        self,
        result: PipelineResult,
        classification: ResultClassification,
    ) -> bool:
        if result.response.get("refusal") is True:
            reason = result.response.get("reason", "")
            if "not authorized" in reason.lower():
                return False
            return True
        if len(classification.warnings) >= WARNING_ESCALATION_THRESHOLD:
            return True
        if classification.confidence < 0.6:
            return True
        return False
    
    def _escalation_reasons(
        self,
        result: PipelineResult,
        classification: ResultClassification,
    ) -> List[str]:
        reasons = []
        if result.response.get("refusal") is True:
            reasons.append(f"validator_rejected: {result.response.get('reason', 'unknown')}")
        if len(classification.warnings) >= WARNING_ESCALATION_THRESHOLD:
            reasons.append(f"warning_count: {len(classification.warnings)}")
        if classification.confidence < 0.6:
            reasons.append(f"low_confidence: {classification.confidence}")
        return reasons
    
    def _is_better_result(
        self,
        new_result: PipelineResult,
        new_class: ResultClassification,
        old_result: PipelineResult,
        old_class: ResultClassification,
    ) -> bool:
        if old_result.response.get("refusal") and not new_result.response.get("refusal"):
            return True
        if new_class.confidence > old_class.confidence:
            return True
        if len(new_class.warnings) < len(old_class.warnings):
            return True
        return False
    
    def _extract_file_reads(
        self,
        response: Dict[str, Any],
        context: WorkspaceContext,
    ) -> List[Dict[str, Any]]:
        """Extract file read artifacts from pipeline response.

        Scans proposals/steps for ``target`` fields that reference existing
        files within the workspace and creates FileReadArtifacts for each.
        """
        import os
        file_reads: List[Dict[str, Any]] = []
        seen: set = set()

        items = response.get("proposals", []) + response.get("steps", [])
        for item in items:
            if not isinstance(item, dict):
                continue
            target = item.get("target")
            if not target or not isinstance(target, str):
                continue
            resolved = context.resolve_path(target)
            if resolved is None:
                continue
            if resolved in seen:
                continue
            if not os.path.isfile(resolved):
                continue
            seen.add(resolved)
            try:
                art = create_file_read(resolved)
                file_reads.append(art.to_dict())
            except Exception:
                pass

        return file_reads

    def _build_run_record(
        self,
        input_data: ArtifactInput,
        result: PipelineResult,
        classification: ResultClassification = None,
        escalation: Optional[Dict[str, Any]] = None,
        file_reads: Optional[List[Dict[str, Any]]] = None,
        workspace_context_loaded: Optional[Dict[str, Any]] = None,
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
        
        if classification is None:
            classification = ResultClassification.from_pipeline_result(response, success)
        
        return RunRecord.create(
            input_data=input_data,
            output=output,
            model_used=result.model_used,
            fallback_triggered=result.fallback_triggered,
            success=success,
            classification=classification,
            escalation=escalation,
            file_reads=file_reads,
            workspace_context_loaded=workspace_context_loaded,
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
    
    def _get_workspace_context(self, workspace_id: str = None) -> WorkspaceContext:
        """
        Get workspace context for a request.
        
        Args:
            workspace_id: Optional workspace ID
            
        Returns:
            WorkspaceContext (default if no workspace specified)
        """
        if workspace_id is None:
            return get_current_context()
        
        context = WorkspaceContext.from_workspace_id(workspace_id)
        if context is None:
            return get_current_context()
        
        return context
