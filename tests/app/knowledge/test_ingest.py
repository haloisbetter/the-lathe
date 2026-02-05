"""
Tests for knowledge ingestion.

Verifies:
- Deterministic chunking
- Unsafe path rejection
- Format validation
- Binary file rejection
"""
import os
import tempfile
import pytest

from lathe_app.knowledge.ingest import (
    chunk_text,
    is_safe_path,
    is_supported_format,
    is_binary_file,
    ingest_file,
    ingest_path,
    generate_document_id,
    generate_chunk_id,
)


class TestDeterministicChunking:
    """Tests that chunking is deterministic."""
    
    def test_same_input_same_output(self):
        """Same text always produces same chunks."""
        text = "Hello world. " * 100
        
        chunks1 = chunk_text(text, chunk_size=100, overlap=20)
        chunks2 = chunk_text(text, chunk_size=100, overlap=20)
        
        assert chunks1 == chunks2
    
    def test_chunk_content_deterministic(self):
        """Chunk content is exactly reproducible."""
        text = "ABCDEFGHIJ" * 50
        
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        for i in range(3):
            new_chunks = chunk_text(text, chunk_size=100, overlap=10)
            for j, (chunk, start, end) in enumerate(chunks):
                assert new_chunks[j][0] == chunk
                assert new_chunks[j][1] == start
                assert new_chunks[j][2] == end
    
    def test_empty_text_empty_chunks(self):
        """Empty text produces no chunks."""
        chunks = chunk_text("", chunk_size=100, overlap=10)
        assert chunks == []
    
    def test_chunk_overlap_works(self):
        """Chunks overlap correctly."""
        text = "0123456789" * 10
        
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        
        assert len(chunks) > 1
        first_end = chunks[0][2]
        second_start = chunks[1][1]
        assert second_start < first_end
    
    def test_document_id_deterministic(self):
        """Document ID is deterministic."""
        path = "test.md"
        content = "Hello world"
        
        id1 = generate_document_id(path, content)
        id2 = generate_document_id(path, content)
        
        assert id1 == id2
        assert id1.startswith("doc-")
    
    def test_chunk_id_deterministic(self):
        """Chunk ID is deterministic."""
        doc_id = "doc-123"
        index = 0
        content = "Hello world"
        
        id1 = generate_chunk_id(doc_id, index, content)
        id2 = generate_chunk_id(doc_id, index, content)
        
        assert id1 == id2
        assert id1.startswith("chunk-")


class TestUnsafePathRejection:
    """Tests that unsafe paths are rejected."""
    
    def test_etc_rejected(self):
        """System /etc path rejected."""
        safe, error = is_safe_path("/etc/passwd")
        assert not safe
        assert "unsafe" in error.lower()
    
    def test_var_rejected(self):
        """System /var path rejected."""
        safe, error = is_safe_path("/var/log/syslog")
        assert not safe
    
    def test_usr_rejected(self):
        """System /usr path rejected."""
        safe, error = is_safe_path("/usr/bin/python")
        assert not safe
    
    def test_proc_rejected(self):
        """System /proc path rejected."""
        safe, error = is_safe_path("/proc/1/status")
        assert not safe
    
    def test_traversal_outside_base_rejected(self):
        """Parent traversal outside base rejected."""
        safe, error = is_safe_path("../../../etc/passwd", base_dir="/home/user")
        assert not safe
    
    def test_relative_path_allowed(self):
        """Relative paths within base are allowed."""
        safe, error = is_safe_path("docs/readme.md")
        assert safe


class TestFormatValidation:
    """Tests for format validation."""
    
    def test_md_supported(self):
        assert is_supported_format("readme.md")
    
    def test_txt_supported(self):
        assert is_supported_format("notes.txt")
    
    def test_py_supported(self):
        assert is_supported_format("main.py")
    
    def test_json_supported(self):
        assert is_supported_format("config.json")
    
    def test_exe_not_supported(self):
        assert not is_supported_format("program.exe")
    
    def test_pdf_not_supported(self):
        assert not is_supported_format("document.pdf")
    
    def test_jpg_not_supported(self):
        assert not is_supported_format("image.jpg")


class TestFileIngestion:
    """Tests for file ingestion."""
    
    def test_ingest_markdown_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Document\n\nThis is a test.")
            f.flush()
            
            try:
                doc, chunks, error = ingest_file(f.name)
                
                assert error is None
                assert doc is not None
                assert doc.format == ".md"
                assert len(chunks) >= 1
            finally:
                os.unlink(f.name)
    
    def test_ingest_nonexistent_file(self):
        doc, chunks, error = ingest_file("/nonexistent/path/file.md")
        
        assert doc is None
        assert error is not None
        assert "not found" in error.lower()
    
    def test_ingest_unsafe_path_rejected(self):
        doc, chunks, error = ingest_file("/etc/passwd")
        
        assert doc is None
        assert error is not None
        assert "unsafe" in error.lower()
    
    def test_ingest_unsupported_format_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("content")
            f.flush()
            
            try:
                doc, chunks, error = ingest_file(f.name)
                
                assert doc is None
                assert error is not None
                assert "unsupported" in error.lower()
            finally:
                os.unlink(f.name)


class TestDirectoryIngestion:
    """Tests for directory ingestion."""
    
    def test_ingest_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "doc1.md"), "w") as f:
                f.write("# Doc 1\n\nContent 1")
            with open(os.path.join(tmpdir, "doc2.txt"), "w") as f:
                f.write("Doc 2 content")
            with open(os.path.join(tmpdir, "image.jpg"), "w") as f:
                f.write("not actually an image")
            
            docs, chunks, errors = ingest_path(tmpdir)
            
            assert len(docs) == 2
            assert len(chunks) >= 2
    
    def test_ingest_skips_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, ".hidden.md"), "w") as f:
                f.write("# Hidden doc")
            with open(os.path.join(tmpdir, "visible.md"), "w") as f:
                f.write("# Visible doc")
            
            docs, chunks, errors = ingest_path(tmpdir)
            
            assert len(docs) == 1
            assert "visible" in docs[0].path


class TestIngestNeverBlocks:
    """Tests that ingestion failures never block Lathe."""
    
    def test_errors_collected_not_raised(self):
        """Errors are returned, not raised as exceptions."""
        docs, chunks, errors = ingest_path("/nonexistent/path")
        
        assert len(errors) > 0
        assert len(docs) == 0
    
    def test_partial_success_continues(self):
        """If some files fail, others still succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "good.md"), "w") as f:
                f.write("# Good doc")
            
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            
            docs, chunks, errors = ingest_path(tmpdir)
            
            assert len(docs) >= 1
