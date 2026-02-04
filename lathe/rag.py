import os
from lathe.repo import search_repo
from lathe.context.builder import get_file_context

def retrieve_rag_evidence(task_description: str, top_n: int = 5):
    """
    RAG without embeddings.
    1. Identify keywords from task description.
    2. Search repo for those keywords.
    3. Retrieve context snippets.
    """
    # Simple keyword extraction: words > 3 chars
    keywords = [word.strip(".,!?\"'()").lower() for word in task_description.split() if len(word) > 3]
    
    candidate_results = []
    seen_file_lines = set()
    
    for kw in keywords:
        results = search_repo(kw)
        for res in results:
            # Avoid duplicate lines in results
            key = (res['path'], res['line'])
            if key not in seen_file_lines:
                seen_file_lines.add(key)
                candidate_results.append(res)
    
    # Sort by some relevance? For now, just take top_n
    # We could count how many keywords matched per file/line.
    selected = candidate_results[:top_n]
    
    evidence = []
    for item in selected:
        path = item['path']
        line = item['line']
        
        # Determine range: 5 lines before and after
        start = max(1, line - 5)
        end = line + 5
        
        try:
            if line == 0: # Filename match
                # Just get the first 10 lines
                ctx = get_file_context(f"{path}:1-10")
                reason = "Filename match"
            else:
                ctx = get_file_context(f"{path}:{start}-{end}")
                reason = f"Content match for keyword in line {line}"
            
            evidence.append({
                "path": ctx['path'],
                "range": f"{start}-{end}" if line > 0 else "1-10",
                "content": ctx['lines'],
                "hash": ctx['hash'],
                "reason": reason
            })
        except Exception:
            continue
            
    return evidence
