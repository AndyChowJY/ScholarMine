"""Per-paper Markdown writer."""
from pathlib import Path
from typing import Any, Dict, List

from scholar_mine.utils.logger import Logger

log = Logger.get()

class MDWriter:
    def __init__(self, output_dir: Path, schema: dict, placeholder: str = "-"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fields = schema.get("fields", [])
        self.placeholder = placeholder

    def write_all(self, per_paper_data: dict) -> list:
        """Write one .md per source paper. per_paper_data: {source_name: [row_dicts]}"""
        paths = []
        for source, rows in per_paper_data.items():
            path = self.write_one(source, rows)
            if path:
                paths.append(path)
        return paths

    def write_one(self, source: str, rows: List[Dict[str, Any]]) -> Path:
        safe_name = Path(source).stem if source.endswith('.pdf') else source
        path = self.output_dir / f"{safe_name}.md"

        lines = [f"# Extracted data: {source}\n"]
        if not rows:
            lines.append("REJECT: No valid data extracted")
            path.write_text("\n".join(lines), encoding="utf-8")
            return path

        # Table header
        field_names = [f.get("name", f.get("key", "?")) for f in self.fields]
        field_keys = [f.get("key", "") for f in self.fields]
        header = "| " + " | ".join(field_names) + " |"
        sep = "|" + "|".join(["--------"] * len(field_names)) + "|"
        lines.append(header)
        lines.append(sep)

        for row in rows:
            vals = []
            for key in field_keys:
                v = row.get(key, "")
                if v is None or str(v).strip() == "":
                    v = self.placeholder
                vals.append(str(v).replace("|", "\\|"))
            lines.append("| " + " | ".join(vals) + " |")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
