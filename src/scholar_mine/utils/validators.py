"""Data validation helpers for PDF files and extraction schemas."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def validate_pdf(pdf_path: Path, min_pages: int = 2, max_size_mb: float = 100) -> tuple[bool, Optional[str]]:
    """Validate a PDF file: existence, size, page count.

    Returns (is_valid, error_reason).
    """
    if not pdf_path.exists():
        return False, "file not found"

    if not pdf_path.suffix.lower() == ".pdf":
        return False, f"not a PDF: {pdf_path.suffix}"

    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"too large: {size_mb:.1f}MB > {max_size_mb}MB"

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages = len(doc)
        doc.close()
        if pages < min_pages:
            return False, f"too few pages: {pages} < {min_pages}"
    except Exception as e:
        return False, f"cannot open PDF: {e}"

    return True, None


def validate_schema(schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate an extraction schema dict.

    Required keys: schema_id, domain, fields (list of {name, key, type}).
    """
    if not isinstance(schema, dict):
        return False, "schema must be a dict"

    required_top = ["schema_id", "domain", "fields"]
    for k in required_top:
        if k not in schema:
            return False, f"missing top-level key: {k}"

    fields = schema.get("fields", [])
    if not isinstance(fields, list) or len(fields) == 0:
        return False, "fields must be a non-empty list"

    for i, f in enumerate(fields):
        if not isinstance(f, dict):
            return False, f"field[{i}] is not a dict"
        for fk in ["name", "key", "type"]:
            if fk not in f:
                return False, f"field[{i}] missing key: {fk}"

    return True, None


AUTO_REJECT_PATTERNS = [
    re.compile(r, re.IGNORECASE) for r in [
        r"corrigendum",
        r"erratum",
        r"retraction",
        r"table of contents",
        r"front matter",
        r"cover image",
        r"graphical abstract only",
        r"editorial board",
        r"call for papers",
    ]
]


def quick_title_reject(title: str) -> tuple[bool, Optional[str]]:
    """Fast regex-based title rejection before LLM check.

    Returns (should_reject, reason).
    """
    if not title or len(title.strip()) < 10:
        return True, "title too short or empty"

    for pattern in AUTO_REJECT_PATTERNS:
        if pattern.search(title):
            return True, f"matched reject pattern: {pattern.pattern}"

    return False, None


def fuzzy_dedup_key(title: str) -> str:
    """Generate a fuzzy dedup key from a title (lowercase, alphanumeric)."""
    cleaned = re.sub(r'[^a-z0-9]', '', title.lower())
    return cleaned[:60]