#!/usr/bin/env python3
"""
Lightweight verification script for Lathe subsystems (no pytest required).

Runs basic checks on:
1. Import independence
2. Interface existence
3. Statefulness
4. Shared model usage
"""

import sys
import os
import traceback
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Verifier:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str, func):
        """Run a single test."""
        try:
            func()
            self.passed += 1
            self.results.append((name, True, None))
            print(f"✓ {name}")
        except Exception as e:
            self.failed += 1
            self.results.append((name, False, str(e)))
            print(f"✗ {name}: {e}")

    def report(self):
        """Print summary."""
        print(f"\n{'='*60}")
        print(f"VERIFICATION SUMMARY")
        print(f"{'='*60}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        print(f"{'='*60}")
        return self.failed == 0


def test_prompts_import():
    """Test: Can import prompts subsystem independently."""
    from lathe.prompts import PromptRegistry, Prompt
    assert PromptRegistry is not None
    assert Prompt is not None


def test_context_import():
    """Test: Can import context subsystem independently."""
    from lathe.context import ContextBuilder, SourceFilter
    assert ContextBuilder is not None
    assert SourceFilter is not None


def test_validation_import():
    """Test: Can import validation subsystem independently."""
    from lathe.validation import ValidationEngine
    assert ValidationEngine is not None


def test_shared_models_import():
    """Test: Can import shared models."""
    from lathe.shared.models import (
        PromptMetadata,
        ContextSource,
        ContextOutput,
        ValidationResult,
    )
    assert all(
        [
            PromptMetadata,
            ContextSource,
            ContextOutput,
            ValidationResult,
        ]
    )


def test_shared_enums_import():
    """Test: Can import shared enums."""
    from lathe.shared.enums import (
        ValidationLevel,
        ContextSourceType,
        PromptScope,
    )
    assert all([ValidationLevel, ContextSourceType, PromptScope])


def test_prompts_registry_interface():
    """Test: PromptRegistry has required methods."""
    from lathe.prompts import PromptRegistry

    registry = PromptRegistry()
    required_methods = [
        "register",
        "get_prompt",
        "list_prompts",
        "list_versions",
        "delete_prompt",
        "count_prompts",
    ]
    for method in required_methods:
        assert hasattr(registry, method), f"Missing method: {method}"


def test_context_builder_interface():
    """Test: ContextBuilder has required methods."""
    from lathe.context import ContextBuilder

    builder = ContextBuilder()
    required_methods = ["build", "get_source_stats", "truncate_content"]
    for method in required_methods:
        assert hasattr(builder, method), f"Missing method: {method}"


def test_validation_engine_interface():
    """Test: ValidationEngine has required methods."""
    from lathe.validation import ValidationEngine

    engine = ValidationEngine()
    required_methods = ["validate", "get_validation_summary"]
    for method in required_methods:
        assert hasattr(engine, method), f"Missing method: {method}"


def test_prompts_register_and_retrieve():
    """Test: Can register and retrieve prompts."""
    from lathe.prompts import PromptRegistry, Prompt
    from lathe.shared.enums import PromptScope
    from lathe.shared.models import PromptMetadata

    registry = PromptRegistry()
    prompt = Prompt(
        id="test", name="Test", content="content", version="1.0"
    )

    # Register returns PromptMetadata
    metadata = registry.register(prompt, scope=PromptScope.GLOBAL)
    assert isinstance(metadata, PromptMetadata)
    assert metadata.id == "test"

    # Retrieve returns Prompt
    retrieved = registry.get_prompt("test")
    assert retrieved is not None
    assert retrieved.id == "test"


def test_context_build():
    """Test: Can build context from sources."""
    from lathe.context import ContextBuilder
    from lathe.shared.models import ContextSource, ContextOutput
    from lathe.shared.enums import ContextSourceType

    builder = ContextBuilder()
    sources = [
        ContextSource(
            type=ContextSourceType.FILE,
            identifier="test.py",
            content="def test(): pass",
            priority=100,
        )
    ]

    output = builder.build(sources)
    assert isinstance(output, ContextOutput)
    assert hasattr(output, "assembled_content")
    assert hasattr(output, "sources_used")
    assert hasattr(output, "total_tokens_estimated")


def test_validation_validate():
    """Test: Can validate content with rules."""
    from lathe.validation import ValidationEngine
    from lathe.validation.rules import FullFileReplacementRule
    from lathe.shared.models import ValidationResult
    from lathe.shared.enums import ValidationLevel

    engine = ValidationEngine()
    rule = FullFileReplacementRule(severity=ValidationLevel.FAIL)
    result = engine.validate("def foo(): pass", [rule])

    assert isinstance(result, ValidationResult)
    assert hasattr(result, "overall_level")
    assert result.overall_level in [
        ValidationLevel.PASS,
        ValidationLevel.WARN,
        ValidationLevel.FAIL,
    ]


def test_no_cross_imports_prompts():
    """Test: Prompts subsystem doesn't import context or validation."""
    import lathe.prompts.registry

    source = open(lathe.prompts.registry.__file__).read()
    assert "from lathe.context" not in source, "prompts imports context"
    assert "from lathe.validation" not in source, "prompts imports validation"


def test_no_cross_imports_context():
    """Test: Context subsystem doesn't import prompts or validation."""
    import lathe.context.builder

    source = open(lathe.context.builder.__file__).read()
    assert "from lathe.prompts" not in source, "context imports prompts"
    assert "from lathe.validation" not in source, "context imports validation"


def test_no_cross_imports_validation():
    """Test: Validation subsystem doesn't import prompts or context."""
    import lathe.validation.engine

    source = open(lathe.validation.engine.__file__).read()
    assert "from lathe.prompts" not in source, "validation imports prompts"
    assert "from lathe.context" not in source, "validation imports context"


def test_stateless_prompts():
    """Test: PromptRegistry is stateless."""
    from lathe.prompts import PromptRegistry

    reg1 = PromptRegistry()
    reg2 = PromptRegistry()

    assert reg1.count_prompts() == 0
    assert reg2.count_prompts() == 0

    from lathe.prompts.schemas import Prompt

    p = Prompt(id="x", name="X", content="test", version="1.0")
    reg1.register(p)

    assert reg1.count_prompts() == 1
    assert reg2.count_prompts() == 0


def test_stateless_context():
    """Test: ContextBuilder is stateless."""
    from lathe.context import ContextBuilder
    from lathe.shared.models import ContextSource
    from lathe.shared.enums import ContextSourceType

    builder = ContextBuilder()

    source1 = ContextSource(
        type=ContextSourceType.FILE,
        identifier="a",
        content="aaa",
        priority=100,
    )
    source2 = ContextSource(
        type=ContextSourceType.FILE,
        identifier="b",
        content="bbb",
        priority=100,
    )

    output1 = builder.build([source1])
    output2 = builder.build([source2])

    assert output1.sources_used != output2.sources_used


def test_no_persistence_imports():
    """Test: No subsystem imports database or ledger libraries at top level."""
    # This check specifically looks for top-level persistence imports that break statelessness
    import lathe.prompts.registry
    import lathe.context.builder
    import lathe.validation.engine

    for module in [
        lathe.prompts.registry,
        lathe.context.builder,
        lathe.validation.engine,
    ]:
        source = open(module.__file__).read()
        # Verify no database libs
        assert "import sqlite" not in source
        assert "supabase" not in source
        # verify no top-level ledger imports
        assert "from lathe.ledger import" not in source
        # verify no top-level storage imports
        assert "from lathe.storage" not in source


def test_validation_levels_exist():
    """Test: ValidationLevel enum has all required values."""
    from lathe.shared.enums import ValidationLevel

    assert hasattr(ValidationLevel, "PASS")
    assert hasattr(ValidationLevel, "WARN")
    assert hasattr(ValidationLevel, "FAIL")


def test_context_source_types_exist():
    """Test: ContextSourceType enum has all required values."""
    from lathe.shared.enums import ContextSourceType

    assert hasattr(ContextSourceType, "KNOWLEDGE")
    assert hasattr(ContextSourceType, "MEMORY")
    assert hasattr(ContextSourceType, "FILE")
    assert hasattr(ContextSourceType, "METADATA")
    assert hasattr(ContextSourceType, "CUSTOM")


def test_prompt_scopes_exist():
    """Test: PromptScope enum has all required values."""
    from lathe.shared.enums import PromptScope

    assert hasattr(PromptScope, "GLOBAL")
    assert hasattr(PromptScope, "PROJECT")
    assert hasattr(PromptScope, "TASK")
    assert hasattr(PromptScope, "CUSTOM")


def test_rule_implementations():
    """Test: Validation rule implementations exist."""
    from lathe.validation.rules import (
        FullFileReplacementRule,
        ExplicitAssumptionsRule,
        RequiredSectionRule,
        NoHallucinatedFilesRule,
        OutputFormatRule,
    )

    assert all(
        [
            FullFileReplacementRule,
            ExplicitAssumptionsRule,
            RequiredSectionRule,
            NoHallucinatedFilesRule,
            OutputFormatRule,
        ]
    )


def test_pipeline_support():
    """Test: Validation pipeline exists and works."""
    from lathe.validation.engine import (
        ValidationStage,
        ValidationPipeline,
    )
    from lathe.validation.rules import FullFileReplacementRule
    from lathe.shared.enums import ValidationLevel

    rule = FullFileReplacementRule(severity=ValidationLevel.FAIL)
    stage = ValidationStage("test_stage", [rule])
    pipeline = ValidationPipeline()
    pipeline.add_stage(stage)

    result = pipeline.execute("def test(): pass")
    assert result is not None


def main():
    """Run all verification tests."""
    verifier = Verifier()

    print("IMPORT TESTS")
    print("-" * 60)
    verifier.test("Import prompts subsystem", test_prompts_import)
    verifier.test("Import context subsystem", test_context_import)
    verifier.test("Import validation subsystem", test_validation_import)
    verifier.test("Import shared models", test_shared_models_import)
    verifier.test("Import shared enums", test_shared_enums_import)

    print("\nINTERFACE TESTS")
    print("-" * 60)
    verifier.test(
        "PromptRegistry interface exists", test_prompts_registry_interface
    )
    verifier.test(
        "ContextBuilder interface exists", test_context_builder_interface
    )
    verifier.test(
        "ValidationEngine interface exists",
        test_validation_engine_interface,
    )

    print("\nFUNCTIONAL TESTS")
    print("-" * 60)
    verifier.test("Register and retrieve prompts", test_prompts_register_and_retrieve)
    verifier.test("Build context from sources", test_context_build)
    verifier.test("Validate content with rules", test_validation_validate)

    print("\nARCHITECTURE COMPLIANCE TESTS")
    print("-" * 60)
    verifier.test(
        "No cross-imports (prompts)",
        test_no_cross_imports_prompts,
    )
    verifier.test(
        "No cross-imports (context)",
        test_no_cross_imports_context,
    )
    verifier.test(
        "No cross-imports (validation)",
        test_no_cross_imports_validation,
    )
    verifier.test(
        "No persistence imports",
        test_no_persistence_imports,
    )

    print("\nSTATELESSNESS TESTS")
    print("-" * 60)
    verifier.test("PromptRegistry is stateless", test_stateless_prompts)
    verifier.test("ContextBuilder is stateless", test_stateless_context)

    print("\nENUM AND CONSTANT TESTS")
    print("-" * 60)
    verifier.test("ValidationLevel values exist", test_validation_levels_exist)
    verifier.test("ContextSourceType values exist", test_context_source_types_exist)
    verifier.test("PromptScope values exist", test_prompt_scopes_exist)

    print("\nEXTENSION FEATURE TESTS")
    print("-" * 60)
    verifier.test("Validation rule implementations", test_rule_implementations)
    verifier.test("Validation pipeline support", test_pipeline_support)

    success = verifier.report()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
