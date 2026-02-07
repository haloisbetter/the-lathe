"""
Tool Registry

Deterministic, read-only registry of available tools.
Each tool is described by a ToolSpec dataclass.
The registry is a static list — no runtime registration, no mutation.

Tools are NOT agents. Tools do NOT reason. Tools are pure capability adapters.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolSpec:
    id: str
    category: str
    description: str
    read_only: bool
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    trust_required: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "read_only": self.read_only,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "trust_required": self.trust_required,
        }


TOOL_REGISTRY: List[ToolSpec] = [
    ToolSpec(
        id="fs_tree",
        category="filesystem",
        description="List files in a workspace, optionally filtered by extension.",
        read_only=True,
        inputs={
            "workspace": {"type": "string", "required": True, "description": "Workspace ID"},
            "ext": {"type": "string", "required": False, "description": "File extension filter (e.g. .py)"},
        },
        outputs={
            "files": {"type": "array", "description": "List of relative file paths"},
            "count": {"type": "integer", "description": "Number of files found"},
        },
        trust_required=0,
    ),
    ToolSpec(
        id="fs_stats",
        category="filesystem",
        description="Count files by extension in a workspace.",
        read_only=True,
        inputs={
            "workspace": {"type": "string", "required": True, "description": "Workspace ID"},
        },
        outputs={
            "extensions": {"type": "object", "description": "Extension → count mapping"},
            "total_files": {"type": "integer", "description": "Total file count"},
        },
        trust_required=0,
    ),
    ToolSpec(
        id="git_status",
        category="git",
        description="Read-only git status summary for a workspace.",
        read_only=True,
        inputs={
            "workspace": {"type": "string", "required": True, "description": "Workspace ID"},
        },
        outputs={
            "clean": {"type": "boolean", "description": "Whether the working tree is clean"},
            "branch": {"type": "string", "description": "Current branch name"},
            "stdout": {"type": "string", "description": "Raw git status output"},
        },
        trust_required=0,
    ),
]


def get_tool_spec(tool_id: str) -> Optional[ToolSpec]:
    for tool in TOOL_REGISTRY:
        if tool.id == tool_id:
            return tool
    return None
