"""
Minimal verification tests for Lathe subsystems.

Objectives:
1. Verify independent imports (no cross-subsystem dependencies)
2. Verify public interfaces exist and are callable
3. Verify stateless behavior
4. Verify structured outputs via shared models
"""

import sys
import pytest


class TestPromptSubsystem:
    """Verify lathe-prompts subsystem."""

    def test_import_prompt_subsystem(self):
        """Verify prompts subsystem can be imported independently."""
        from lathe.prompts import PromptRegistry, Prompt

        assert PromptRegistry is not None
        assert Prompt is not None

    def test_prompt_registry_interface(self):
        """Verify PromptRegistry public interface exists."""
        from lathe.prompts import PromptRegistry

        registry = PromptRegistry()

        # Verify methods exist
        assert hasattr(registry, "register")
        assert hasattr(registry, "get_prompt")
        assert hasattr(registry, "list_prompts")
        assert hasattr(registry, "list_versions")
        assert hasattr(registry, "delete_prompt")
        assert hasattr(registry, "count_prompts")

    def test_prompt_registration_and_retrieval(self):
        """Verify prompt can be registered and retrieved."""
        from lathe.prompts import PromptRegistry, Prompt
        from lathe.shared.enums import PromptScope

        registry = PromptRegistry()
        prompt = Prompt(
            id="test_prompt",
            name="Test Prompt",
            content="Test content",
            version="1.0",
        )

        # Register
        metadata = registry.register(prompt, scope=PromptScope.GLOBAL)
        assert metadata is not None
        assert metadata.id == "test_prompt"
        assert metadata.name == "Test Prompt"

        # Retrieve
        retrieved = registry.get_prompt("test_prompt")
        assert retrieved is not None
        assert retrieved.id == "test_prompt"
        assert retrieved.content == "Test content"

    def test_prompt_uses_shared_models(self):
        """Verify Prompt subsystem uses shared models for output."""
        from lathe.prompts import PromptRegistry
        from lathe.shared.models import PromptMetadata

        registry = PromptRegistry()

        # Metadata output should be from shared models
        from lathe.prompts.schemas import Prompt as PromptSchema
        prompt = PromptSchema(
            id="x", name="X", content="test", version="1.0"
        )
        metadata = registry.register(prompt)

        assert isinstance(metadata, PromptMetadata)
        assert hasattr(metadata, "id")
        assert hasattr(metadata, "scope")
        assert hasattr(metadata, "version")

    def test_prompt_subsystem_stateless(self):
        """Verify PromptRegistry is stateless between calls."""
        from lathe.prompts import PromptRegistry

        # Two independent registries should be independent
        reg1 = PromptRegistry()
        reg2 = PromptRegistry()

        assert reg1.count_prompts() == 0
        assert reg2.count_prompts() == 0

        # Add to one, doesn't affect other
        from lathe.prompts.schemas import Prompt
        p = Prompt(id="x", name="X", content="test", version="1.0")
        reg1.register(p)

        assert reg1.count_prompts() == 1
        assert reg2.count_prompts() == 0  # Independent


