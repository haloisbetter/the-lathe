import pytest
import json
from lathe.agent import AgentReasoning

def test_guardrail_denies_docs():
    agent = AgentReasoning()
    # Mock evidence with a doc file
    evidence = [{"path": "README.md", "range": "1-10", "content": [], "hash": "abc"}]
    result = agent.propose("add tests", {}, evidence)
    
    assert len(result["proposals"]) == 0
    assert "refusal" in result
    assert "README.md" in result["details"]

def test_guardrail_allows_code():
    agent = AgentReasoning()
    evidence = [{"path": "lathe/main.py", "range": "1-10", "content": [], "hash": "abc"}]
    result = agent.propose("fix bug", {}, evidence)
    
    assert len(result["proposals"]) == 1
    assert result["proposals"][0]["file"] == "lathe/main.py"

def test_rag_channels_separation():
    from lathe.rag import retrieve_rag_evidence
    # This assumes search_repo works and we have some files
    # We verify the logic by checking if we get any doc files in actionable channel
    actionable = retrieve_rag_evidence("test", channel="actionable")
    for item in actionable:
        assert not item["path"].endswith(".md")
        assert not item["path"] == "Makefile"
