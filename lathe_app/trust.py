"""
Graduated Trust Policies

Declarative per-workspace auto-approve rules.
Trust levels 0-4 control how much autonomy the system gets.

Level 0: Always require explicit approval (default)
Level 1: Auto-approve read-only / informational
Level 2: Auto-approve docs + tests only
Level 3: Auto-approve single-module changes within thresholds
Level 4: Full autonomy (explicit opt-in)

Evaluation happens ONLY in the app layer.
Executor runs ONLY if policy allows OR explicit approval provided.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrustPolicy:
    trust_level: int = 0
    allow_docs_only: bool = False
    allow_tests_only: bool = False
    allow_single_module_only: bool = False
    deny_new_dependencies: bool = True
    deny_outside_workspace: bool = True
    max_files_changed: int = 0
    max_gravity: float = 0.0
    max_file_size_kb: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trust_level": self.trust_level,
            "allow_docs_only": self.allow_docs_only,
            "allow_tests_only": self.allow_tests_only,
            "allow_single_module_only": self.allow_single_module_only,
            "deny_new_dependencies": self.deny_new_dependencies,
            "deny_outside_workspace": self.deny_outside_workspace,
            "max_files_changed": self.max_files_changed,
            "max_gravity": self.max_gravity,
            "max_file_size_kb": self.max_file_size_kb,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustPolicy":
        return cls(
            trust_level=data.get("trust_level", 0),
            allow_docs_only=data.get("allow_docs_only", False),
            allow_tests_only=data.get("allow_tests_only", False),
            allow_single_module_only=data.get("allow_single_module_only", False),
            deny_new_dependencies=data.get("deny_new_dependencies", True),
            deny_outside_workspace=data.get("deny_outside_workspace", True),
            max_files_changed=data.get("max_files_changed", 0),
            max_gravity=data.get("max_gravity", 0.0),
            max_file_size_kb=data.get("max_file_size_kb", 0),
        )

    @classmethod
    def default(cls) -> "TrustPolicy":
        return cls(trust_level=0)

    @classmethod
    def load_from_workspace(cls, workspace_root: str) -> "TrustPolicy":
        trust_file = os.path.join(workspace_root, ".lathe", "trust.json")
        if not os.path.isfile(trust_file):
            return cls.default()
        try:
            with open(trust_file, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return cls.default()


DOC_EXTENSIONS = frozenset({".md", ".txt", ".rst", ".adoc"})
TEST_PATTERNS = frozenset({"test_", "_test.", "tests/", "test/"})


@dataclass
class TrustEvaluation:
    allowed: bool
    reason: str
    policy: TrustPolicy
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "policy": self.policy.to_dict(),
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
        }


def evaluate_trust(
    policy: TrustPolicy,
    touched_files: List[str],
    workspace_root: Optional[str] = None,
    gravity_scores: Optional[Dict[str, float]] = None,
) -> TrustEvaluation:
    if policy.trust_level == 0:
        return TrustEvaluation(
            allowed=False,
            reason="Trust level 0: explicit approval required",
            policy=policy,
        )

    checks_passed = []
    checks_failed = []

    if policy.deny_outside_workspace and workspace_root:
        abs_root = os.path.abspath(workspace_root)
        for f in touched_files:
            abs_f = os.path.abspath(f)
            if not abs_f.startswith(abs_root + os.sep) and abs_f != abs_root:
                checks_failed.append(f"outside_workspace: {f}")
        if not checks_failed:
            checks_passed.append("within_workspace")

    if checks_failed:
        return TrustEvaluation(
            allowed=False,
            reason="Files outside workspace boundary",
            policy=policy,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    if policy.trust_level >= 4:
        return TrustEvaluation(
            allowed=True,
            reason="Trust level 4: full autonomy",
            policy=policy,
            checks_passed=checks_passed + ["full_autonomy"],
            checks_failed=checks_failed,
        )

    if policy.max_files_changed > 0 and len(touched_files) > policy.max_files_changed:
        checks_failed.append(f"too_many_files: {len(touched_files)} > {policy.max_files_changed}")
    else:
        checks_passed.append("file_count_ok")

    if policy.max_gravity > 0 and gravity_scores:
        max_grav = max(gravity_scores.values()) if gravity_scores else 0
        if max_grav > policy.max_gravity:
            checks_failed.append(f"gravity_exceeded: {max_grav} > {policy.max_gravity}")
        else:
            checks_passed.append("gravity_ok")

    if policy.trust_level >= 1:
        if _all_docs(touched_files) and policy.allow_docs_only:
            checks_passed.append("docs_only")
            if not checks_failed:
                return TrustEvaluation(
                    allowed=True,
                    reason="Trust level 1+: docs-only change auto-approved",
                    policy=policy,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )

    if policy.trust_level >= 2:
        if _all_tests(touched_files) and policy.allow_tests_only:
            checks_passed.append("tests_only")
            if not checks_failed:
                return TrustEvaluation(
                    allowed=True,
                    reason="Trust level 2+: tests-only change auto-approved",
                    policy=policy,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )

    if policy.trust_level >= 3:
        if _single_module(touched_files) and policy.allow_single_module_only:
            checks_passed.append("single_module")
            if not checks_failed:
                return TrustEvaluation(
                    allowed=True,
                    reason="Trust level 3: single-module change auto-approved",
                    policy=policy,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )

    if checks_failed:
        return TrustEvaluation(
            allowed=False,
            reason="Policy checks failed",
            policy=policy,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    return TrustEvaluation(
        allowed=False,
        reason=f"Trust level {policy.trust_level}: no matching auto-approve rule",
        policy=policy,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
    )


def _all_docs(files: List[str]) -> bool:
    if not files:
        return False
    return all(
        os.path.splitext(f)[1].lower() in DOC_EXTENSIONS
        for f in files
    )


def _all_tests(files: List[str]) -> bool:
    if not files:
        return False
    return all(
        any(p in f.lower() for p in TEST_PATTERNS)
        for f in files
    )


def _single_module(files: List[str]) -> bool:
    if not files:
        return False
    dirs = set()
    for f in files:
        parts = os.path.normpath(f).split(os.sep)
        if len(parts) > 1:
            dirs.add(parts[0])
        else:
            dirs.add(".")
    return len(dirs) <= 1
