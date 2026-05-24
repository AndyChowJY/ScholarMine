"""Stage 5: Split extracted data per paper, write MD files + CSV."""
import json
from collections import defaultdict
from pathlib import Path

from scholar_mine.store.md_writer import MDWriter
from scholar_mine.store.csv_aggregator import CSVAggregator
from scholar_mine.utils.logger import Logger

log = Logger.get()

class Stage05Store:
    def __init__(self, config: dict, workspace: Path, schema: dict):
        self.config = config
        self.workspace = Path(workspace)
        self.schema = schema
        output_cfg = config.get("output", {})
        self.md_dir = workspace / output_cfg.get("md_dir", "output/md")
        self.csv_path = workspace / output_cfg.get("csv_path", "output/summary.csv")
        self.placeholder = output_cfg.get("placeholder", "-")
        self.raw_dir = workspace / "extracted" / "llm_raw"

    def run(self) -> dict:
        merged_path = self.raw_dir / "all_extracted.json"
        if not merged_path.exists():
            # Try to load from pipeline internal state
            log.warning("all_extracted.json not found, checking raw_dir")
            merged = self._load_from_batches()
        else:
            merged = json.loads(merged_path.read_text(encoding="utf-8"))

        if not merged:
            log.error("No extracted data to store")
            return {"md_files": 0, "csv_rows": 0}

        # Group by source
        per_paper = defaultdict(list)
        for row in merged:
            source = row.pop("source", "unknown")
            per_paper[source].append(row)

        # Write per-paper Markdown
        md_writer = MDWriter(self.md_dir, self.schema, self.placeholder)
        md_paths = md_writer.write_all(dict(per_paper))
        log.info(f"Wrote {len(md_paths)} Markdown files to {self.md_dir}")

        # Write summary CSV
        csv_agg = CSVAggregator(self.csv_path, self.schema, self.placeholder)
        csv_agg.aggregate(merged)
        log.info(f"Wrote summary CSV to {self.csv_path}")

        return {
            "md_files": len(md_paths),
            "csv_rows": len(merged),
            "csv_path": str(self.csv_path),
        }

    def _load_from_batches(self) -> list:
        merged = []
        for batch_file in sorted(self.raw_dir.glob("batch_*.json")):
            try:
                data = json.loads(batch_file.read_text(encoding="utf-8"))
                for paper_result in data.get("results", []):
                    source = paper_result.get("source", "unknown")
                    for row in paper_result.get("data", []):
                        row["source"] = source
                        merged.append(row)
            except Exception as e:
                log.warning(f"Failed to load {batch_file}: {e}")
        return merged
