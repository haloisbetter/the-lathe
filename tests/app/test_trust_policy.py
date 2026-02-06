"""
Tests for graduated trust policies.

Proves:
1) Trust level 0 always requires approval
2) Trust level 4 always auto-approves
3) Docs-only changes auto-approved at level 1+ with allow_docs_only
4) Tests-only changes auto-approved at level 2+ with allow_tests_only
5) Single-module changes auto-approved at level 3 with allow_single_module_only
6) Outside-workspace paths denied
7) File count threshold enforced
8) Trust policy loads from JSON file
"""
import json
import os
import pytest
from lathe_app.trust import (
    TrustPolicy,
    TrustEvaluation,
    evaluate_trust,
)


class TestTrustPolicy:
    def test_default_policy(self):
        p = TrustPolicy.default()
        assert p.trust_level == 0
        assert p.deny_outside_workspace is True

    def test_to_dict(self):
        p = TrustPolicy(trust_level=2, allow_docs_only=True)
        d = p.to_dict()
        assert d["trust_level"] == 2
        assert d["allow_docs_only"] is True

    def test_from_dict(self):
        p = TrustPolicy.from_dict({"trust_level": 3, "max_files_changed": 5})
        assert p.trust_level == 3
        assert p.max_files_changed == 5

    def test_load_from_workspace_missing(self, tmp_path):
        p = TrustPolicy.load_from_workspace(str(tmp_path))
        assert p.trust_level == 0

    def test_load_from_workspace_file(self, tmp_path):
        lathe_dir = tmp_path / ".lathe"
        lathe_dir.mkdir()
        trust_file = lathe_dir / "trust.json"
        trust_file.write_text(json.dumps({
            "trust_level": 2,
            "allow_docs_only": True,
            "max_files_changed": 10,
        }))
        p = TrustPolicy.load_from_workspace(str(tmp_path))
        assert p.trust_level == 2
        assert p.allow_docs_only is True
        assert p.max_files_changed == 10

    def test_load_from_workspace_bad_json(self, tmp_path):
        lathe_dir = tmp_path / ".lathe"
        lathe_dir.mkdir()
        trust_file = lathe_dir / "trust.json"
        trust_file.write_text("NOT JSON")
        p = TrustPolicy.load_from_workspace(str(tmp_path))
        assert p.trust_level == 0


class TestEvaluateTrust:
    def test_level_0_always_requires_approval(self):
        policy = TrustPolicy(trust_level=0)
        result = evaluate_trust(policy, ["README.md"])
        assert result.allowed is False
        assert "explicit approval" in result.reason.lower()

    def test_level_4_always_approves(self):
        policy = TrustPolicy(trust_level=4)
        result = evaluate_trust(policy, ["anything.py", "whatever.js"])
        assert result.allowed is True
        assert "full autonomy" in result.reason.lower()

    def test_docs_only_approved_at_level_1(self):
        policy = TrustPolicy(trust_level=1, allow_docs_only=True)
        result = evaluate_trust(policy, ["README.md", "docs/guide.txt"])
        assert result.allowed is True
        assert "docs-only" in result.reason.lower()

    def test_docs_only_denied_without_flag(self):
        policy = TrustPolicy(trust_level=1, allow_docs_only=False)
        result = evaluate_trust(policy, ["README.md"])
        assert result.allowed is False

    def test_mixed_files_not_docs_only(self):
        policy = TrustPolicy(trust_level=1, allow_docs_only=True)
        result = evaluate_trust(policy, ["README.md", "main.py"])
        assert result.allowed is False

    def test_tests_only_approved_at_level_2(self):
        policy = TrustPolicy(trust_level=2, allow_tests_only=True)
        result = evaluate_trust(policy, ["tests/test_main.py", "test_utils.py"])
        assert result.allowed is True
        assert "tests-only" in result.reason.lower()

    def test_tests_denied_at_level_1(self):
        policy = TrustPolicy(trust_level=1, allow_tests_only=True)
        result = evaluate_trust(policy, ["tests/test_main.py"])
        assert result.allowed is False

    def test_single_module_at_level_3(self):
        policy = TrustPolicy(trust_level=3, allow_single_module_only=True)
        result = evaluate_trust(policy, ["src/a.py", "src/b.py"])
        assert result.allowed is True
        assert "single-module" in result.reason.lower()

    def test_multi_module_denied_at_level_3(self):
        policy = TrustPolicy(trust_level=3, allow_single_module_only=True)
        result = evaluate_trust(policy, ["src/a.py", "lib/b.py"])
        assert result.allowed is False

    def test_outside_workspace_denied(self):
        policy = TrustPolicy(trust_level=4, deny_outside_workspace=True)
        result = evaluate_trust(
            policy,
            ["/etc/passwd"],
            workspace_root="/home/user/project",
        )
        assert result.allowed is False
        assert "outside workspace" in result.reason.lower()

    def test_max_files_threshold(self):
        policy = TrustPolicy(
            trust_level=1,
            allow_docs_only=True,
            max_files_changed=2,
        )
        result = evaluate_trust(policy, ["a.md", "b.md", "c.md"])
        assert result.allowed is False
        assert any("too_many_files" in c for c in result.checks_failed)

    def test_evaluation_to_dict(self):
        policy = TrustPolicy(trust_level=0)
        result = evaluate_trust(policy, ["test.py"])
        d = result.to_dict()
        assert "allowed" in d
        assert "reason" in d
        assert "policy" in d
        assert "checks_passed" in d
        assert "checks_failed" in d
