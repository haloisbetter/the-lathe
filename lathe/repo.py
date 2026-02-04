import os
import re
from pathlib import Path

def get_ignore_patterns(root_path):
    ignore_patterns = [".git", "__pycache__", ".lathe", "node_modules", ".pythonlibs", ".cache"]
    gitignore_path = Path(root_path) / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_patterns.append(line)
    return ignore_patterns

def is_ignored(path, root_path, ignore_patterns):
    rel_path = os.path.relpath(path, root_path)
    for pattern in ignore_patterns:
        if pattern in rel_path or pattern in os.path.basename(path):
            return True
    return False

def is_binary(file_path):
    try:
        with open(file_path, "tr") as f:
            f.read(1024)
            return False
    except UnicodeDecodeError:
        return True

def search_repo(query, root_path="."):
    root_path = os.path.abspath(root_path)
    ignore_patterns = get_ignore_patterns(root_path)
    results = []

    for root, dirs, files in os.walk(root_path):
        # Filter directories in-place to respect .gitignore
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), root_path, ignore_patterns)]
        
        for file in files:
            file_path = os.path.join(root, file)
            if is_ignored(file_path, root_path, ignore_patterns):
                continue
            
            if is_binary(file_path):
                continue
            
            # Filename match
            if query.lower() in file.lower():
                results.append({
                    "path": os.path.relpath(file_path, root_path),
                    "line": 0,
                    "snippet": "[Filename match]"
                })

            # Content search
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if query.lower() in line.lower():
                            results.append({
                                "path": os.path.relpath(file_path, root_path),
                                "line": i,
                                "snippet": line.strip()
                            })
            except Exception:
                continue
                
    return results
