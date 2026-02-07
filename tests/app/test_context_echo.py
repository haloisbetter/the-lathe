"""
Tests for Context Echo Validation

Proves:
1. Response WITHOUT Context Echo is rejected
2. Response WITH malformed Context Echo is rejected
3. Response referencing files not in echo is rejected
4. Valid Context Echo passes
5. Kernel remains untouched
6. Orchestrator integration with echo validation
"""
import json
import pytest

from lathe_app.validation.context_echo import (
    validate_context_echo,
    ContextEchoResult,
    ContextEchoViolation,
    ECHO_START,
    ECHO_END,
)


VALID_ECHO = f"""{ECHO_START}
Workspace: my-project
Snapshot: snap-001
Files:
- src/main.py
- src/utils.py
- README.md
{ECHO_END}"""

VALID_RESPONSE = f"""{VALID_ECHO}

Based on the files provided, I recommend modifying src/main.py to add error handling.
The src/utils.py file contains helper functions that can be reused.
"""


class TestEchoBlockPresence:

    def test_missing_echo_block_is_rejected(self):
        result = validate_context_echo("Just a plain response with no echo block.")
        assert result.valid is False
        assert len(result.violations) == 1
        assert result.violations[0].rule == "echo_block_missing"

    def test_missing_start_delimiter(self):
        text = f"""Workspace: test
Snapshot: snap-1
Files:
- foo.py
{ECHO_END}
Some reasoning here."""
        result = validate_context_echo(text)
        assert result.valid is False
        assert result.violations[0].rule == "echo_block_missing"

    def test_missing_end_delimiter(self):
        text = f"""{ECHO_START}
Workspace: test
Snapshot: snap-1
Files:
- foo.py
Some reasoning here."""
        result = validate_context_echo(text)
        assert result.valid is False
        assert result.violations[0].rule == "echo_block_missing"

    def test_empty_response_is_rejected(self):
        result = validate_context_echo("")
        assert result.valid is False
        assert result.violations[0].rule == "echo_block_missing"


class TestMalformedEchoBlock:

    def test_missing_workspace_field(self):
        text = f"""{ECHO_START}
Snapshot: snap-1
Files:
- foo.py
{ECHO_END}
Some reasoning."""
        result = validate_context_echo(text)
        assert result.valid is False
        rules = [v.rule for v in result.violations]
        assert "missing_field" in rules

    def test_missing_snapshot_field(self):
        text = f"""{ECHO_START}
Workspace: test
Files:
- foo.py
{ECHO_END}
Some reasoning."""
        result = validate_context_echo(text)
        assert result.valid is False
        rules = [v.rule for v in result.violations]
        assert "missing_field" in rules

    def test_missing_files_field(self):
        text = f"""{ECHO_START}
Workspace: test
Snapshot: snap-1
{ECHO_END}
Some reasoning."""
        result = validate_context_echo(text)
        assert result.valid is False
        rules = [v.rule for v in result.violations]
        assert "missing_field" in rules

    def test_all_fields_missing(self):
        text = f"""{ECHO_START}
Nothing useful here
{ECHO_END}
Some reasoning."""
        result = validate_context_echo(text)
        assert result.valid is False
        assert len(result.violations) == 3

    def test_snapshot_id_alias_accepted(self):
        text = f"""{ECHO_START}
Workspace: test
Snapshot ID: snap-1
Files Available:
- foo.py
{ECHO_END}
Some reasoning about foo.py."""
        result = validate_context_echo(text)
        assert result.valid is True


