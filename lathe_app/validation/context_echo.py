"""
Context Echo Validator

Deterministic structural validation of the Context Echo Block
in agent responses. Enforces the Agent Contract requirement that
every response must declare its context before reasoning.

Validation rules:
1. The block MUST exist (delimited by CONTEXT_ECHO_START / CONTEXT_ECHO_END)
2. Required fields: Workspace, Snapshot, Files
3. Any file path referenced elsewhere in the response MUST appear in Files

On failure: returns a structured ContextEchoViolation with WHY record.
No semantic judgment. No retries. No reframing. No model escalation.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


ECHO_START = "--- CONTEXT_ECHO_START ---"
ECHO_END = "--- CONTEXT_ECHO_END ---"

_FILE_PATH_PATTERN = re.compile(
    r'(?:^|[\s"\'`(,])('
    r'[a-zA-Z0-9_.][a-zA-Z0-9_./\-]*'
    r'\.[a-zA-Z0-9]{1,10}'
    r')(?:[\s"\'`),:]|$)',
    re.MULTILINE,
)

REQUIRED_FIELDS = frozenset({"workspace", "snapshot", "files"})

_FIELD_ALIASES = {
    "workspace": {"workspace"},
    "snapshot": {"snapshot", "snapshot id", "snapshot_id"},
    "files": {"files", "files available"},
}

_NON_FILE_EXTENSIONS = frozenset({
    ".com", ".org", ".net", ".io", ".dev", ".app", ".ai",
})


@dataclass
class ContextEchoViolation:
    rule: str
    detail: str


@dataclass
class ContextEchoResult:
    valid: bool
    violations: List[ContextEchoViolation] = field(default_factory=list)
    workspace: Optional[str] = None
    snapshot: Optional[str] = None
    files: List[str] = field(default_factory=list)

    def why(self) -> List[dict]:
        return [
            {"rule": v.rule, "detail": v.detail}
            for v in self.violations
        ]


def _extract_echo_block(text: str) -> Optional[str]:
    start = text.find(ECHO_START)
    if start == -1:
        return None
    end = text.find(ECHO_END, start)
    if end == -1:
        return None
    return text[start + len(ECHO_START):end].strip()


def _parse_fields(block: str) -> dict:
    fields = {}
    current_key = None
    current_items = []

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("---"):
            continue

        if ":" in stripped and not stripped.startswith("-"):
            if current_key is not None:
                fields[current_key] = current_items
            key_part, _, value_part = stripped.partition(":")
            normalized = key_part.strip().lower()
            for canonical, aliases in _FIELD_ALIASES.items():
                if normalized in aliases:
                    normalized = canonical
                    break
            current_key = normalized
            val = value_part.strip()
            current_items = [val] if val and val != "-" else []
        elif stripped.startswith("-") and current_key is not None:
            item = stripped.lstrip("-").strip()
            if item:
                current_items.append(item)

    if current_key is not None:
        fields[current_key] = current_items

    return fields


def _extract_file_paths(text: str) -> List[str]:
    paths = set()
    for match in _FILE_PATH_PATTERN.finditer(text):
        candidate = match.group(1)
        if "/" in candidate:
            ext = "." + candidate.rsplit(".", 1)[-1].lower() if "." in candidate else ""
            if ext not in _NON_FILE_EXTENSIONS:
                paths.add(candidate)
    return sorted(paths)


def _normalize_echo_path(raw: str) -> str:
    path = raw.strip()
    if " " in path:
        path = path.split()[0]
    return path


def validate_context_echo(response_text: str) -> ContextEchoResult:
    violations: List[ContextEchoViolation] = []

    block = _extract_echo_block(response_text)
    if block is None:
        violations.append(ContextEchoViolation(
            rule="echo_block_missing",
            detail="Response does not contain a Context Echo Block "
                   f"(delimited by '{ECHO_START}' and '{ECHO_END}').",
        ))
        return ContextEchoResult(valid=False, violations=violations)

    fields = _parse_fields(block)

    for required in REQUIRED_FIELDS:
        if required not in fields:
            violations.append(ContextEchoViolation(
                rule="missing_field",
                detail=f"Required field '{required}' is missing from the Context Echo Block.",
            ))

    if violations:
        return ContextEchoResult(valid=False, violations=violations)

    workspace_val = fields.get("workspace", ["NONE"])
    workspace = workspace_val[0] if workspace_val else "NONE"

    snapshot_val = fields.get("snapshot", ["NONE"])
    snapshot = snapshot_val[0] if snapshot_val else "NONE"

    echo_files_raw = fields.get("files", [])
    echo_files = [_normalize_echo_path(f) for f in echo_files_raw]

    echo_end_pos = response_text.find(ECHO_END)
    reasoning_text = response_text[echo_end_pos + len(ECHO_END):]

    referenced_paths = _extract_file_paths(reasoning_text)

    echo_set = set(echo_files)
    for ref_path in referenced_paths:
        if ref_path not in echo_set:
            matched = False
            for ep in echo_set:
                if ep.endswith(ref_path) or ref_path.endswith(ep):
                    matched = True
                    break
            if not matched:
                violations.append(ContextEchoViolation(
                    rule="undeclared_file_reference",
                    detail=f"File '{ref_path}' is referenced in the response "
                           f"but not declared in the Context Echo Block.",
                ))

    return ContextEchoResult(
        valid=len(violations) == 0,
        violations=violations,
        workspace=workspace,
        snapshot=snapshot,
        files=echo_files,
    )
