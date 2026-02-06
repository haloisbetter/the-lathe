"""
Workspace Indexer

Per-workspace RAG index management.
Each workspace gets its own isolated KnowledgeIndex.

Guarantees:
- Workspace-scoped indexes (no cross-contamination)
- Read-only ingestion (no writes to workspace filesystem)
- Uses existing knowledge infrastructure (KnowledgeIndex, ingest_file)
- Default workspace is NONE — Lathe uses its own docs if no workspace selected
"""
import os
import threading
from typing import Dict, List, Optional, Tuple

from lathe_app.knowledge.index import KnowledgeIndex
from lathe_app.knowledge.ingest import ingest_file
from lathe_app.knowledge.models import Document, Chunk


class WorkspaceIndexer:
    def __init__(self):
        self._indexes: Dict[str, KnowledgeIndex] = {}
        self._lock = threading.Lock()

    def ingest_files(
        self,
        workspace_name: str,
        file_paths: List[str],
        root_path: str,
    ) -> Tuple[int, int, List[str]]:
        """
        Ingest files into a workspace-scoped index.

        Args:
            workspace_name: Name of the workspace
            file_paths: Absolute paths to files to ingest
            root_path: Workspace root (used as base_dir for safety checks)

        Returns:
            (document_count, chunk_count, errors)
        """
        documents: List[Document] = []
        all_chunks: List[Chunk] = []
        errors: List[str] = []

        for path in file_paths:
            doc, chunks, err = ingest_file(path, base_dir=root_path)
            if err:
                errors.append(err)
            if doc:
                documents.append(doc)
                all_chunks.extend(chunks)

        with self._lock:
            index = KnowledgeIndex()
            index.build_index(documents, all_chunks)
            self._indexes[workspace_name] = index

        return len(documents), len(all_chunks), errors

    def query(
        self,
        workspace_name: str,
        query_text: str,
        k: int = 5,
    ) -> List[Dict]:
        """
        Query a workspace-scoped index.

        Returns empty list if workspace has no index.
        """
        with self._lock:
            index = self._indexes.get(workspace_name)

        if index is None:
            return []

        results = index.query(query_text, k=k)
        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "similarity": round(score, 4),
                "workspace": workspace_name,
            }
            for chunk, score in results
        ]

    def get_index(self, workspace_name: str) -> Optional[KnowledgeIndex]:
        with self._lock:
            return self._indexes.get(workspace_name)

    def has_index(self, workspace_name: str) -> bool:
        with self._lock:
            return workspace_name in self._indexes

    def remove_index(self, workspace_name: str) -> bool:
        with self._lock:
            if workspace_name in self._indexes:
                del self._indexes[workspace_name]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._indexes.clear()


_default_indexer: Optional[WorkspaceIndexer] = None
_indexer_lock = threading.Lock()


def get_default_indexer() -> WorkspaceIndexer:
    global _default_indexer
    with _indexer_lock:
        if _default_indexer is None:
            _default_indexer = WorkspaceIndexer()
        return _default_indexer


def reset_default_indexer() -> None:
    global _default_indexer
    with _indexer_lock:
        if _default_indexer is not None:
            _default_indexer.clear()
        _default_indexer = None
