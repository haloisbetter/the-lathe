"""
Tests for the Lathe OpenWebUI tool wrapper.

Verifies:
1. All three functions are callable
2. Functions accept expected inputs
3. Functions return structured outputs
4. Error handling works correctly
5. Phase discipline is enforced
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestToolWrapper:
    """Test the OpenWebUI tool wrapper."""

    def test_import_tool_functions(self):
        """Test: Can import all three tool functions."""
        from lathe.tool import lathe_plan, lathe_validate, lathe_context_preview

        assert callable(lathe_plan)
        assert callable(lathe_validate)
        assert callable(lathe_context_preview)

    def test_lathe_plan_basic(self):
        """Test: lathe_plan returns structured output."""
        from lathe.tool import lathe_plan

        result = lathe_plan(
            project="test_project",
            scope="test_scope",
            phase="analysis",
            goal="Test goal",
        )

        # Check result structure
        assert isinstance(result, dict)
        assert "phase" in result
        assert "system_prompt" in result
        assert "context_blocks" in result
        assert "rules" in result
        assert "risks" in result
        assert "ready" in result

        # Check phase value
        assert result["phase"] == "analysis"
        assert result["ready"] is True

        # Check system prompt is non-empty
        assert isinstance(result["system_prompt"], str)
        assert len(result["system_prompt"]) > 0

        # Check context blocks
        assert isinstance(result["context_blocks"], list)
        assert len(result["context_blocks"]) > 0
        for block in result["context_blocks"]:
            assert "type" in block
            assert "content" in block
            assert "metadata" in block

        # Check rules and risks
        assert isinstance(result["rules"], list)
        assert isinstance(result["risks"], list)

    def test_lathe_plan_all_phases(self):
        """Test: lathe_plan works for all valid phases."""
        from lathe.tool import lathe_plan

        phases = ["analysis", "design", "implementation", "validation", "hardening"]

        for phase in phases:
            result = lathe_plan(
                project="test",
                scope="test",
                phase=phase,
                goal="Test",
            )

            assert result.get("ready") is True
            assert result.get("phase") == phase
            assert isinstance(result.get("rules"), list)
            assert len(result.get("rules", [])) > 0

    def test_lathe_plan_invalid_phase(self):
        """Test: lathe_plan rejects invalid phases."""
        from lathe.tool import lathe_plan

        result = lathe_plan(
            project="test",
            scope="test",
            phase="invalid_phase",
            goal="Test",
        )

        # Should return error structure
        assert result.get("status") == "fail"
        assert result.get("error_type") == "PHASE_VIOLATION"
        assert "Invalid phase" in result.get("message", "")

    def test_lathe_plan_with_constraints_and_sources(self):
        """Test: lathe_plan accepts constraints and sources."""
        from lathe.tool import lathe_plan

        result = lathe_plan(
            project="test",
            scope="test",
            phase="design",
            goal="Test goal",
            constraints=["Constraint 1", "Constraint 2"],
            sources=["knowledge", "memory", "files"],
        )

        assert result.get("ready") is True
        assert "Constraint 1" in result.get("system_prompt", "")

    def test_lathe_validate_basic(self):
        """Test: lathe_validate returns structured output."""
        from lathe.tool import lathe_validate

        result = lathe_validate(
            phase="implementation",
            output="def test():\n    pass",
        )

        # Check result structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "violations" in result
        assert "summary" in result
        assert "can_proceed" in result

        # Check status values
        assert result["status"] in ["pass", "warn", "fail"]

        # Check violations
        assert isinstance(result["violations"], list)

        # Check can_proceed
        assert isinstance(result["can_proceed"], bool)

    def test_lathe_validate_all_phases(self):
        """Test: lathe_validate works for all valid phases."""
        from lathe.tool import lathe_validate

        phases = ["analysis", "design", "implementation", "validation", "hardening"]

        for phase in phases:
            result = lathe_validate(
                phase=phase,
                output="Test output",
            )

            assert result.get("status") in ["pass", "warn", "fail"]
            assert isinstance(result.get("violations"), list)

    def test_lathe_validate_invalid_phase(self):
        """Test: lathe_validate rejects invalid phases."""
        from lathe.tool import lathe_validate

        result = lathe_validate(
            phase="invalid_phase",
            output="Test output",
        )

        # Should return error structure
        assert result.get("status") == "fail"
        assert result.get("error_type") == "PHASE_VIOLATION"

    def test_lathe_validate_with_ruleset(self):
        """Test: lathe_validate accepts custom ruleset."""
        from lathe.tool import lathe_validate

        result = lathe_validate(
            phase="implementation",
            output="def test():\n    pass",
            ruleset=["output_format", "full_file_replacement"],
        )

        assert result.get("status") in ["pass", "warn", "fail"]
        assert isinstance(result.get("violations"), list)

    def test_lathe_context_preview_basic(self):
        """Test: lathe_context_preview returns structured output."""
        from lathe.tool import lathe_context_preview

        result = lathe_context_preview(
            query="test query",
        )

        # Check result structure
        assert isinstance(result, dict)
        assert "context_blocks" in result
        assert "total_tokens" in result
        assert "truncated" in result

        # Check context blocks
        assert isinstance(result["context_blocks"], list)

        # Check token count
        assert isinstance(result["total_tokens"], int)
        assert result["total_tokens"] >= 0

        # Check truncated flag
        assert isinstance(result["truncated"], bool)

    def test_lathe_context_preview_with_sources(self):
        """Test: lathe_context_preview accepts different sources."""
        from lathe.tool import lathe_context_preview

        sources_options = [
            ["knowledge"],
            ["memory"],
            ["files"],
            ["knowledge", "memory"],
            ["knowledge", "memory", "files"],
        ]

        for sources in sources_options:
            result = lathe_context_preview(
                query="test",
                sources=sources,
            )

            assert result.get("status") != "fail" or "error_type" in result
            if result.get("status") != "fail":
                assert isinstance(result.get("context_blocks"), list)

    def test_lathe_context_preview_with_max_tokens(self):
        """Test: lathe_context_preview respects max_tokens."""
        from lathe.tool import lathe_context_preview

        result = lathe_context_preview(
            query="test",
            max_tokens=100,
        )

        assert result.get("total_tokens") <= 100 or result.get("truncated") is True

    def test_error_response_structure(self):
        """Test: Error responses have correct structure."""
        from lathe.tool import lathe_plan

        result = lathe_plan(
            project="test",
            scope="test",
            phase="invalid",
            goal="test",
        )

        # Check error structure
        assert result.get("status") == "fail"
        assert "error_type" in result
        assert "message" in result
        assert "details" in result

        # Check error_type values
        assert result.get("error_type") in [
            "PHASE_VIOLATION",
            "VALIDATION_ERROR",
            "INTERNAL_ERROR",
        ]

    def test_functions_are_stateless(self):
        """Test: Tool functions are stateless."""
        from lathe.tool import lathe_plan

        # Call same function twice with same input
        result1 = lathe_plan(
            project="test",
            scope="test",
            phase="analysis",
            goal="test",
        )

        result2 = lathe_plan(
            project="test",
            scope="test",
            phase="analysis",
            goal="test",
        )

        # Results should be identical
        assert result1.get("phase") == result2.get("phase")
        assert result1.get("ready") == result2.get("ready")

    def test_functions_return_json_serializable(self):
        """Test: All function outputs are JSON-serializable."""
        import json
        from lathe.tool import (
            lathe_plan,
            lathe_validate,
            lathe_context_preview,
        )

        # Test lathe_plan
        result = lathe_plan(
            project="test",
            scope="test",
            phase="analysis",
            goal="test",
        )
        try:
            json.dumps(result)
        except TypeError as e:
            raise AssertionError(f"lathe_plan output not JSON serializable: {e}")

        # Test lathe_validate
        result = lathe_validate(
            phase="analysis",
            output="test",
        )
        try:
            json.dumps(result)
        except TypeError as e:
            raise AssertionError(f"lathe_validate output not JSON serializable: {e}")

        # Test lathe_context_preview
        result = lathe_context_preview(
            query="test",
        )
        try:
            json.dumps(result)
        except TypeError as e:
            raise AssertionError(
                f"lathe_context_preview output not JSON serializable: {e}"
            )

    def test_context_preview_returns_previews(self):
        """Test: lathe_context_preview returns content previews."""
        from lathe.tool import lathe_context_preview

        result = lathe_context_preview(
            query="authentication",
            sources=["knowledge"],
        )

        if result.get("status") != "fail":
            # Check context blocks have preview
            for block in result.get("context_blocks", []):
                assert "source" in block
                assert "size_tokens" in block
                assert "preview" in block
                assert isinstance(block["preview"], str)


def run_all_tests():
    """Run all tests manually."""
    test = TestToolWrapper()
    tests = [
        ("Import tool functions", test.test_import_tool_functions),
        ("lathe_plan basic", test.test_lathe_plan_basic),
        ("lathe_plan all phases", test.test_lathe_plan_all_phases),
        ("lathe_plan invalid phase", test.test_lathe_plan_invalid_phase),
        ("lathe_plan with constraints", test.test_lathe_plan_with_constraints_and_sources),
        ("lathe_validate basic", test.test_lathe_validate_basic),
        ("lathe_validate all phases", test.test_lathe_validate_all_phases),
        ("lathe_validate invalid phase", test.test_lathe_validate_invalid_phase),
        ("lathe_validate with ruleset", test.test_lathe_validate_with_ruleset),
        ("lathe_context_preview basic", test.test_lathe_context_preview_basic),
        ("lathe_context_preview sources", test.test_lathe_context_preview_with_sources),
        ("lathe_context_preview max_tokens", test.test_lathe_context_preview_with_max_tokens),
        ("Error response structure", test.test_error_response_structure),
        ("Functions are stateless", test.test_functions_are_stateless),
        ("JSON serializable", test.test_functions_return_json_serializable),
        ("Context preview content", test.test_context_preview_returns_previews),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
