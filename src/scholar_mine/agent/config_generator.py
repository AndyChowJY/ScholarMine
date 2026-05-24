"""Config generator — writes pipeline_config.yaml from plan results."""
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from scholar_mine.utils.logger import Logger

log = Logger.get()

class ConfigGenerator:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def generate(self, plan, overrides: Optional[dict] = None) -> Path:
        config = ConfigGenerator.build_config_dict(
            research_direction=plan.research_direction,
            keywords=plan.keywords,
            schema=plan.schema,
            paper_count=plan.paper_count,
        )
        if overrides:
            config.update(overrides)
        config["_generated_at"] = datetime.now().isoformat()
        config["_plan_summary"] = {
            "research_direction": plan.research_direction,
            "domain": plan.domain,
            "keyword_count": len(plan.keywords),
            "paper_count": plan.paper_count,
        }
        path = self.workspace / "pipeline_config.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        log.info(f"Pipeline config written to {path}")
        return path

    @staticmethod
    def build_config_dict(
        research_direction: str,
        keywords: List[str],
        schema: dict,
        paper_count: int = 1500,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
    ) -> dict:
        return {
            "pipeline": {
                "research_direction": research_direction,
                "paper_count": paper_count,
                "year_start": year_start,
                "year_end": year_end,
            },
            "keywords": keywords,
            "schema": schema,
            "platforms": {
                "tier1": ["arxiv", "semantic_scholar", "scihub", "core", "chemrxiv"],
                "tier2": ["crossref", "openalex", "pubmed", "unpaywall", "doaj"],
                "tier3": ["google_scholar", "researchgate"],
            },
            "extraction": {
                "batch_size": 40,
                "chars_per_paper": 100000,
                "max_output_tokens": 128000,
            },
            "output": {
                "md_dir": "output/md",
                "csv_path": "output/summary.csv",
                "placeholder": "-",
            },
        }
