import json
import subprocess
import os
from pathlib import Path

def test_deterministic_think():
    # Use the sample repo fixture as the root
    fixture_path = Path("tests/fixtures/sample_repo").resolve()
    why_path = fixture_path / "why.json"
    why_path.write_text(json.dumps({
        "goal": "Test deterministic reasoning",
        "context": "Lathe fixture environment",
        "evidence": "No evidence needed for smoke test",
        "decision": "Run a think command",
        "risk_level": "Low",
        "options_considered": ["Test option"],
        "guardrails": ["Test guardrail"],
        "verification_steps": ["Test verification"]
    }))
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    result = subprocess.run(
        ["python", "-m", "lathe", "think", "hello world", "--why", str(why_path)],
        capture_output=True,
        text=True,
        cwd=str(fixture_path),
        env=env
    )
    
    if result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
    
    assert result.returncode == 0
    assert "--- Reasoning for: hello world ---" in result.stdout
    assert "Proposed Plan:" in result.stdout
    assert "Assumptions:" in result.stdout
    assert "Evidence References:" in result.stdout

def test_deterministic_propose():
    fixture_path = Path("tests/fixtures/sample_repo").resolve()
    why_path = fixture_path / "why.json"
    why_path.write_text(json.dumps({
        "goal": "Test deterministic reasoning",
        "context": "Lathe fixture environment",
        "evidence": "No evidence needed for smoke test",
        "decision": "Run a propose command",
        "risk_level": "Low",
        "options_considered": ["Test option"],
        "guardrails": ["Test guardrail"],
        "verification_steps": ["Test verification"]
    }))
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    result = subprocess.run(
        ["python", "-m", "lathe", "propose", "hello world", "--why", str(why_path)],
        capture_output=True,
        text=True,
        cwd=str(fixture_path),
        env=env
    )
    
    assert result.returncode == 0
    assert "--- Proposal for: hello world ---" in result.stdout
    assert ("Proposal 1 (File:" in result.stdout or "Proposal failed due to security constraints" in result.stdout)
