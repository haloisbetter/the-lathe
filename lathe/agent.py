import os
import json
import fnmatch

class AgentReasoning:
    """
    Reasoning layer for Lathe with machine-enforced targeting guardrails.
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.actionable_allowlist = ["lathe/**", "tests/**"]
        self.denylist = ["*.md", "Makefile", "package.json", "docs/**"]

    def _is_allowed(self, path: str) -> bool:
        # Check denylist first (strict)
        for pattern in self.denylist:
            if fnmatch.fnmatch(path, pattern) or (pattern.endswith("/**") and path.startswith(pattern[:-3])):
                return False
        # Check allowlist
        for pattern in self.actionable_allowlist:
            if fnmatch.fnmatch(path, pattern) or (pattern.endswith("/**") and path.startswith(pattern[:-3])):
                return True
        return False

    def think(self, task: str, why_data: dict, evidence: list):
        """
        Reasoning using conceptual evidence.
        """
        plan = [
            f"1. Analyze {evidence[0]['path'] if evidence else 'architecture'} for intent.",
            "2. Map requirements to actionable code locations.",
            "3. Verify plan against WHY constraints."
        ]
        
        return {
            "proposed_plan": plan,
            "assumptions": ["Conceptual evidence provides sufficient context."],
            "evidence_references": [item['path'] for item in evidence]
        }

    def propose(self, task: str, why_data: dict, evidence: list, max_files: int = 5):
        """
        Produce proposed patches with machine-enforced guardrails.
        """
        proposals = []
        violations = []
        
        # Enforce allowlist BEFORE generation
        target_files = []
        for item in evidence:
            path = item['path']
            if self._is_allowed(path):
                target_files.append(path)
            else:
                violations.append(path)

        if not target_files:
            return {
                "proposals": [],
                "refusal": "No actionable files allowed by targeting guardrails match this task.",
                "details": f"Rejected files (denied or not in allowlist): {violations}",
                "assumptions": [],
                "risks": ["Proposal failed due to security constraints."]
            }

        for file_path in target_files[:max_files]:
            patch = f"""--- a/{file_path}
+++ b/{file_path}
@@ -1,1 +1,2 @@
-# Initial content
+# Proposed change for task: {task}
"""
            proposals.append({
                "file": file_path,
                "diff": patch.strip(),
                "intent": f"Modify {file_path}",
                "evidence_used": [file_path]
            })
            
        return {
            "proposals": proposals,
            "assumptions": ["Guardrails enforced: only .py or test files modified."],
            "risks": ["Standard patch application risks."]
        }
