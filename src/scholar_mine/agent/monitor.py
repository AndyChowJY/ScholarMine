"""Pipeline monitor — reads logs and suggests corrections."""
from pathlib import Path
from typing import Dict, List

from scholar_mine.utils.checkpoint import Checkpoint
from scholar_mine.utils.logger import Logger

log = Logger.get()

class PipelineMonitor:
    def __init__(self, workspace: Path, llm_client=None):
        self.workspace = Path(workspace)
        self.llm = llm_client
        self.checkpoint = Checkpoint(workspace)

    def check_status(self) -> dict:
        return self.checkpoint.status_summary()

    def analyze_errors(self) -> List[str]:
        errors = []
        error_log = self.workspace / "logs" / "errors" / "errors.log"
        if error_log.exists():
            try:
                lines = error_log.read_text(encoding="utf-8").splitlines()
                errors = [l for l in lines if l.strip()][-20:]
            except Exception:
                pass
        return errors

    def suggest_correction(self, error_summary: str) -> str:
        if not self.llm:
            return "No LLM client available for suggestions."
        prompt = f"""The ScholarMine pipeline encountered these errors:\n\n{error_summary}\n\nSuggest concrete parameter adjustments to fix these issues. Be specific about which config values to change."""
        return self.llm.chat(
            system_prompt="You are a pipeline debugging assistant.",
            user_prompt=prompt,
        )