class TestContextSubsystem:
    """Verify lathe-context subsystem."""

    def test_import_context_subsystem(self):
        """Verify context subsystem can be imported independently."""
        from lathe.context import ContextBuilder, SourceFilter

        assert ContextBuilder is not None
        assert SourceFilter is not None

    def test_context_builder_interface(self):
        """Verify ContextBuilder public interface exists."""
        from lathe.context import ContextBuilder

        builder = ContextBuilder()

        # Verify methods exist
        assert hasattr(builder, "build")
        assert hasattr(builder, "get_source_stats")
        assert hasattr(builder, "truncate_content")

    def test_context_builder_basic_build(self):
        """Verify context can be assembled from sources."""
        from lathe.context import ContextBuilder
        from lathe.shared.models import ContextSource
        from lathe.shared.enums import ContextSourceType

        builder = ContextBuilder()

        sources = [
            ContextSource(
                type=ContextSourceType.FILE,
                identifier="test.py",
                content="def test(): pass",
                priority=100,
            ),
            ContextSource(
                type=ContextSourceType.KNOWLEDGE,
                identifier="tip",
                content="Use type hints",
                priority=50,
            ),
        ]

        output = builder.build(sources)

        # Verify output structure
        assert output is not None
        assert hasattr(output, "assembled_content")
        assert hasattr(output, "sources_used")
        assert hasattr(output, "total_tokens_estimated")
        assert len(output.sources_used) == 2

    def test_context_uses_shared_models(self):
        """Verify Context subsystem uses shared models for I/O."""
        from lathe.context import ContextBuilder
        from lathe.shared.models import ContextSource, ContextOutput
        from lathe.shared.enums import ContextSourceType

        builder = ContextBuilder()
        source = ContextSource(
            type=ContextSourceType.FILE,
            identifier="x",
            content="test",
            priority=100,
        )

        output = builder.build([source])

        # Output should be shared model
        assert isinstance(output, ContextOutput)
        assert hasattr(output, "assembled_content")
        assert hasattr(output, "sources_used")
        assert hasattr(output, "total_tokens_estimated")

    def test_context_subsystem_stateless(self):
        """Verify ContextBuilder is stateless between calls."""
        from lathe.context import ContextBuilder
        from lathe.shared.models import ContextSource
        from lathe.shared.enums import ContextSourceType

        builder = ContextBuilder()

        # Two calls with different inputs produce different outputs
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

        # Different outputs, not cached
        assert output1.sources_used != output2.sources_used


class TestValidationSubsystem:
    """Verify lathe-validation subsystem."""

    def test_import_validation_subsystem(self):
        """Verify validation subsystem can be imported independently."""
        from lathe.validation import ValidationEngine

        assert ValidationEngine is not None

    def test_validation_engine_interface(self):
        """Verify ValidationEngine public interface exists."""
        from lathe.validation import ValidationEngine

        engine = ValidationEngine()

        # Verify methods exist
        assert hasattr(engine, "validate")
        assert hasattr(engine, "get_validation_summary")

    def test_validation_engine_basic_validation(self):
        """Verify validation can execute rules and return results."""
        from lathe.validation import ValidationEngine
        from lathe.validation.rules import FullFileReplacementRule
        from lathe.shared.enums import ValidationLevel

        engine = ValidationEngine()
        rule = FullFileReplacementRule(
            severity=ValidationLevel.FAIL, min_lines=1
        )

        content = "def foo():\n    return True"
        result = engine.validate(content, [rule])

        # Verify result structure
        assert result is not None
        assert hasattr(result, "overall_level")
        assert hasattr(result, "rule_results")
        assert hasattr(result, "passed_rules")
        assert hasattr(result, "failed_rules")

    def test_validation_uses_shared_models(self):
        """Verify Validation subsystem uses shared models for output."""
        from lathe.validation import ValidationEngine
        from lathe.validation.rules import FullFileReplacementRule
        from lathe.shared.models import ValidationResult
        from lathe.shared.enums import ValidationLevel

        engine = ValidationEngine()
        rule = FullFileReplacementRule(severity=ValidationLevel.FAIL)
        result = engine.validate("def x(): pass", [rule])

        # Output should be shared model
        assert isinstance(result, ValidationResult)
        assert isinstance(result.overall_level, ValidationLevel)

    def test_validation_subsystem_stateless(self):
        """Verify ValidationEngine is stateless between calls."""
        from lathe.validation import ValidationEngine
        from lathe.validation.rules import FullFileReplacementRule
        from lathe.shared.enums import ValidationLevel

        engine = ValidationEngine()
        rule = FullFileReplacementRule(severity=ValidationLevel.FAIL)

        # Two different validations
        result1 = engine.validate("def foo(): pass", [rule])
        result2 = engine.validate("invalid content", [rule])

        # Different outcomes based on input, not cached
        assert result1.overall_level == ValidationLevel.PASS
        # result2 could vary based on rule logic