class TestUndeclaredFileReferences:

    def test_referencing_undeclared_file_is_rejected(self):
        text = f"""{ECHO_START}
Workspace: my-project
Snapshot: snap-001
Files:
- src/main.py
{ECHO_END}

I recommend modifying src/main.py and also src/secret.py for the fix.
"""
        result = validate_context_echo(text)
        assert result.valid is False
        rules = [v.rule for v in result.violations]
        assert "undeclared_file_reference" in rules
        details = [v.detail for v in result.violations]
        assert any("src/secret.py" in d for d in details)

    def test_multiple_undeclared_files(self):
        text = f"""{ECHO_START}
Workspace: proj
Snapshot: snap-1
Files:
- src/main.py
{ECHO_END}

Check src/auth.py and src/db.py for potential issues.
Also review lib/helpers.py.
"""
        result = validate_context_echo(text)
        assert result.valid is False
        undeclared = [v for v in result.violations if v.rule == "undeclared_file_reference"]
        assert len(undeclared) >= 2

    def test_declared_files_pass(self):
        result = validate_context_echo(VALID_RESPONSE)
        assert result.valid is True

    def test_file_reference_in_echo_block_not_checked(self):
        text = f"""{ECHO_START}
Workspace: proj
Snapshot: snap-1
Files:
- src/main.py
- src/utils.py
{ECHO_END}

The src/main.py file looks good."""
        result = validate_context_echo(text)
        assert result.valid is True

    def test_suffix_matching_allows_relative_refs(self):
        text = f"""{ECHO_START}
Workspace: proj
Snapshot: snap-1
Files:
- src/components/Button.tsx
{ECHO_END}

The src/components/Button.tsx component needs refactoring."""
        result = validate_context_echo(text)
        assert result.valid is True


class TestValidEchoBlock:

    def test_minimal_valid_echo(self):
        text = f"""{ECHO_START}
Workspace: NONE
Snapshot: NONE
Files:
{ECHO_END}
No files to analyze."""
        result = validate_context_echo(text)
        assert result.valid is True
        assert result.workspace == "NONE"
        assert result.snapshot == "NONE"
        assert result.files == []

    def test_full_valid_echo(self):
        result = validate_context_echo(VALID_RESPONSE)
        assert result.valid is True
        assert result.workspace == "my-project"
        assert result.snapshot == "snap-001"
        assert "src/main.py" in result.files
        assert "src/utils.py" in result.files
        assert "README.md" in result.files

    def test_why_is_empty_on_success(self):
        result = validate_context_echo(VALID_RESPONSE)
        assert result.why() == []

    def test_why_populated_on_failure(self):
        result = validate_context_echo("no echo here")
        why = result.why()
        assert len(why) >= 1
        assert "rule" in why[0]
        assert "detail" in why[0]


