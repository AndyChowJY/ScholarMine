"""Stage 3: Filter and classify downloaded PDFs."""
import shutil
from pathlib import Path

from scholar_mine.pdf.reader import PDFReader
from scholar_mine.utils.logger import Logger
from scholar_mine.utils.validators import validate_pdf, quick_title_reject

log = Logger.get()

class Stage03Filter:
    def __init__(self, config: dict, workspace: Path, llm_client):
        self.config = config
        self.workspace = Path(workspace)
        self.llm = llm_client
        self.download_dir = workspace / "downloads"
        self.accepted_dir = workspace / "accepted"
        self.rejected_dir = workspace / "rejected"
        for d in [self.accepted_dir, self.rejected_dir]:
            d.mkdir(parents=True, exist_ok=True)
        for sub in ["irrelevant", "corrupted", "duplicate", "no_data"]:
            (self.rejected_dir / sub).mkdir(exist_ok=True)
        self.reader = PDFReader()

    def run(self) -> dict:
        pdfs = list(self.download_dir.glob("*.pdf"))
        if not pdfs:
            log.warning("No PDFs to filter")
            return {"total": 0, "accepted": 0, "rejected": 0}

        log.info(f"Filtering {len(pdfs)} PDFs")
        accepted = 0
        rejected_stats = {"irrelevant": 0, "corrupted": 0, "duplicate": 0, "no_data": 0}

        for pdf in pdfs:
            # Step 1: technical validation
            valid, err = validate_pdf(pdf, min_pages=2, max_size_mb=100)
            if not valid:
                self._reject(pdf, "corrupted", err or "validation failed")
                rejected_stats["corrupted"] += 1
                continue

            # Step 2: title check
            try:
                text = self.reader.extract_text(pdf, max_chars=2000)
                first_line = text.split("\n")[0] if text else ""
                should_reject, reason = quick_title_reject(first_line)
                if should_reject:
                    self._reject(pdf, "irrelevant", reason or "title check failed")
                    rejected_stats["irrelevant"] += 1
                    continue
            except Exception:
                pass

            # Step 3: move to accepted
            dest = self.accepted_dir / pdf.name
            if not dest.exists():
                shutil.copy2(pdf, dest)
            accepted += 1

        log.info(f"Filter complete: {accepted} accepted, "
                 f"{sum(rejected_stats.values())} rejected")
        return {"total": len(pdfs), "accepted": accepted,
                "rejected": rejected_stats}

    def _reject(self, pdf: Path, category: str, reason: str):
        dest = self.rejected_dir / category / pdf.name
        shutil.copy2(pdf, dest)
        log.info(f"REJECT [{category}]: {pdf.name} — {reason}")
