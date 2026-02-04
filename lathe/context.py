import hashlib
from pathlib import Path

def get_file_context(path_spec, max_lines=500):
    """
    path_spec format: path:start-end
    Example: lathe/main.py:1-20
    """
    try:
        path_part, range_part = path_spec.rsplit(":", 1)
        start_str, end_str = range_part.split("-")
        start = int(start_str)
        end = int(end_str)
    except ValueError:
        raise ValueError("Invalid format. Use path:start-end (e.g., file.py:1-20)")

    if start < 1:
        start = 1
    
    if end - start + 1 > max_lines:
        end = start + max_lines - 1

    file_path = Path(path_part)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path_part}")

    lines_to_return = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        all_lines = f.readlines()
        
    actual_end = min(end, len(all_lines))
    content_to_hash = ""
    
    for i in range(start - 1, actual_end):
        line_content = all_lines[i]
        lines_to_return.append((i + 1, line_content.rstrip()))
        content_to_hash += line_content

    content_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()

    return {
        "path": path_part,
        "lines": lines_to_return,
        "hash": content_hash
    }
