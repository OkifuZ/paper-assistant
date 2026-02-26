"""PDF document cache and path utilities."""

from pathlib import Path

import fitz  # PyMuPDF

_doc_cache: dict[str, fitz.Document] = {}


def resolve_path(file_path: str) -> str:
    """Resolve and validate a PDF file path."""
    p = Path(file_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {p}")
    return str(p)


def open_doc(file_path: str) -> fitz.Document:
    """Open a PDF, returning a cached document if available."""
    key = resolve_path(file_path)
    if key in _doc_cache:
        return _doc_cache[key]
    doc = fitz.open(key)
    _doc_cache[key] = doc
    return doc


def check_has_text(doc: fitz.Document, sample_pages: int = 5) -> bool:
    """Check if the PDF contains extractable text."""
    total_chars = 0
    for i in range(min(sample_pages, len(doc))):
        total_chars += len(doc[i].get_text().strip())
    return total_chars >= 50
