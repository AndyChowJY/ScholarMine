"""CSV aggregator — combine all extracted rows into a single CSV."""
import csv
from pathlib import Path
from typing import Any, Dict, List

from scholar_mine.utils.logger import Logger

log = Logger.get()

class CSVAggregator:
    def __init__(self, output_path: Path, schema: dict, placeholder: str = "-"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.fields = schema.get("fields", [])
        self.placeholder = placeholder

    def aggregate(self, all_data: List[Dict[str, Any]]) -> Path:
        """Write CSV with schema field names as headers. all_data is a list of row dicts."""
        field_keys = [f.get("key", "") for f in self.fields]
        field_names = [f.get("name", f.get("key", "?")) for f in self.fields]

        rows_written = 0
        with open(self.output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=field_keys, extrasaction="ignore")
            # Write header with display names
            header_row = {key: name for key, name in zip(field_keys, field_names)}
            writer.writerow(header_row)

            for row in all_data:
                cleaned = {}
                for key in field_keys:
                    v = row.get(key, "")
                    if v is None or str(v).strip() == "":
                        v = self.placeholder
                    cleaned[key] = str(v)
                writer.writerow(cleaned)
                rows_written += 1

        log.info(f"CSV written: {rows_written} rows to {self.output_path}")
        return self.output_path
