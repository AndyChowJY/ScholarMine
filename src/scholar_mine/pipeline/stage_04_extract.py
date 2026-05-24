"""Stage 4: Batch extract structured info from accepted PDFs via LLM."""
import json
from pathlib import Path
from typing import Any, Dict, List

from scholar_mine.pdf.reader import PDFReader
from scholar_mine.pdf.ref_stripper import ReferenceStripper
from scholar_mine.utils.logger import Logger

log = Logger.get()

class Stage04Extract:
    def __init__(self, config: dict, workspace: Path, llm_client, schema: dict):
        self.config = config
        self.workspace = Path(workspace)
        self.llm = llm_client
        self.schema = schema
        self.accepted_dir = workspace / "accepted"
        self.raw_dir = workspace / "extracted" / "llm_raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.reader = PDFReader()
        self.extract_cfg = config.get("extraction", {})
        self.batch_size = self.extract_cfg.get("batch_size", 40)
        self.chars_per_paper = self.extract_cfg.get("chars_per_paper", 100000)

    def run(self) -> dict:
        pdfs = list(self.accepted_dir.glob("*.pdf"))
        if not pdfs:
            log.warning("No PDFs in accepted/")
            return {"total": 0, "extracted": 0}

        log.info(f"Extracting from {len(pdfs)} papers, batch size {self.batch_size}")

        # Read all PDFs
        papers = []
        for pdf in pdfs:
            text = self.reader.extract_text(pdf, max_chars=self.chars_per_paper)
            text = ReferenceStripper.strip(text)
            papers.append({"source": pdf.name, "text": text, "path": str(pdf)})

        # Batch and send to LLM
        all_results = []
        for i in range(0, len(papers), self.batch_size):
            batch = papers[i:i + self.batch_size]
            log.info(f"Processing batch {i//self.batch_size + 1}: "
                     f"{len(batch)} papers (indices {i}-{i+len(batch)-1})")
            try:
                result = self.llm.extract_batch(batch, self.schema,
                                                max_tokens=self.extract_cfg.get("max_output_tokens", 128000))
                all_results.append(result)
                # Save raw batch result
                batch_path = self.raw_dir / f"batch_{i//self.batch_size + 1:04d}.json"
                batch_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
            except Exception as e:
                log.error(f"LLM batch {i//self.batch_size + 1} failed: {e}")

        # Merge all results
        merged = self._merge_results(all_results)
        merged_path = self.raw_dir / "all_extracted.json"
        merged_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        log.info(f"Extraction complete: {len(merged)} records from {len(pdfs)} papers")
        return {"total_papers": len(pdfs), "records_extracted": len(merged),
                "batches": len(all_results)}

    def _merge_results(self, all_results: List[dict]) -> List[dict]:
        merged = []
        for batch_result in all_results:
            results = batch_result.get("results", [])
            for paper_result in results:
                source = paper_result.get("source", "unknown")
                data = paper_result.get("data", [])
                for row in data:
                    row["source"] = source
                    merged.append(row)
        return merged
