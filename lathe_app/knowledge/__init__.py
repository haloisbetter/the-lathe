"""
Knowledge Ingestion System for Lathe App Layer

Provides safe, deterministic ingestion of user documentation for RAG.

Architectural Law:
- Lathe reasons (kernel)
- The app learns (knowledge ingestion)
- RAG consumes read-only knowledge
- No execution paths depend on ingestion success
"""
from lathe_app.knowledge.models import Document, Chunk, KnowledgeIndexStatus
from lathe_app.knowledge.ingest import ingest_path, ingest_file, chunk_text
from lathe_app.knowledge.index import KnowledgeIndex, get_default_index
from lathe_app.knowledge.status import get_status

__all__ = [
    "Document",
    "Chunk",
    "KnowledgeIndexStatus",
    "ingest_path",
    "ingest_file",
    "chunk_text",
    "KnowledgeIndex",
    "get_default_index",
    "get_status",
]
