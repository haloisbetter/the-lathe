"""
Lathe App Query Layer

Read-only run history queries.
All queries are read-only with no side effects.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from lathe_app.artifacts import RunRecord, ProposalArtifact, RefusalArtifact, PlanArtifact
from lathe_app.storage import Storage


@dataclass
class QueryResult:
    """Result of a run query."""
    runs: List[RunRecord]
    total: int
    query: Dict[str, Any]


class RunQuery:
    """
    Read-only query interface for run history.
    
    Supports filtering by:
    - intent (propose, think, rag, plan)
    - outcome (success, refusal)
    - file paths touched
    - time range
    """
    
    def __init__(self, storage: Storage):
        self._storage = storage
    
    def search(
        self,
        *,
        intent: Optional[str] = None,
        outcome: Optional[str] = None,
        file: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> QueryResult:
        """
        Search runs with optional filters.
        
        Args:
            intent: Filter by intent type (propose, think, rag, plan)
            outcome: Filter by outcome (success, refusal)
            file: Filter by file path touched
            since: Filter by timestamp (ISO format)
            until: Filter by timestamp (ISO format)
            limit: Maximum results to return
            
        Returns:
            QueryResult with matching runs
        """
        query = {
            "intent": intent,
            "outcome": outcome,
            "file": file,
            "since": since,
            "until": until,
            "limit": limit,
        }
        
        all_run_ids = self._storage.list_runs()
        matching = []
        
        for run_id in all_run_ids:
            run = self._storage.load_run(run_id)
            if run is None:
                continue
            
            if self._matches(run, intent=intent, outcome=outcome, file=file, since=since, until=until):
                matching.append(run)
                
                if len(matching) >= limit:
                    break
        
        return QueryResult(
            runs=matching,
            total=len(matching),
            query=query,
        )
    
    def _matches(
        self,
        run: RunRecord,
        *,
        intent: Optional[str],
        outcome: Optional[str],
        file: Optional[str],
        since: Optional[str],
        until: Optional[str],
    ) -> bool:
        """Check if a run matches all filters."""
        if intent and run.input.intent != intent:
            return False
        
        if outcome:
            if outcome == "success" and not run.success:
                return False
            if outcome == "refusal" and run.success:
                return False
        
        if file:
            if not self._touches_file(run, file):
                return False
        
        if since:
            if run.timestamp < since:
                return False
        
        if until:
            if run.timestamp > until:
                return False
        
        return True
    
    def _touches_file(self, run: RunRecord, file: str) -> bool:
        """Check if a run touches a specific file."""
        output = run.output
        
        if isinstance(output, ProposalArtifact):
            for proposal in output.proposals:
                target = proposal.get("target", proposal.get("file", ""))
                if file in target or target in file:
                    return True
        
        if isinstance(output, PlanArtifact):
            for step in output.steps:
                files = step.get("files", [])
                if file in files or any(file in f for f in files):
                    return True
        
        return False
    
    def get_files_touched(self, run_id: str) -> List[str]:
        """Get list of files touched by a run."""
        run = self._storage.load_run(run_id)
        if run is None:
            return []
        
        files = []
        output = run.output
        
        if isinstance(output, ProposalArtifact):
            for proposal in output.proposals:
                target = proposal.get("target", proposal.get("file"))
                if target:
                    files.append(target)
        
        if isinstance(output, PlanArtifact):
            for step in output.steps:
                files.extend(step.get("files", []))
        
        return files
