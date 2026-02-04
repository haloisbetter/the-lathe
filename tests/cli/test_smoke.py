import subprocess
import pytest

def test_cli_help():
    result = subprocess.run(["python", "-m", "lathe", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "The Lathe CLI" in result.stdout

def test_cli_why_example():
    result = subprocess.run(["python", "-m", "lathe", "why", "example"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "goal" in result.stdout
    assert "context" in result.stdout

def test_cli_ledger_show():
    result = subprocess.run(["python", "-m", "lathe", "ledger", "show", "."], capture_output=True, text=True)
    assert result.returncode == 0
    assert "# Purpose" in result.stdout

def test_cli_repo_search():
    result = subprocess.run(["python", "-m", "lathe", "repo", "search", "lathe"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "lathe" in result.stdout.lower()

def test_cli_rag_preview():
    result = subprocess.run(["python", "-m", "lathe", "rag", "preview", "test task"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--- RAG Evidence for: test task ---" in result.stdout
