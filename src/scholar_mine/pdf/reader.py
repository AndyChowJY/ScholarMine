"""PDF text extraction via PyMuPDF."""
from pathlib import Path
from typing import Optional

from scholar_mine.utils.logger import Logger

log = Logger.get()

class PDFReader:
    def __init__(self, engine: str = "pymupdf"):
        self.engine = engine

    def extract_text(self, pdf_path: Path, max_chars: int = 150000) -> str:
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            full_text = []
            total = 0
            for page in doc:
                text = page.get_text()
                full_text.append(text)
                total += len(text)
                if total >= max_chars:
                    break
            doc.close()
            result = "\n\n".join(full_text)
            if len(result) > max_chars:
                result = result[:max_chars] + "\n\n[...truncated...]"
            return result
        except Exception as e:
            log.error(f"Failed to read {pdf_path}: {e}")
            return ""

    def extract_pages(self, pdf_path: Path, start: int, end: int) -> str:
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            texts = []
            for i in range(start - 1, min(end, len(doc))):
                texts.append(doc[i].get_text())
            doc.close()
            return "\n\n".join(texts)
        except Exception as e:
            log.error(f"Failed to extract pages from {pdf_path}: {e}")
            return ""

    def page_count(self, pdf_path: Path) -> int:
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0
