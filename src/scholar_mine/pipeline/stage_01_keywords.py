"""Stage 1: Keyword generation via LLM."""
import json
from pathlib import Path
from typing import List

from scholar_mine.utils.logger import Logger

log = Logger.get()

class Stage01Keywords:
    def __init__(self, config: dict, llm_client, workspace: Path):
        self.config = config
        self.llm = llm_client
        self.workspace = Path(workspace)

    def run(self) -> List[str]:
        keywords = self.config.get("keywords", [])
        if keywords:
            log.info(f"Using {len(keywords)} pre-configured keywords")
            self._save(keywords)
            return keywords

        direction = self.config.get("pipeline", {}).get("research_direction", "")
        if not direction:
            log.warning("No keywords or research direction in config")
            return []

        log.info(f"Generating keywords for: {direction}")
        keywords = self.llm.generate_keywords(direction, count=25)
        self._save(keywords)
        return keywords

    def _save(self, keywords: List[str]):
        path = self.workspace / "keywords.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for kw in keywords:
                f.write(json.dumps({"keyword": kw}, ensure_ascii=False) + "\n")
        log.info(f"Saved {len(keywords)} keywords to {path}")