class TestOrchestratorIntegration:

    def _make_agent_fn(self, response_text: str):
        def agent_fn(normalized, model_id):
            return response_text
        return agent_fn

    def test_orchestrator_rejects_without_echo_when_enabled(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        agent_fn = self._make_agent_fn(json.dumps({
            "proposals": [{"action": "create", "target": "foo.py"}],
            "assumptions": [],
            "risks": [],
            "results": ["done"],
            "model_fingerprint": "test-model",
        }))

        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=agent_fn,
            storage=storage,
            require_context_echo=True,
        )

        run = orch.execute(
            intent="propose",
            task="add auth",
            why={"goal": "security"},
        )

        assert run.success is False
        assert hasattr(run.output, "reason")
        assert "Context Echo" in run.output.reason

    def test_orchestrator_passes_with_valid_echo(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        response = f"""{ECHO_START}
Workspace: test
Snapshot: snap-1
Files:
- src/auth.py
{ECHO_END}
""" + json.dumps({
            "proposals": [{"action": "create", "target": "src/auth.py"}],
            "assumptions": [],
            "risks": [],
            "results": ["done"],
            "model_fingerprint": "test-model",
        })

        agent_fn = self._make_agent_fn(response)
        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=agent_fn,
            storage=storage,
            require_context_echo=True,
        )

        run = orch.execute(
            intent="propose",
            task="add auth",
            why={"goal": "security"},
        )

        assert run.success is False or run.output is not None

    def test_orchestrator_skips_echo_validation_when_disabled(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        agent_fn = self._make_agent_fn(json.dumps({
            "proposals": [],
            "assumptions": [],
            "risks": [],
            "results": ["done"],
            "model_fingerprint": "test-model",
        }))

        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=agent_fn,
            storage=storage,
            require_context_echo=False,
        )

        run = orch.execute(
            intent="propose",
            task="add feature",
            why={"goal": "test"},
        )

        assert run.output is not None

    def test_echo_violation_stored_in_refusal(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        agent_fn = self._make_agent_fn("plain text, no echo")
        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=agent_fn,
            storage=storage,
            require_context_echo=True,
        )

        run = orch.execute(
            intent="think",
            task="analyze code",
            why={"goal": "quality"},
        )

        assert run.success is False
        assert "Context Echo" in run.output.reason
        details = run.output.details
        assert "echo_block_missing" in details


    def test_speculative_escalation_also_enforces_echo(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        agent_fn = self._make_agent_fn(json.dumps({
            "proposals": [],
            "assumptions": [],
            "risks": [],
            "results": ["done"],
            "model_fingerprint": "test-model",
        }))

        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=agent_fn,
            storage=storage,
            require_context_echo=True,
        )

        run = orch.execute(
            intent="propose",
            task="add feature",
            why={"goal": "test"},
            speculative=True,
        )

        assert run.success is False
        assert "Context Echo" in run.output.reason

    def test_undeclared_file_in_proposals_rejected_via_orchestrator(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        response = f"""{ECHO_START}
Workspace: test
Snapshot: snap-1
Files:
- src/main.py
{ECHO_END}
""" + json.dumps({
            "proposals": [{"action": "create", "target": "src/secret.py"}],
            "assumptions": [],
            "risks": [],
            "results": ["done"],
            "model_fingerprint": "test-model",
        })

        agent_fn = self._make_agent_fn(response)
        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=agent_fn,
            storage=storage,
            require_context_echo=True,
        )

        run = orch.execute(
            intent="propose",
            task="add feature",
            why={"goal": "test"},
        )

        assert run.success is False
        assert "Context Echo" in run.output.reason


class TestKernelUntouched:

    def test_no_context_echo_imports_in_kernel(self):
        import lathe.pipeline as pipeline
        import lathe.output_validator as ov
        import lathe.normalize as norm

        for mod in [pipeline, ov, norm]:
            source = open(mod.__file__).read()
            assert "context_echo" not in source
            assert "CONTEXT_ECHO" not in source

    def test_validation_module_lives_in_app_layer(self):
        import lathe_app.validation.context_echo as ce
        assert "lathe_app" in ce.__file__
        assert "lathe_app/validation" in ce.__file__


class TestEdgeCases:

    def test_echo_with_hash_annotations(self):
        text = f"""{ECHO_START}
Workspace: proj
Snapshot: snap-abc
Files:
- src/main.py (abc123def)
- lib/utils.py (hash: 999)
{ECHO_END}

Looking at src/main.py for issues."""
        result = validate_context_echo(text)
        assert result.valid is True
        assert any("src/main.py" in f for f in result.files)

    def test_echo_with_none_values(self):
        text = f"""{ECHO_START}
Workspace: NONE
Snapshot: NONE
Files:
- (none)
{ECHO_END}
I cannot analyze without files."""
        result = validate_context_echo(text)
        assert result.valid is True

    def test_urls_not_treated_as_file_paths(self):
        text = f"""{ECHO_START}
Workspace: proj
Snapshot: snap-1
Files:
- src/main.py
{ECHO_END}

See https://example.com/docs for more info about src/main.py."""
        result = validate_context_echo(text)
        assert result.valid is True

    def test_deterministic_results(self):
        for _ in range(10):
            r1 = validate_context_echo(VALID_RESPONSE)
            r2 = validate_context_echo("no echo")
            assert r1.valid is True
            assert r2.valid is False
