"""
Knowledge Ingestion Data Models

Pure data structures with no behavior.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Document:
    """A source document that has been ingested."""
    id: str
    path: str
    content: str
    format: str
    size_bytes: int
    ingested_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "ingested_at": self.ingested_at,
        }


@dataclass
class Chunk:
    """A deterministically chunked piece of a document."""
    id: str
    document_id: str
    content: str
    index: int
    start_offset: int
    end_offset: int
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "index": self.index,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "content_preview": self.content[:100] + "..." if len(self.content) > 100 else self.content,
        }


@dataclass
class KnowledgeIndexStatus:
    """Status of the knowledge index."""
    document_count: int
    chunk_count: int
    last_indexed_at: Optional[str]
    is_empty: bool
    supported_formats: List[str] = field(default_factory=lambda: [".md", ".txt", ".py", ".json"])
    
    def to_dict(self) -> dict:
        return {
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "last_indexed_at": self.last_indexed_at,
            "is_empty": self.is_empty,
            "supported_formats": self.supported_formats,
        }
