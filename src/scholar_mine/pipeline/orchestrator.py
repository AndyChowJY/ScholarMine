"""Pipeline orchestrator — coordinates 5 stages with checkpoint resume."""
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from scholar_mine.utils.logger import Logger
from scholar_mine.utils.checkpoint import Checkpoint

log = Logger.get()

class Orchestrator:
    def __init__(self, config_path: Path, workspace: Path):
        self.config_path = Path(config_path)
        self.workspace = Path(workspace)
        self.checkpoint = Checkpoint(workspace)
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def run(self, start_stage: int = 1, end_stage: int = 5) -> bool:
        log.info(f"Pipeline starting from stage {start_stage} to {end_stage}")
        stages = {
            1: self._run_stage1,
            2: self._run_stage2,
            3: self._run_stage3,
            4: self._run_stage4,
            5: self._run_stage5,
        }
        all_ok = True
        for s in range(start_stage, end_stage + 1):
            if self.checkpoint.is_done(s):
                log.info(f"Stage {s}: already complete, skipping")
                continue
            try:
                result = stages[s]()
                self.checkpoint.mark_done(s, result)
                log.info(f"Stage {s}: completed")
            except Exception as e:
                log.error(f"Stage {s}: failed — {e}")
                self.checkpoint.mark_failed(s, str(e))
                all_ok = False
                break
        return all_ok

    def _run_stage1(self) -> dict:
        from scholar_mine.pipeline.stage_01_keywords import Stage01Keywords
        from scholar_mine.llm.client import LLMClient
        llm = LLMClient()
        stage = Stage01Keywords(self.config, llm, self.workspace)
        keywords = stage.run()
        return {"keywords_count": len(keywords)}

    def _run_stage2(self) -> dict:
        import asyncio
        from scholar_mine.pipeline.stage_02_crawl import Stage02Crawl
        stage = Stage02Crawl(self.config, self.workspace)
        return asyncio.run(stage.run())

    def _run_stage3(self) -> dict:
        from scholar_mine.pipeline.stage_03_filter import Stage03Filter
        from scholar_mine.llm.client import LLMClient
        llm = LLMClient()
        stage = Stage03Filter(self.config, self.workspace, llm)
        return stage.run()

    def _run_stage4(self) -> dict:
        from scholar_mine.pipeline.stage_04_extract import Stage04Extract
        from scholar_mine.llm.client import LLMClient
        llm = LLMClient()
        schema = self.config.get("schema", {})
        stage = Stage04Extract(self.config, self.workspace, llm, schema)
        return stage.run()

    def _run_stage5(self) -> dict:
        from scholar_mine.pipeline.stage_05_store import Stage05Store
        schema = self.config.get("schema", {})
        stage = Stage05Store(self.config, self.workspace, schema)
        return stage.run()
