"""
Proposal Change Analysis and Risk Assessment

Analyzes proposals to compute change metrics and risk levels.
Works with app layer only - does not modify kernel.
"""
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


def compute_change_summary(proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute change metrics from proposals.

    Returns:
        {
            "files_changed": int,
            "lines_added": int,
            "lines_removed": int,
            "write_operations": bool,
            "affected_files": [list of file paths]
        }
    """
    files_changed = set()
    lines_added = 0
    lines_removed = 0
    write_operations = False
    affected_files = []

    for proposal in proposals:
        action = proposal.get("action", "").lower()
        target = proposal.get("target", "")

        if action in ("write", "edit", "create", "append", "delete", "rename"):
            write_operations = True
            if target and target not in files_changed:
                files_changed.add(target)
                affected_files.append(target)

        if action == "write" or action == "edit":
            proposal_data = proposal.get("proposal", {})
            if isinstance(proposal_data, dict):
                old_content = proposal_data.get("old_content", "")
                new_content = proposal_data.get("new_content", "")

                old_lines = old_content.split("\n") if old_content else []
                new_lines = new_content.split("\n") if new_content else []

                for line in old_lines:
                    if line.strip():
                        lines_removed += 1

                for line in new_lines:
                    if line.strip():
                        lines_added += 1

    return {
        "files_changed": len(files_changed),
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "write_operations": write_operations,
        "affected_files": sorted(affected_files),
    }


def assess_proposal_risk(
    proposals: List[Dict[str, Any]],
    run_data: Dict[str, Any],
    review_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assess risk level of a proposal.

    Risk levels:
    - LOW: read-only operations only
    - MEDIUM: write operations but trust requirements met
    - HIGH: write operations with trust escalation

    Returns:
        {
            "level": "LOW" | "MEDIUM" | "HIGH",
            "reasons": [list of risk factors],
            "write_operations": bool,
            "trust_required": bool,
            "trust_satisfied": bool
        }
    """
    reasons = []
    write_operations = False
    trust_required = False
    trust_satisfied = False

    for proposal in proposals:
        action = proposal.get("action", "").lower()

        if action in ("write", "edit", "create", "append", "delete", "rename"):
            write_operations = True
            reasons.append(f"Proposes {action} operation")

            if proposal.get("trust_required", False):
                trust_required = True
                reasons.append("Trust required for this operation")

    if review_data:
        trust_satisfied = review_data.get("trust_satisfied", False)
        if trust_required and trust_satisfied:
            reasons.append("Trust requirement satisfied")

    level = RiskLevel.LOW.value
    if write_operations:
        if trust_required and not trust_satisfied:
            level = RiskLevel.HIGH.value
        else:
            level = RiskLevel.MEDIUM.value

    return {
        "level": level,
        "reasons": reasons,
        "write_operations": write_operations,
        "trust_required": trust_required,
        "trust_satisfied": trust_satisfied,
    }


def generate_unified_diff_preview(proposals: List[Dict[str, Any]], max_lines: int = 300) -> str:
    """
    Generate a unified diff preview from proposals.

    Limits output to max_lines to prevent huge diffs.

    Returns:
        Diff string or empty string if no write operations
    """
    diff_lines = []
    line_count = 0
    has_more = False

    for proposal in proposals:
        if line_count > max_lines:
            has_more = True
            break

        action = proposal.get("action", "").lower()
        target = proposal.get("target", "")

        if action not in ("write", "edit"):
            continue

        proposal_data = proposal.get("proposal", {})
        if not isinstance(proposal_data, dict):
            continue

        old_content = proposal_data.get("old_content", "")
        new_content = proposal_data.get("new_content", "")

        if not target:
            target = "file"

        diff_lines.append(f"--- a/{target}")
        diff_lines.append(f"+++ b/{target}")
        line_count += 2

        old_lines = old_content.split("\n") if old_content else []
        new_lines = new_content.split("\n") if new_content else []

        max(len(old_lines), len(new_lines))

        for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines)):
            if line_count > max_lines:
                has_more = True
                break

            if old_line != new_line:
                diff_lines.append(f"- {old_line}")
                diff_lines.append(f"+ {new_line}")
                line_count += 2

        if len(new_lines) > len(old_lines):
            for new_line in new_lines[len(old_lines):]:
                if line_count > max_lines:
                    has_more = True
                    break
                diff_lines.append(f"+ {new_line}")
                line_count += 1

        if len(old_lines) > len(new_lines):
            for old_line in old_lines[len(new_lines):]:
                if line_count > max_lines:
                    has_more = True
                    break
                diff_lines.append(f"- {old_line}")
                line_count += 1

        diff_lines.append("")

    result = "\n".join(diff_lines)

    if has_more:
        result += f"\n[... diff truncated at {max_lines} lines ...]"

    return result.strip()
