import os
import fnmatch
from lathe.repo import search_repo
from lathe.context.builder import get_file_context_from_lines
from pathlib import Path

# Explicit separation of RAG channels
CONCEPTUAL_PATTERNS = ["*.md", "docs/**", "Makefile", "package.json"]
ACTIONABLE_PATTERNS = ["*.py", "tests/**"]

def _is_match(path: str, patterns: list) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.endswith("/**") and path.startswith(pattern[:-3]):
            return True
    return False

def retrieve_rag_evidence(task_description: str, top_n: int = 5, channel: str = "conceptual"):
    """
    RAG without embeddings, split into Conceptual and Actionable channels.
    """
    keywords = [word.strip(".,!?\"'()").lower() for word in task_description.split() if len(word) > 3]
    
    candidate_results = []
    seen_file_lines = set()
    
    # Select allowlist based on channel
    allowlist = CONCEPTUAL_PATTERNS if channel == "conceptual" else ACTIONABLE_PATTERNS
    
    for kw in keywords:
        results = search_repo(kw)
        for res in results:
            path_str = res['path']
            # Machine-enforced channel boundary
            if not _is_match(path_str, allowlist):
                continue
                
            key = (path_str, res['line'])
            if key not in seen_file_lines:
                seen_file_lines.add(key)
                candidate_results.append(res)
    
    selected = candidate_results[:top_n]
    
    evidence = []
    for item in selected:
        path_str = item['path']
        line = item['line']
        start = max(1, line - 5)
        end = line + 5
        
        try:
            file_path = Path(path_str)
            if not file_path.exists():
                continue
                
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            
            if line == 0:
                ctx = get_file_context_from_lines(path_str, all_lines, 1, 10)
                reason = "Filename match"
                actual_start, actual_end = 1, 10
            else:
                ctx = get_file_context_from_lines(path_str, all_lines, start, end)
                reason = f"Content match for keyword in line {line}"
                actual_start, actual_end = start, end
            
            evidence.append({
                "path": ctx['path'],
                "range": f"{actual_start}-{actual_end}",
                "content": ctx['lines'],
                "hash": ctx['hash'],
                "reason": reason
            })
        except Exception:
            continue
            
    return evidence
