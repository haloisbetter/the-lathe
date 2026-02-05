"""
Tests for knowledge index.

Verifies:
- Deterministic queries
- Rebuild vs incremental
- Empty index returns empty results
"""
import pytest

from lathe_app.knowledge.index import (
    KnowledgeIndex,
    hash_embedding,
    cosine_similarity,
    get_default_index,
    reset_default_index,
)
from lathe_app.knowledge.models import Document, Chunk


def make_test_document(id: str = "doc-1", content: str = "Test content") -> Document:
    return Document(
        id=id,
        path=f"/test/{id}.md",
        content=content,
        format=".md",
        size_bytes=len(content),
    )


def make_test_chunk(doc_id: str, index: int, content: str) -> Chunk:
    return Chunk(
        id=f"chunk-{doc_id}-{index}",
        document_id=doc_id,
        content=content,
        index=index,
        start_offset=0,
        end_offset=len(content),
    )


class TestDeterministicEmbedding:
    """Tests for hash-based embedding."""
    
    def test_same_text_same_embedding(self):
        """Same text always produces same embedding."""
        text = "Hello world"
        
        emb1 = hash_embedding(text)
        emb2 = hash_embedding(text)
        
        assert emb1 == emb2
    
    def test_different_text_different_embedding(self):
        """Different text produces different embeddings."""
        emb1 = hash_embedding("Hello")
        emb2 = hash_embedding("World")
        
        assert emb1 != emb2
    
    def test_embedding_has_correct_dimensions(self):
        """Embedding has expected dimensions."""
        emb = hash_embedding("Test", dimensions=64)
        assert len(emb) == 64
        
        emb = hash_embedding("Test", dimensions=128)
        assert len(emb) == 128


class TestCosineSimilarity:
    """Tests for cosine similarity."""
    
    def test_identical_vectors_similarity_one(self):
        """Identical vectors have similarity 1.0."""
        vec = [0.1, 0.2, 0.3]
        sim = cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001
    
    def test_different_length_returns_zero(self):
        """Vectors of different length return 0."""
        sim = cosine_similarity([1, 2], [1, 2, 3])
        assert sim == 0.0
    
    def test_zero_vector_returns_zero(self):
        """Zero vector returns 0."""
        sim = cosine_similarity([0, 0, 0], [1, 2, 3])
        assert sim == 0.0


class TestKnowledgeIndex:
    """Tests for KnowledgeIndex."""
    
    def test_empty_index_returns_empty_results(self):
        """Empty index returns empty list, not error."""
        index = KnowledgeIndex()
        
        results = index.query("test query")
        
        assert results == []
        assert index.is_empty
    
    def test_add_and_query(self):
        """Can add chunks and query them."""
        index = KnowledgeIndex()
        doc = make_test_document("doc-1", "Full document content")
        chunk = make_test_chunk("doc-1", 0, "Python programming tutorial")
        
        index.add_document(doc)
        index.add_chunk(chunk)
        
        results = index.query("Python programming", k=1)
        
        assert len(results) == 1
        assert results[0][0].id == chunk.id
    
    def test_query_returns_same_results(self):
        """Same query always returns same results (determinism)."""
        index = KnowledgeIndex()
        doc = make_test_document()
        chunks = [
            make_test_chunk("doc-1", 0, "Python basics"),
            make_test_chunk("doc-1", 1, "JavaScript fundamentals"),
            make_test_chunk("doc-1", 2, "Rust programming"),
        ]
        
        index.add_document(doc)
        for chunk in chunks:
            index.add_chunk(chunk)
        
        query = "Python programming"
        results1 = index.query(query, k=2)
        results2 = index.query(query, k=2)
        
        assert len(results1) == len(results2)
        for i in range(len(results1)):
            assert results1[i][0].id == results2[i][0].id
            assert results1[i][1] == results2[i][1]
    
    def test_build_index_replaces(self):
        """build_index replaces existing data."""
        index = KnowledgeIndex()
        
        doc1 = make_test_document("doc-1")
        chunk1 = make_test_chunk("doc-1", 0, "First content")
        index.build_index([doc1], [chunk1])
        
        assert index.document_count == 1
        assert index.chunk_count == 1
        
        doc2 = make_test_document("doc-2", "New content")
        chunk2 = make_test_chunk("doc-2", 0, "Second content")
        index.build_index([doc2], [chunk2])
        
        assert index.document_count == 1
        assert index.chunk_count == 1
        assert index.get_document("doc-2") is not None
        assert index.get_document("doc-1") is None
    
    def test_clear_removes_all(self):
        """clear() removes all data."""
        index = KnowledgeIndex()
        doc = make_test_document()
        chunk = make_test_chunk("doc-1", 0, "Content")
        
        index.build_index([doc], [chunk])
        assert not index.is_empty
        
        index.clear()
        
        assert index.is_empty
        assert index.document_count == 0
        assert index.chunk_count == 0
    
    def test_last_indexed_at_updated(self):
        """last_indexed_at is updated on build."""
        index = KnowledgeIndex()
        
        assert index.last_indexed_at is None
        
        index.build_index([], [])
        
        assert index.last_indexed_at is not None


class TestDefaultIndex:
    """Tests for default index singleton."""
    
    def test_get_default_index_returns_same_instance(self):
        reset_default_index()
        
        index1 = get_default_index()
        index2 = get_default_index()
        
        assert index1 is index2
    
    def test_reset_creates_new_instance(self):
        reset_default_index()
        index1 = get_default_index()
        
        reset_default_index()
        index2 = get_default_index()
        
        assert index1 is not index2
