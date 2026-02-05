"""
In-Memory Vector Index

Hash-based embedding stub for deterministic similarity search.
No external dependencies.

Guarantees:
- Deterministic: same query always returns same results
- Rebuildable and discardable
- Missing index returns empty results, not error
"""
import hashlib
from typing import List, Optional, Tuple
from datetime import datetime

from lathe_app.knowledge.models import Chunk, Document


def hash_embedding(text: str, dimensions: int = 64) -> List[float]:
    """
    Generate deterministic hash-based embedding.
    
    This is a stub implementation using SHA-256 hash.
    Same text always produces same embedding.
    """
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    hash_bytes = hasher.digest()
    
    embedding = []
    for i in range(dimensions):
        byte_val = hash_bytes[i % len(hash_bytes)]
        embedding.append((byte_val - 128) / 128.0)
    
    return embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


class KnowledgeIndex:
    """
    In-memory vector index for knowledge chunks.
    
    Thread-safe for reads (single-threaded writes).
    Deterministic: same queries return same results.
    """
    
    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, Chunk] = {}
        self._embeddings: dict[str, List[float]] = {}
        self._last_indexed_at: Optional[str] = None
    
    def clear(self) -> None:
        """Clear all indexed data."""
        self._documents.clear()
        self._chunks.clear()
        self._embeddings.clear()
        self._last_indexed_at = None
    
    def add_document(self, document: Document) -> None:
        """Add a document to the index."""
        self._documents[document.id] = document
    
    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk and compute its embedding."""
        self._chunks[chunk.id] = chunk
        embedding = hash_embedding(chunk.content)
        self._embeddings[chunk.id] = embedding
        chunk.embedding = embedding
    
    def build_index(self, documents: List[Document], chunks: List[Chunk]) -> None:
        """
        Build the index from documents and chunks.
        
        This replaces any existing index data.
        """
        self.clear()
        
        for doc in documents:
            self.add_document(doc)
        
        for chunk in chunks:
            self.add_chunk(chunk)
        
        self._last_indexed_at = datetime.utcnow().isoformat()
    
    def query(self, query_text: str, k: int = 5) -> List[Tuple[Chunk, float]]:
        """
        Query the index for similar chunks.
        
        Returns list of (Chunk, similarity_score) sorted by score descending.
        
        If index is empty, returns empty list (not an error).
        Deterministic: same query always returns same results.
        """
        if not self._chunks:
            return []
        
        query_embedding = hash_embedding(query_text)
        
        scored_chunks = []
        for chunk_id, chunk in self._chunks.items():
            embedding = self._embeddings.get(chunk_id)
            if embedding is None:
                continue
            
            similarity = cosine_similarity(query_embedding, embedding)
            scored_chunks.append((chunk, similarity))
        
        scored_chunks.sort(key=lambda x: (-x[1], x[0].id))
        
        return scored_chunks[:k]
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self._documents.get(doc_id)
    
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by ID."""
        return self._chunks.get(chunk_id)
    
    @property
    def document_count(self) -> int:
        """Number of documents in the index."""
        return len(self._documents)
    
    @property
    def chunk_count(self) -> int:
        """Number of chunks in the index."""
        return len(self._chunks)
    
    @property
    def last_indexed_at(self) -> Optional[str]:
        """Timestamp of last indexing operation."""
        return self._last_indexed_at
    
    @property
    def is_empty(self) -> bool:
        """Check if index is empty."""
        return len(self._chunks) == 0


_default_index: Optional[KnowledgeIndex] = None


def get_default_index() -> KnowledgeIndex:
    """Get or create the default knowledge index."""
    global _default_index
    if _default_index is None:
        _default_index = KnowledgeIndex()
    return _default_index


def reset_default_index() -> None:
    """Reset the default index (for testing)."""
    global _default_index
    _default_index = None