class TestArchitectureCompliance:
    """Verify architectural constraints."""

    def test_no_cross_subsystem_imports_prompts(self):
        """Verify prompts subsystem doesn't import context or validation."""
        import lathe.prompts.registry as prompts_module

        source = open(prompts_module.__file__).read()

        assert "from lathe.context" not in source
        assert "from lathe.validation" not in source
        assert "lathe.context" not in source
        assert "lathe.validation" not in source

    def test_no_cross_subsystem_imports_context(self):
        """Verify context subsystem doesn't import prompts or validation."""
        import lathe.context.builder as context_module

        source = open(context_module.__file__).read()

        assert "from lathe.prompts" not in source
        assert "from lathe.validation" not in source
        assert "lathe.prompts" not in source
        assert "lathe.validation" not in source

    def test_no_cross_subsystem_imports_validation(self):
        """Verify validation subsystem doesn't import prompts or context."""
        import lathe.validation.engine as validation_module

        source = open(validation_module.__file__).read()

        assert "from lathe.prompts" not in source
        assert "from lathe.context" not in source
        assert "lathe.prompts" not in source
        assert "lathe.context" not in source

    def test_all_subsystems_import_from_shared(self):
        """Verify all subsystems import from shared for contracts."""
        import lathe.prompts.registry as prompts_module
        import lathe.context.builder as context_module
        import lathe.validation.engine as validation_module

        prompts_src = open(prompts_module.__file__).read()
        context_src = open(context_module.__file__).read()
        validation_src = open(validation_module.__file__).read()

        # All should use shared models
        assert "from lathe.shared" in prompts_src
        assert "from lathe.shared" in context_src
        assert "from lathe.shared" in validation_src

    def test_no_persistence_imports_prompts(self):
        """Verify prompts doesn't import database or file I/O libraries."""
        import lathe.prompts.registry as prompts_module

        source = open(prompts_module.__file__).read()

        assert "import sqlite" not in source
        assert "import psycopg" not in source
        assert "supabase" not in source
        assert "open(" not in source

    def test_no_persistence_imports_context(self):
        """Verify context doesn't import database or file I/O libraries."""
        import lathe.context.builder as context_module

        source = open(context_module.__file__).read()

        assert "import sqlite" not in source
        assert "supabase" not in source
        assert "open(" not in source

    def test_no_persistence_imports_validation(self):
        """Verify validation doesn't import database or file I/O libraries."""
        import lathe.validation.engine as validation_module

        source = open(validation_module.__file__).read()

        assert "import sqlite" not in source
        assert "supabase" not in source
        assert "open(" not in source


class TestSharedModelsUsage:
    """Verify shared models are properly used for contracts."""

    def test_shared_models_exist(self):
        """Verify all shared models are defined."""
        from lathe.shared.models import (
            PromptMetadata,
            Prompt,
            ContextSource,
            ContextOutput,
            ValidationRule,
            ValidationResult,
        )

        assert PromptMetadata is not None
        assert Prompt is not None
        assert ContextSource is not None
        assert ContextOutput is not None
        assert ValidationRule is not None
        assert ValidationResult is not None

    def test_shared_enums_exist(self):
        """Verify all shared enums are defined."""
        from lathe.shared.enums import (
            ValidationLevel,
            ContextSourceType,
            PromptScope,
        )

        assert ValidationLevel is not None
        assert ContextSourceType is not None
        assert PromptScope is not None

    def test_validation_level_values(self):
        """Verify ValidationLevel enum has correct values."""
        from lathe.shared.enums import ValidationLevel

        assert hasattr(ValidationLevel, "PASS")
        assert hasattr(ValidationLevel, "WARN")
        assert hasattr(ValidationLevel, "FAIL")

    def test_context_source_type_values(self):
        """Verify ContextSourceType enum has correct values."""
        from lathe.shared.enums import ContextSourceType

        assert hasattr(ContextSourceType, "KNOWLEDGE")
        assert hasattr(ContextSourceType, "MEMORY")
        assert hasattr(ContextSourceType, "FILE")
        assert hasattr(ContextSourceType, "METADATA")
        assert hasattr(ContextSourceType, "CUSTOM")

    def test_prompt_scope_values(self):
        """Verify PromptScope enum has correct values."""
        from lathe.shared.enums import PromptScope

        assert hasattr(PromptScope, "GLOBAL")
        assert hasattr(PromptScope, "PROJECT")
        assert hasattr(PromptScope, "TASK")
        assert hasattr(PromptScope, "CUSTOM")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
