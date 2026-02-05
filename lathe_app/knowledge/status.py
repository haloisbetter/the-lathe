"""
Knowledge Index Status

Track ingestion status without persistence.
"""
from lathe_app.knowledge.models import KnowledgeIndexStatus
from lathe_app.knowledge.index import get_default_index
from lathe_app.knowledge.ingest import SUPPORTED_FORMATS


def get_status() -> KnowledgeIndexStatus:
    """
    Get current status of the knowledge index.
    
    Returns KnowledgeIndexStatus with current metrics.
    """
    index = get_default_index()
    
    return KnowledgeIndexStatus(
        document_count=index.document_count,
        chunk_count=index.chunk_count,
        last_indexed_at=index.last_indexed_at,
        is_empty=index.is_empty,
        supported_formats=list(SUPPORTED_FORMATS),
    )
