"""
Tests for RAG integration with knowledge index.

Verifies:
- RAG returns chunks from knowledge index
- Missing index returns empty results
- Kernel is untouched
"""
import pytest

from lathe_app.knowledge.index import (
    KnowledgeIndex,
    get_default_index,
    reset_default_index,
)
from lathe_app.knowledge.models import Document, Chunk
from lathe_app.orchestrator import query_knowledge_index


def make_test_chunk(doc_id: str, index: int, content: str) -> Chunk:
    return Chunk(
        id=f"chunk-{doc_id}-{index}",
        document_id=doc_id,
        content=content,
        index=index,
        start_offset=0,
        end_offset=len(content),
    )


class TestRAGWithKnowledge:
    """Tests for RAG integration."""
    
    def setup_method(self):
        reset_default_index()
    
    def teardown_method(self):
        reset_default_index()
    
    def test_empty_index_returns_empty(self):
        """Empty knowledge index returns empty results."""
        results = query_knowledge_index("test query")
        
        assert results == []
    
    def test_query_returns_chunks(self):
        """Query returns relevant chunks from index."""
        index = get_default_index()
        
        doc = Document(
            id="doc-1",
            path="test.md",
            content="Full content",
            format=".md",
            size_bytes=100,
        )
        chunks = [
            make_test_chunk("doc-1", 0, "Python is a programming language"),
            make_test_chunk("doc-1", 1, "JavaScript is also a language"),
        ]
        
        index.add_document(doc)
        for chunk in chunks:
            index.add_chunk(chunk)
        
        results = query_knowledge_index("Python programming", k=2)
        
        assert len(results) > 0
        assert "chunk_id" in results[0]
        assert "content" in results[0]
        assert "similarity" in results[0]
    
    def test_same_query_same_results(self):
        """Same query returns same results (determinism)."""
        index = get_default_index()
        
        doc = Document(
            id="doc-1",
            path="test.md",
            content="Content",
            format=".md",
            size_bytes=100,
        )
        chunk = make_test_chunk("doc-1", 0, "Machine learning basics")
        
        index.add_document(doc)
        index.add_chunk(chunk)
        
        results1 = query_knowledge_index("machine learning", k=5)
        results2 = query_knowledge_index("machine learning", k=5)
        
        assert results1 == results2


class TestKernelUntouched:
    """Tests that kernel (lathe/) is not modified."""
    
    def test_lathe_pipeline_has_no_knowledge_imports(self):
        """lathe/pipeline.py does not import knowledge modules."""
        import lathe.pipeline
        import inspect
        
        source = inspect.getsource(lathe.pipeline)
        
        assert "lathe_app.knowledge" not in source
        assert "knowledge" not in source.lower() or "knowledge" in source.lower().split("#")[0] is False
    
    def test_lathe_normalize_has_no_knowledge_imports(self):
        """lathe/normalize.py does not import knowledge modules."""
        import lathe.normalize
        import inspect
        
        source = inspect.getsource(lathe.normalize)
        
        assert "lathe_app.knowledge" not in source
    
    def test_lathe_model_tiers_has_no_knowledge_imports(self):
        """lathe/model_tiers.py does not import knowledge modules."""
        import lathe.model_tiers
        import inspect
        
        source = inspect.getsource(lathe.model_tiers)
        
        assert "lathe_app.knowledge" not in source
