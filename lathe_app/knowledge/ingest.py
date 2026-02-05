"""
Knowledge Ingestion

Safely ingests user documentation into chunks for RAG.

Guarantees:
- Rejects binaries and unsafe paths
- Deterministic chunking (same input = same output)
- No execution logic
"""
import hashlib
import os
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

from lathe_app.knowledge.models import Document, Chunk

SUPPORTED_FORMATS = frozenset({".md", ".txt", ".py", ".json"})

UNSAFE_PATH_PREFIXES = frozenset({
    "/etc", "/var", "/usr", "/bin", "/sbin", "/root",
    "/proc", "/sys", "/dev", "/boot", "/lib", "/lib64",
})

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def is_safe_path(path: str, base_dir: str = ".") -> Tuple[bool, str]:
    """
    Check if a path is safe to ingest.
    
    Returns (is_safe, error_message).
    """
    try:
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_dir)
        
        for prefix in UNSAFE_PATH_PREFIXES:
            if abs_path.startswith(prefix):
                return False, f"Unsafe path: {path} (system directory)"
        
        if ".." in path:
            resolved = os.path.realpath(path)
            if not resolved.startswith(abs_base):
                return False, f"Unsafe path: {path} (traversal outside base)"
        
        return True, ""
    except Exception as e:
        return False, f"Path validation error: {str(e)}"


def is_supported_format(path: str) -> bool:
    """Check if file format is supported."""
    ext = Path(path).suffix.lower()
    return ext in SUPPORTED_FORMATS


def is_binary_file(path: str) -> bool:
    """Check if file appears to be binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
        return False
    except Exception:
        return True


def generate_document_id(path: str, content: str) -> str:
    """Generate deterministic document ID from path and content."""
    hasher = hashlib.sha256()
    hasher.update(path.encode("utf-8"))
    hasher.update(content.encode("utf-8"))
    return f"doc-{hasher.hexdigest()[:16]}"


def generate_chunk_id(document_id: str, index: int, content: str) -> str:
    """Generate deterministic chunk ID."""
    hasher = hashlib.sha256()
    hasher.update(document_id.encode("utf-8"))
    hasher.update(str(index).encode("utf-8"))
    hasher.update(content.encode("utf-8"))
    return f"chunk-{hasher.hexdigest()[:16]}"


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Tuple[str, int, int]]:
    """
    Chunk text deterministically.
    
    Returns list of (chunk_content, start_offset, end_offset).
    
    Chunking is deterministic: same input always produces same output.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_content = text[start:end]
        chunks.append((chunk_content, start, end))
        
        if end >= text_len:
            break
        
        start = end - overlap
        if start < 0:
            start = 0
        if start >= text_len:
            break
    
    return chunks


def ingest_file(
    path: str,
    base_dir: str = ".",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> Tuple[Optional[Document], List[Chunk], Optional[str]]:
    """
    Ingest a single file.
    
    Returns (Document, list of Chunks, error_message).
    If error, Document is None and error_message explains why.
    """
    safe, error = is_safe_path(path, base_dir)
    if not safe:
        return None, [], error
    
    if not os.path.exists(path):
        return None, [], f"File not found: {path}"
    
    if not os.path.isfile(path):
        return None, [], f"Not a file: {path}"
    
    if not is_supported_format(path):
        ext = Path(path).suffix
        return None, [], f"Unsupported format: {ext} (supported: {', '.join(SUPPORTED_FORMATS)})"
    
    if is_binary_file(path):
        return None, [], f"Binary file rejected: {path}"
    
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return None, [], f"Read error: {str(e)}"
    
    ext = Path(path).suffix.lower()
    doc_id = generate_document_id(path, content)
    
    document = Document(
        id=doc_id,
        path=path,
        content=content,
        format=ext,
        size_bytes=len(content.encode("utf-8")),
        ingested_at=datetime.utcnow().isoformat(),
    )
    
    chunk_tuples = chunk_text(content, chunk_size, overlap)
    chunks = []
    
    for i, (chunk_content, start, end) in enumerate(chunk_tuples):
        chunk_id = generate_chunk_id(doc_id, i, chunk_content)
        chunks.append(Chunk(
            id=chunk_id,
            document_id=doc_id,
            content=chunk_content,
            index=i,
            start_offset=start,
            end_offset=end,
        ))
    
    return document, chunks, None


def ingest_path(
    path: str,
    base_dir: str = ".",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    recursive: bool = True,
) -> Tuple[List[Document], List[Chunk], List[str]]:
    """
    Ingest a file or directory.
    
    Returns (list of Documents, list of Chunks, list of errors).
    
    Errors are collected but do not stop processing.
    """
    documents = []
    all_chunks = []
    errors = []
    
    safe, error = is_safe_path(path, base_dir)
    if not safe:
        errors.append(error)
        return documents, all_chunks, errors
    
    if not os.path.exists(path):
        errors.append(f"Path not found: {path}")
        return documents, all_chunks, errors
    
    if os.path.isfile(path):
        doc, chunks, err = ingest_file(path, base_dir, chunk_size, overlap)
        if err:
            errors.append(err)
        if doc:
            documents.append(doc)
            all_chunks.extend(chunks)
        return documents, all_chunks, errors
    
    if os.path.isdir(path):
        if recursive:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                for filename in files:
                    if filename.startswith("."):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    
                    if not is_supported_format(file_path):
                        continue
                    
                    doc, chunks, err = ingest_file(file_path, base_dir, chunk_size, overlap)
                    if err:
                        errors.append(err)
                    if doc:
                        documents.append(doc)
                        all_chunks.extend(chunks)
        else:
            for filename in os.listdir(path):
                if filename.startswith("."):
                    continue
                
                file_path = os.path.join(path, filename)
                
                if not os.path.isfile(file_path):
                    continue
                
                if not is_supported_format(file_path):
                    continue
                
                doc, chunks, err = ingest_file(file_path, base_dir, chunk_size, overlap)
                if err:
                    errors.append(err)
                if doc:
                    documents.append(doc)
                    all_chunks.extend(chunks)
    
    return documents, all_chunks, errors
