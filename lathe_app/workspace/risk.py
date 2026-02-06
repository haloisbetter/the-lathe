"""
Workspace Risk Assessment

Computes risk signals from workspace scans:
- Extension distribution
- Directory depth fingerprint
- File size distribution (top N largest files)
- Python import graph (AST-based, read-only, no code execution)
- Dependency gravity (import counts per file)

All operations are read-only. No code execution.
"""
import ast
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FileMetrics:
    path: str
    size_bytes: int
    depth: int
    extension: str


@dataclass
class ImportEdge:
    source: str
    target: str


@dataclass
class RiskSummary:
    total_files: int = 0
    extension_distribution: Dict[str, int] = field(default_factory=dict)
    max_depth: int = 0
    avg_depth: float = 0.0
    largest_files: List[Dict[str, Any]] = field(default_factory=list)
    import_graph_edges: int = 0
    gravity_scores: Dict[str, float] = field(default_factory=dict)
    hotspot_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "extension_distribution": self.extension_distribution,
            "max_depth": self.max_depth,
            "avg_depth": round(self.avg_depth, 2),
            "largest_files": self.largest_files,
            "import_graph_edges": self.import_graph_edges,
            "gravity_scores": {k: round(v, 2) for k, v in self.gravity_scores.items()},
            "hotspot_files": self.hotspot_files,
        }


def compute_file_metrics(files: List[str], root_path: str) -> List[FileMetrics]:
    metrics = []
    for f in files:
        try:
            size = os.path.getsize(f)
        except OSError:
            size = 0
        rel = os.path.relpath(f, root_path)
        depth = rel.count(os.sep)
        _, ext = os.path.splitext(f)
        metrics.append(FileMetrics(
            path=rel,
            size_bytes=size,
            depth=depth,
            extension=ext.lower() if ext else "",
        ))
    return metrics


def compute_extension_distribution(metrics: List[FileMetrics]) -> Dict[str, int]:
    counter: Counter = Counter()
    for m in metrics:
        if m.extension:
            counter[m.extension] += 1
    return dict(counter.most_common())


def compute_depth_stats(metrics: List[FileMetrics]) -> Tuple[int, float]:
    if not metrics:
        return 0, 0.0
    depths = [m.depth for m in metrics]
    return max(depths), sum(depths) / len(depths)


def compute_largest_files(metrics: List[FileMetrics], top_n: int = 10) -> List[Dict[str, Any]]:
    sorted_by_size = sorted(metrics, key=lambda m: m.size_bytes, reverse=True)
    return [
        {"path": m.path, "size_bytes": m.size_bytes, "size_kb": round(m.size_bytes / 1024, 1)}
        for m in sorted_by_size[:top_n]
    ]


def parse_python_imports(file_path: str) -> List[str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except (SyntaxError, OSError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


def compute_import_graph(py_files: List[str], root_path: str) -> Tuple[List[ImportEdge], Dict[str, float]]:
    edges: List[ImportEdge] = []
    import_counts: Counter = Counter()

    file_modules = {}
    for f in py_files:
        rel = os.path.relpath(f, root_path)
        module = rel.replace(os.sep, ".").replace(".py", "")
        if module.endswith(".__init__"):
            module = module[:-9]
        file_modules[f] = module

    module_set = set(file_modules.values())
    top_level_set = {m.split(".")[0] for m in module_set}

    for f in py_files:
        source_module = file_modules[f]
        imports = parse_python_imports(f)
        for imp in imports:
            if imp in top_level_set or imp in module_set:
                edges.append(ImportEdge(source=source_module, target=imp))
                import_counts[imp] += 1

    max_count = max(import_counts.values()) if import_counts else 1
    gravity: Dict[str, float] = {}
    for module, count in import_counts.items():
        gravity[module] = round(count / max_count, 4)

    return edges, gravity


def compute_risk_summary(
    files: List[str],
    root_path: str,
    top_n_largest: int = 10,
    hotspot_threshold: float = 0.7,
) -> RiskSummary:
    metrics = compute_file_metrics(files, root_path)
    ext_dist = compute_extension_distribution(metrics)
    max_depth, avg_depth = compute_depth_stats(metrics)
    largest = compute_largest_files(metrics, top_n=top_n_largest)

    py_files = [f for f in files if f.endswith(".py")]
    edges, gravity = compute_import_graph(py_files, root_path)

    hotspots = [mod for mod, score in gravity.items() if score >= hotspot_threshold]

    return RiskSummary(
        total_files=len(files),
        extension_distribution=ext_dist,
        max_depth=max_depth,
        avg_depth=avg_depth,
        largest_files=largest,
        import_graph_edges=len(edges),
        gravity_scores=gravity,
        hotspot_files=sorted(hotspots),
    )


def assess_proposal_risk(
    touched_files: List[str],
    risk_summary: RiskSummary,
) -> Dict[str, Any]:
    touched_gravity = {}
    for f in touched_files:
        normalized = f.replace(os.sep, ".").replace(".py", "")
        for mod, score in risk_summary.gravity_scores.items():
            if mod in normalized or normalized in mod:
                touched_gravity[f] = score
                break

    max_gravity = max(touched_gravity.values()) if touched_gravity else 0.0
    touches_hotspot = any(
        any(h in f.replace(os.sep, ".") for h in risk_summary.hotspot_files)
        for f in touched_files
    )

    largest_paths = {entry["path"] for entry in risk_summary.largest_files[:5]}
    touches_large_file = any(
        os.path.basename(f) in {os.path.basename(p) for p in largest_paths}
        or any(f.endswith(p) for p in largest_paths)
        for f in touched_files
    )

    risk_level = "low"
    if touches_hotspot or max_gravity > 0.8:
        risk_level = "high"
    elif touches_large_file or max_gravity > 0.5:
        risk_level = "medium"

    return {
        "risk_level": risk_level,
        "touched_files": len(touched_files),
        "max_gravity": round(max_gravity, 2),
        "touches_hotspot": touches_hotspot,
        "touches_large_file": touches_large_file,
        "gravity_details": touched_gravity,
    }
